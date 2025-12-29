# 참고: docs/backend/05-llm-service.md
# 참고: docs/backend/06-company-analysis.md

"""
LLM 기업 분석 서비스 (Gemini 2.5 Pro)

기업 분석 보고서 생성 전용 서비스
"""

from google import genai
from google.genai import types
from typing import Dict, Any, Optional, List
import logging
import json
import re
from datetime import datetime
import asyncio

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_random,
    retry_if_exception_type
)

from app.core.config import settings
from app.utils.llm_utils import (
    LLMAPIError,
    LLMRateLimitError,
    RateLimiter,
    CostTracker,
    deduplicate_news
)

logger = logging.getLogger(__name__)


class LLMCompanyAnalysis:
    """Gemini 2.5 Pro 기업 분석 서비스"""

    def __init__(self):
        """서비스 초기화 및 Gemini API 설정"""
        # API 키 검증
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        # 클라이언트 설정 (새 SDK)
        self.client = genai.Client(api_key=api_key)
        self.model_name = settings.GEMINI_MODEL

        # Generation config
        self.generation_config = types.GenerateContentConfig(
            temperature=settings.GEMINI_TEMPERATURE,
            top_p=0.9,
            top_k=40,
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
        )

        # Rate Limiter (분당 60회)
        self.rate_limiter = RateLimiter(
            max_requests=60,
            time_window=60
        )

        # Cost Tracker
        self.cost_tracker = CostTracker()

        logger.info(f"LLMCompanyAnalysis initialized with model: {settings.GEMINI_MODEL}")

    @retry(
        retry=retry_if_exception_type((LLMAPIError, LLMRateLimitError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=180) + wait_random(0, 3),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number}/5 - waiting before retry..."
        )
    )
    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> tuple[str, int]:
        """
        기본 텍스트 생성

        Args:
            prompt: 프롬프트
            temperature: 생성 온도 (기본값: settings)
            max_tokens: 최대 토큰 수 (기본값: settings)

        Returns:
            tuple[str, int]: (생성된 텍스트, 토큰 사용량)

        Raises:
            LLMAPIError: API 호출 실패 시
            LLMRateLimitError: Rate limit 초과 시

        Example:
            >>> response_text, tokens = await service.generate("삼성전자를 분석해줘")
        """
        # Rate Limiting
        await self.rate_limiter.acquire()

        try:
            # Generation config (온도 오버라이드 가능)
            config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else settings.GEMINI_TEMPERATURE,
                top_p=0.9,
                top_k=40,
                max_output_tokens=max_tokens if max_tokens is not None else settings.GEMINI_MAX_TOKENS,
            )

            # 비동기 모드로 API 호출 (새 SDK - asyncio.to_thread로 래핑)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # 응답 추출
            result_text = response.text

            # 토큰 사용량 로깅 (새 SDK - usage_metadata)
            tokens_used = 0
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                tokens_used = input_tokens + output_tokens
                self.cost_tracker.record_usage(input_tokens, output_tokens)
                logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {tokens_used}")

            return result_text, tokens_used

        except Exception as e:
            # 503 Service Unavailable 및 Rate Limit 에러 체크
            error_str = str(e).lower()
            if (
                '503' in str(e) or
                'unavailable' in error_str or
                'overloaded' in error_str or
                'rate limit' in error_str or
                'quota' in error_str
            ):
                logger.warning(f"Service temporarily unavailable (will retry): {e}")
                raise LLMRateLimitError(str(e))

            # 일반 API 에러 (재시도 불가)
            logger.error(f"LLM API error: {e}")
            raise LLMAPIError(str(e))

    async def analyze_company(
        self,
        ticker: str,
        company_data: Dict[str, Any]
    ) -> Dict:
        """
        기업 분석 보고서 생성

        Args:
            ticker: 종목 코드
            company_data: 기업 데이터
                {
                    'name': str,
                    'current_price': int,
                    'market_cap': int,
                    'financial': Dict,
                    'news': List[Dict],
                    'technical': Dict
                }

        Returns:
            분석 결과 딕셔너리

        Example:
            >>> analysis = await service.analyze_company('005930', data)
        """
        logger.info(f"Starting company analysis: {ticker}")

        # Step 1: 기본 밸류에이션 계산 (Python)
        logger.info("Step 1: 기본 밸류에이션 계산")
        base_val = self._calculate_base_valuation(
            company_data['financial'],
            company_data['current_price']
        )

        # Step 2: 기술적 지표 조정 계산 (Python)
        logger.info("Step 2: 기술적 지표 조정 계산")
        tech_adj = self._calculate_technical_adjustment(
            company_data['technical']
        )

        # Step 3: 뉴스 센티먼트 분석 (LLM)
        logger.info("Step 3: 뉴스 센티먼트 분석 (LLM)")
        news_sentiment = await self._analyze_news_sentiment(
            company_data['news']
        )

        # 중복 제거된 뉴스 추출 (원본 company_data는 보존)
        deduplicated_news = news_sentiment.get('deduplicated_news', company_data['news'])

        # 최종 목표가 계산
        total_adjustment = tech_adj['adjustment'] + news_sentiment['adjustment']
        total_adjustment = max(-0.25, min(0.25, total_adjustment))  # ±25% 제한

        preliminary_target = int(base_val['base_target'] * (1 + total_adjustment))

        logger.info(f"예비 목표가: {preliminary_target:,}원 (조정: {total_adjustment:+.1%})")

        # 프롬프트용 데이터 생성 (중복 제거된 뉴스 사용)
        prompt_data = {**company_data, 'news': deduplicated_news}

        # 프롬프트 구성 (Step 1~3 결과 포함)
        prompt = self._build_company_analysis_prompt(
            ticker,
            prompt_data,
            base_val,
            tech_adj,
            news_sentiment,
            preliminary_target
        )

        # LLM 호출 (최종 분석 및 검증)
        response_text, tokens_used = await self.generate(prompt)

        # JSON 파싱
        try:
            # JSON 블록 추출 (```json ... ``` 형식 처리)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 직접 JSON인 경우
                json_str = response_text

            analysis = json.loads(json_str)

            # 유효성 검증
            required_keys = ['summary', 'opinion', 'target_price', 'financial_analysis',
                            'industry_analysis', 'news_analysis', 'technical_analysis',
                            'risks', 'investment_strategy']
            for key in required_keys:
                if key not in analysis:
                    raise ValueError(f"Missing required key: {key}")

            # opinion 값 검증
            valid_opinions = ['STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL']
            if analysis['opinion'] not in valid_opinions:
                logger.warning(f"Invalid opinion: {analysis['opinion']}, defaulting to HOLD")
                analysis['opinion'] = 'HOLD'

            # risks 개수 검증
            if not isinstance(analysis['risks'], list) or len(analysis['risks']) < 3:
                logger.warning(f"Risks must be a list with at least 3 items")
                if not isinstance(analysis['risks'], list):
                    analysis['risks'] = []
                while len(analysis['risks']) < 3:
                    analysis['risks'].append("추가 리스크 분석 필요")

            # Step 1~3 계산 결과 추가
            analysis['target_price_calculation'] = {
                'step1_base_valuation': base_val,
                'step2_technical_adjustment': tech_adj,
                'step3_news_sentiment': news_sentiment,
                'preliminary_target': preliminary_target,
                'total_adjustment': total_adjustment
            }

            # 메타데이터 추가 (프롬프트 포함)
            analysis['metadata'] = {
                'model': settings.GEMINI_MODEL,
                'ticker': ticker,
                'generated_at': datetime.now().isoformat(),
                'prompt': prompt  # 디버깅용 프롬프트 포함
            }

            # tokens_used 추가
            analysis['tokens_used'] = tokens_used

            logger.info(f"Analysis completed: {ticker} - {analysis['opinion']} - 목표가: {analysis['target_price']:,}원 (토큰: {tokens_used})")
            return analysis

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            raise LLMAPIError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Error processing company analysis: {e}")
            raise

    # Note: _deduplicate_news() 메서드 삭제됨
    # - app.utils.llm_utils.deduplicate_news() 함수로 이동
    # - 중복 방지를 위해 utils로 분리

    async def _analyze_news_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        Step 3: 뉴스 센티먼트 분석 (LLM 호출)

        Args:
            news_list: 뉴스 목록 (최대 100개) [{'title': str, 'published_at': datetime, 'source': str}, ...]

        Returns:
            {
                'adjustment': float,      # -0.05 ~ 0.05
                'positive_count': int,
                'negative_count': int,
                'neutral_count': int,
                'key_positive_news': List[str],  # 주요 긍정 뉴스 제목
                'key_negative_news': List[str],  # 주요 부정 뉴스 제목
                'reasoning': str,
                'details': str,
                'original_count': int,   # 원본 뉴스 개수
                'deduplicated_count': int  # 중복 제거 후 개수
            }
        """
        if not news_list:
            logger.warning("뉴스 데이터 없음, 센티먼트 조정 0%")
            return {
                'adjustment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'key_positive_news': [],
                'key_negative_news': [],
                'reasoning': "뉴스 데이터 없음",
                'details': "뉴스 없음: 0%",
                'original_count': 0,
                'deduplicated_count': 0,
                'deduplicated_news': []
            }

        original_count = len(news_list)

        # 1. 전체 뉴스 중복 제거 (ko-sbert-sts 코사인 유사도 66% 이상)
        news_list = deduplicate_news(news_list, threshold=0.66)
        logger.info(f"뉴스 중복 제거: {original_count}개 → {len(news_list)}개 (중복 {original_count - len(news_list)}개 제거)")

        # 2. 중복 제거 후 최대 100개 선택하여 분석 (제목만)
        news_sample = news_list[:100]
        deduplicated_count = len(news_sample)
        logger.info(f"최종 분석 대상: {deduplicated_count}개 (최대 100개 제한)")

        prompt = f"""다음 {len(news_sample)}개 뉴스 **제목**을 분석하여 긍정/부정/중립을 분류하세요.

**긍정 뉴스**: M&A, 신사업, 기술 협력, 실적 개선, 수주, 투자 확대, 신제품, 매출 증가, 호조 등
**부정 뉴스**: 적자, 감원, 소송, 규제, 수요 감소, 공장 가동 중단, 리콜, 하락, 부진 등
**중립 뉴스**: 단순 사실 전달, 인사 발령, 일상적 업무 등

### 뉴스 목록 (제목만)
{self._format_news_data(news_sample, limit=100)}

### 작업
1. 각 뉴스를 긍정/부정/중립으로 분류
2. 개수 집계
3. 주요 긍정/부정 뉴스 선정 (영향력 큰 순서대로)

**JSON 응답 (코드 블록 없이):**
{{
    "positive_count": int,
    "negative_count": int,
    "neutral_count": int,
    "key_positive_news": ["긍정 뉴스 제목1", "제목2", ...],
    "key_negative_news": ["부정 뉴스 제목1", "제목2", ...],
    "reasoning": "긍정 뉴스 60개(55%)로 다수. M&A 팀 신설, AI 협력 등 성장 동력 확보 관련 호재가 주를 이룸"
}}
"""

        logger.info(f"Step 3 뉴스 센티먼트 분석 시작 ({len(news_sample)}개 뉴스)")

        try:
            response_text, _ = await self.generate(prompt, temperature=0.3)  # tokens_used는 무시

            # JSON 파싱 (```json 블록 또는 순수 JSON 추출)
            # 마크다운 코드 블록에서 JSON 추출 시도
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response_text)
            if code_block_match:
                result = json.loads(code_block_match.group(1))
            else:
                # 중첩된 JSON 객체를 올바르게 추출 (중괄호 균형)
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    result = json.loads(response_text)

            # 개수 추출
            positive = result.get('positive_count', 0)
            negative = result.get('negative_count', 0)
            neutral = result.get('neutral_count', 0)
            reasoning = result.get('reasoning', '')
            key_positive = result.get('key_positive_news', [])
            key_negative = result.get('key_negative_news', [])

            # 조정 비율 계산 (코드 기반)
            # 긍정 뉴스: +0.05% per news
            # 부정 뉴스: -0.05% per news
            adjustment = (positive * 0.0005) + (negative * -0.0005)
            adjustment = max(-0.05, min(0.05, adjustment))  # ±5% 제한

            details = f"긍정 {positive}개, 부정 {negative}개, 중립 {neutral}개 (원본 {original_count}개 → 중복제거 {deduplicated_count}개) → {adjustment:+.1%}"

            logger.info(f"Step 3 완료: {details}")

            return {
                'adjustment': adjustment,
                'positive_count': positive,
                'negative_count': negative,
                'neutral_count': neutral,
                'key_positive_news': key_positive,
                'key_negative_news': key_negative,
                'reasoning': reasoning,
                'details': details,
                'original_count': original_count,
                'deduplicated_count': deduplicated_count,
                'deduplicated_news': news_sample  # 중복 제거된 뉴스 리스트
            }

        except Exception as e:
            logger.exception(f"뉴스 센티먼트 분석 실패: {e}")  # exception()은 자동으로 traceback 포함
            # 폴백: 0% 조정, 중복 제거된 뉴스는 유지 (프롬프트에서 사용)
            fallback_news = news_sample if 'news_sample' in locals() else (news_list if 'news_list' in locals() else [])
            return {
                'adjustment': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'key_positive_news': [],
                'key_negative_news': [],
                'reasoning': f"분석 실패 (폴백): {str(e)}",
                'details': "분석 실패: 0%",
                'original_count': original_count if 'original_count' in locals() else 0,
                'deduplicated_count': len(fallback_news),
                'deduplicated_news': fallback_news
            }

    async def analyze_news_sentiment(self, news_list: List[Dict]) -> Dict:
        """
        뉴스 센티먼트 분석 (외부 API용 - 레거시 호환)

        Args:
            news_list: 뉴스 목록

        Returns:
            {
                'positive_count': int,
                'negative_count': int,
                'neutral_count': int,
                'sentiment': str,  # 'positive', 'neutral', 'negative'
                'summary': str  # 종합 요약
            }
        """
        result = await self._analyze_news_sentiment(news_list)

        # 레거시 형식으로 변환
        if result['adjustment'] > 0.02:
            sentiment = 'positive'
        elif result['adjustment'] < -0.02:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {
            'positive_count': result['positive_count'],
            'negative_count': result['negative_count'],
            'neutral_count': result['neutral_count'],
            'sentiment': sentiment,
            'summary': result['reasoning']
        }

    # ============= 목표가 계산 유틸리티 (Step 1, 2) =============

    def _calculate_base_valuation(
        self,
        financial: Dict,
        current_price: int
    ) -> Dict:
        """
        Step 1: 기본 밸류에이션 계산 (PER, PBR 기반)

        Args:
            financial: 재무 데이터 {'per', 'pbr', 'roe', 'revenue_growth_yoy'}
            current_price: 현재 주가

        Returns:
            {
                'per_target': int,     # PER 기반 목표가 (N/A일 경우 0)
                'pbr_target': int,     # PBR 기반 목표가 (N/A일 경우 0)
                'base_target': int,    # 평균 목표가
                'per_multiplier': float,   # PER 조정 배수
                'pbr_multiplier': float,   # PBR 조정 배수
                'details': str         # 계산 상세
            }

        Note:
            - PER 또는 PBR이 0인 경우 해당 지표는 N/A로 처리하고 계산에서 제외
            - 둘 다 0인 경우 현재가를 기준으로 함
        """
        per = financial.get('per', 0) or 0
        pbr = financial.get('pbr', 0) or 0
        roe = financial.get('roe', 0) or 0
        # Note: data_service는 'revenue_growth_yoy'로 반환하지만 호환성 위해 둘 다 체크
        revenue_growth = financial.get('revenue_growth_yoy', 0) or financial.get('revenue_growth', 0) or 0

        # 성장률에 따른 PER 조정 배수
        if revenue_growth >= 20:
            per_multiplier = 1.2
        elif revenue_growth >= 10:
            per_multiplier = 1.1
        elif revenue_growth >= 0:
            per_multiplier = 1.05
        else:
            per_multiplier = 0.95

        # ROE에 따른 PBR 조정 배수
        if roe >= 15:
            pbr_multiplier = 1.2
        elif roe >= 10:
            pbr_multiplier = 1.1
        elif roe >= 5:
            pbr_multiplier = 1.0
        else:
            pbr_multiplier = 0.9

        # A. PER 기반 목표가 (PER이 0이면 N/A 처리)
        per_target = 0
        per_detail = "N/A"
        if per > 0:
            eps = current_price / per
            adjusted_per = per * per_multiplier
            per_target = int(eps * adjusted_per)
            per_detail = f"EPS {eps:,.0f}원 × PER {per:.1f}배 × {per_multiplier:.2f} = {per_target:,}원"

        # B. PBR 기반 목표가 (PBR이 0이면 N/A 처리)
        pbr_target = 0
        pbr_detail = "N/A"
        if pbr > 0:
            bps = current_price / pbr
            adjusted_pbr = pbr * pbr_multiplier
            pbr_target = int(bps * adjusted_pbr)
            pbr_detail = f"BPS {bps:,.0f}원 × PBR {pbr:.2f}배 × {pbr_multiplier:.2f} = {pbr_target:,}원"

        # C. 평균 목표가 (유효한 값만 평균)
        valid_targets = [t for t in [per_target, pbr_target] if t > 0]
        if valid_targets:
            base_target = sum(valid_targets) // len(valid_targets)
        else:
            # 둘 다 N/A인 경우 현재가 기준
            base_target = current_price
            logger.warning(f"PER/PBR 모두 N/A - 현재가({current_price:,}원)를 기준으로 설정")

        details = (
            f"[PER 밸류] {per_detail} | "
            f"[PBR 밸류] {pbr_detail} | "
            f"[평균] {base_target:,}원"
        )

        logger.info(f"Step 1 계산 완료: {details}")

        return {
            'per_target': per_target,
            'pbr_target': pbr_target,
            'base_target': base_target,
            'per_multiplier': per_multiplier,
            'pbr_multiplier': pbr_multiplier,
            'details': details
        }

    def _calculate_technical_adjustment(
        self,
        technical: Dict
    ) -> Dict:
        """
        Step 2: 기술적 지표 기반 조정 비율 계산

        Args:
            technical: 기술적 지표 {'rsi', 'macd_status', 'ma_position'}

        Returns:
            {
                'adjustment': float,  # 조정 비율 (-0.10 ~ 0.10)
                'rsi_adj': float,
                'macd_adj': float,
                'ma_adj': float,
                'details': str
            }
        """
        rsi = technical.get('rsi', 50)
        macd_status = technical.get('macd_status', 'neutral')
        ma_position = technical.get('ma_position', '중립')

        # RSI 조정 (-5% ~ +5%)
        if rsi > 70:
            rsi_adj = -0.05  # 과매수
        elif rsi < 30:
            rsi_adj = 0.05   # 과매도
        else:
            rsi_adj = 0.0

        # MACD 조정 (-5% ~ +5%)
        if macd_status == 'golden_cross':
            macd_adj = 0.05
        elif macd_status == 'dead_cross':
            macd_adj = -0.05
        else:
            macd_adj = 0.0

        # MA 위치 조정 (-3% ~ +3%)
        if '상회' in ma_position:
            ma_adj = 0.03
        elif '하회' in ma_position:
            ma_adj = -0.03
        else:
            ma_adj = 0.0

        # 총 조정 (최대 ±10% 제한)
        total_adj = max(-0.10, min(0.10, rsi_adj + macd_adj + ma_adj))

        details = (
            f"RSI({rsi:.1f}): {rsi_adj:+.1%} | "
            f"MACD({macd_status}): {macd_adj:+.1%} | "
            f"MA({ma_position}): {ma_adj:+.1%} | "
            f"합계: {total_adj:+.1%}"
        )

        logger.info(f"Step 2 계산 완료: {details}")

        return {
            'adjustment': total_adj,
            'rsi_adj': rsi_adj,
            'macd_adj': macd_adj,
            'ma_adj': ma_adj,
            'details': details
        }

    # ============= 프롬프트 템플릿 =============

    def _build_company_analysis_prompt(
        self,
        ticker: str,
        data: Dict,
        base_val: Dict,
        tech_adj: Dict,
        news_sentiment: Dict,
        preliminary_target: int
    ) -> str:
        """
        기업 분석 프롬프트 생성

        Args:
            ticker: 종목코드
            data: 기업 데이터
            base_val: Step 1 기본 밸류에이션 결과
            tech_adj: Step 2 기술적 조정 결과
            news_sentiment: Step 3 뉴스 센티먼트 결과
            preliminary_target: 예비 목표가

        Returns:
            완성된 프롬프트 문자열
        """
        fin = data.get('financial', {})
        tech = data.get('technical', {})

        prompt = f"""당신은 한국 주식 시장의 전문 애널리스트입니다. 다음 기업에 대한 종합 분석 보고서를 작성하세요.

# 기업 정보
- 종목명: {data.get('name', 'N/A')}
- 종목코드: {ticker}
- 현재가: {data.get('current_price', 0):,}원
- 시가총액: {data.get('market_cap', 0) // 100000000:,}억원

# 재무 데이터
{self._format_financial_data(fin)}

# 최근 뉴스 (중복 제거 완료, 최대 15개)
{self._format_news_data(data.get('news', []), limit=15)}

# 기술적 지표
{self._format_technical_data(tech)}

---

# 목표가 계산 (Step 1~3)

## Step 1: 기본 밸류에이션 (PER/PBR 기반)
- PER 목표가: {base_val['per_target']:,}원
- PBR 목표가: {base_val['pbr_target']:,}원
- **기본 목표가: {base_val['base_target']:,}원**

상세: {base_val['details']}

### Step 2: 기술적 지표 조정
- {tech_adj['details']}
- **기술적 조정: {tech_adj['adjustment']:+.1%}**

### Step 3: 뉴스 센티먼트 분석 (중복 제거 후 {news_sentiment.get('deduplicated_count', 0)}개 분석)
- 긍정: {news_sentiment['positive_count']}개 (+{news_sentiment['positive_count'] * 0.05:.2f}%)
- 부정: {news_sentiment['negative_count']}개 ({news_sentiment['negative_count'] * -0.05:.2f}%)
- 중립: {news_sentiment['neutral_count']}개
- **뉴스 조정: {news_sentiment['adjustment']:+.2%}** (±5% 한도)

**주요 긍정 뉴스:**
{chr(10).join([f"  - {title}" for title in news_sentiment['key_positive_news'][:5]])}

**주요 부정 뉴스:**
{chr(10).join([f"  - {title}" for title in news_sentiment['key_negative_news'][:5]]) if news_sentiment['key_negative_news'] else '  (없음)'}

분석 근거: {news_sentiment['reasoning']}

## 예비 목표가
```
기본 밸류 {base_val['base_target']:,}원 × (1 + 기술적 조정 {tech_adj['adjustment']:.1%} + 뉴스 조정 {news_sentiment['adjustment']:.1%})
= {preliminary_target:,}원
```

---

# 분석 지침

## 투자의견 결정

목표가와 현재가를 비교하여 **종목 특성(변동성, 업종)을 고려**해 결정:
- **STRONG_BUY**: 큰 상승 여력, 강력한 모멘텀
- **BUY**: 적정 상승 여력
- **HOLD**: 제한적 상승/하락 여력
- **SELL**: 하락 가능성
- **STRONG_SELL**: 큰 하락 위험

### 손절가 (SELL/STRONG_SELL 시 필수)
- **손절가 = 목표가 - (목표가 × 0.05)**

---

다음 JSON 형식으로 작성하세요:

{{
    "summary": "투자 의견과 목표가의 핵심 근거 3줄 요약 (재무/뉴스/기술적 요인 중 결정적 요인 명시)",
    "opinion": "STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL",
    "target_price": 목표가(정수),
    "stop_loss_price": 손절가(정수, SELL/STRONG_SELL인 경우만 목표가-5%, 아니면 null),
    "key_points": ["핵심 근거 1", "핵심 근거 2", "핵심 근거 3"],
    "financial_analysis": {{
        "profitability": "수익성 분석: ROE 수치와 업종 평균 대비 평가",
        "growth": "성장성 분석: 매출/영업이익 성장률 및 전망",
        "stability": "안정성 분석: 부채비율, 유동비율 등 재무 건전성",
        "valuation": "밸류에이션: PER/PBR 업종 평균 대비 고평가/저평가 여부"
    }},
    "industry_analysis": {{
        "industry_trend": "업종 트렌드: 현재 업황 및 향후 전망",
        "competitive_advantage": "경쟁 우위: 기술력, 시장지배력, 브랜드 등",
        "market_position": "시장 지위: 시장점유율 및 경쟁사 대비 포지션"
    }},
    "news_analysis": {{
        "sentiment": "positive|neutral|negative",
        "key_news": ["주요 뉴스 1", "주요 뉴스 2", "주요 뉴스 3"],
        "impact": "뉴스가 주가에 미치는 영향 분석"
    }},
    "technical_analysis": {{
        "trend": "현재 추세: 상승/하락/횡보 및 근거",
        "support_resistance": "지지선/저항선: 구체적 가격대",
        "indicators": "지표 분석: RSI, MACD, 이동평균선 해석"
    }},
    "risks": ["리스크1: 구체적 설명", "리스크2: 구체적 설명", "리스크3: 구체적 설명"],
    "investment_strategy": {{
        "short_term": "단기(1주-1개월): 진입가, 목표가, 손절가 제시",
        "mid_term": "중기(1-3개월): 모니터링 포인트 및 대응 전략",
        "long_term": "장기(3개월+): 보유/회피 근거 및 장기 전망"
    }}
}}

**필수**:
- 모든 수치에 구체적 근거
- 리스크 **3가지 이상** 필수
- 목표가 산정 시 **시장 상황/업종 이슈** 반드시 고려
- 투자 권유 아닌 **참고 자료**임 명시
- **유효한 JSON만** 응답 (마크다운 코드 블록 없이)
"""
        return prompt

    # ============= 데이터 포맷팅 =============

    def _format_financial_data(self, financial: Dict) -> str:
        """
        재무 데이터를 텍스트로 포맷

        DataService.get_financial_data() 반환: {'roe', 'per', 'pbr', 'debt_ratio', 'revenue_growth_yoy'}

        Note: 0.00 값은 데이터 없음을 의미하므로 N/A로 표시
        """
        if not financial:
            return "재무 데이터 없음"

        def fmt(value, suffix: str = '') -> str:
            """0 또는 None 값을 N/A로 변환"""
            if value is None or value == 0 or value == 0.0:
                return "N/A"
            return f"{value:.2f}{suffix}"

        return f"""
- ROE (자기자본이익률): {fmt(financial.get('roe'), '%')}
- PER (주가수익비율): {fmt(financial.get('per'))}
- PBR (주가순자산비율): {fmt(financial.get('pbr'))}
- 부채비율: {fmt(financial.get('debt_ratio'), '%')}
- 매출 성장률 (YoY): {fmt(financial.get('revenue_growth_yoy') or financial.get('revenue_growth'), '%')}
"""

    def _format_news_data(self, news: List[Dict], limit: int = 15) -> str:
        """
        뉴스 데이터를 텍스트로 포맷

        DataService.get_news_data() 반환: List[{'title', 'content', 'published_at', 'source', 'url'}]

        Args:
            news: 뉴스 목록
            limit: 최대 개수 (기본값: 15, 센티먼트 분석 시 100 전달 가능)
        """
        if not news:
            return "최근 뉴스 없음"

        news_str_list = []
        for i, item in enumerate(news[:limit], 1):
            title = item.get('title', 'N/A')
            date = item.get('published_at', 'N/A')

            if isinstance(date, datetime):
                date_str = date.strftime('%Y.%m.%d %H:%M')
            else:
                date_str = str(date)

            source = item.get('source', 'N/A')
            news_str_list.append(f"{i}. [{date_str}] {title} ({source})")

        return "\n".join(news_str_list)

    def _format_technical_data(self, technical: Dict) -> str:
        """
        기술적 지표를 텍스트로 포맷

        DataService.get_technical_indicators() 반환: {'rsi', 'macd', 'macd_signal', 'macd_status', 'ma5', 'ma20', 'ma60', 'ma_position'}
        """
        if not technical:
            return "기술적 지표 데이터 없음"

        macd_status = technical.get('macd_status', 'neutral')
        macd_status_kr = {
            'golden_cross': '골든크로스 (매수 신호)',
            'dead_cross': '데드크로스 (매도 신호)',
            'neutral': '중립'
        }.get(macd_status, macd_status)

        return f"""
- RSI (14일): {technical.get('rsi', 0):.2f} {'(과매수)' if technical.get('rsi', 0) > 70 else '(과매도)' if technical.get('rsi', 0) < 30 else ''}
- MACD: {technical.get('macd', 0):.4f}
- MACD Signal: {technical.get('macd_signal', 0):.4f}
- MACD 상태: {macd_status_kr}
- 이동평균선:
  - 5일 MA: {technical.get('ma5', 0):,.0f}원
  - 20일 MA: {technical.get('ma20', 0):,.0f}원
  - 60일 MA: {technical.get('ma60', 0):,.0f}원
- MA 위치: {technical.get('ma_position', '중립')}
"""
