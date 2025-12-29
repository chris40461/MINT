# 참고: docs/backend/05-llm-service.md
# 참고: docs/backend/07-market-reports.md

"""
LLM 시장 리포트 서비스 (Gemini 2.5 Pro)

장 시작/마감 리포트 생성 전용 서비스
"""

from google import genai
from google.genai import types
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
import asyncio
import numpy as np

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
    CostTracker
)
from app.services.data_service import DataService
from app.db.database import get_db
from app.db.models import FinancialData
from app.utils.normalization import ScoreCalculator
from app.utils.llm_utils import deduplicate_news
import pandas as pd
import json

from pykrx import stock

logger = logging.getLogger(__name__)


class LLMReport:
    """Gemini 2.5 Pro 시장 리포트 서비스"""

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

        # Data Service 초기화
        self.data_service = DataService()

        logger.info(f"LLMReport initialized with model: {settings.GEMINI_MODEL}")

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
    ) -> str:
        """
        기본 텍스트 생성

        Args:
            prompt: 프롬프트
            temperature: 생성 온도 (기본값: settings)
            max_tokens: 최대 토큰 수 (기본값: settings)

        Returns:
            생성된 텍스트

        Raises:
            LLMAPIError: API 호출 실패 시
            LLMRateLimitError: Rate limit 초과 시

        Example:
            >>> response = await service.generate("오늘의 시장 전망은?")
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
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                self.cost_tracker.record_usage(input_tokens, output_tokens)
                logger.info(f"Token usage - Input: {input_tokens}, Output: {output_tokens}")

            return result_text

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

    @retry(
        retry=retry_if_exception_type((LLMAPIError, LLMRateLimitError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=180) + wait_random(0, 3),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry attempt {retry_state.attempt_number}/5 (Grounding) - waiting before retry..."
        )
    )
    async def _generate_with_grounding(
        self,
        prompt: str,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Google Search Grounding을 사용한 텍스트 생성

        Args:
            prompt: 프롬프트
            temperature: 생성 온도 (기본값: settings)

        Returns:
            {
                'text': str,  # 생성된 텍스트
                'grounding_metadata': Dict,  # 검색 메타데이터
                'search_queries': List[str],  # 실행된 검색 쿼리
                'sources': List[Dict]  # 참고 출처
            }

        Raises:
            LLMAPIError: API 호출 실패 시
            LLMRateLimitError: Rate limit 초과 시

        Example:
            >>> result = await service._generate_with_grounding("오늘의 글로벌 뉴스는?")
            >>> print(result['text'])
            >>> print(result['sources'])

        Note:
            - 비용: $0.035/request (검색 횟수와 무관)
            - 장 시작 리포트에만 사용 권장
        """
        # Rate Limiting
        await self.rate_limiter.acquire()

        try:
            # Grounding tool 설정
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            # Generation config (Grounding 포함)
            config = types.GenerateContentConfig(
                temperature=temperature if temperature is not None else settings.GEMINI_TEMPERATURE,
                tools=[grounding_tool]
            )

            # 비동기 모드로 API 호출 (새 SDK - asyncio.to_thread로 래핑)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # 응답 텍스트 추출
            result_text = response.text

            # Grounding 메타데이터 추출
            grounding_metadata = {}
            search_queries = []
            sources = []

            # TODO: 새 SDK에서 Grounding 메타데이터 추출 방법 확인 필요
            # 임시로 빈 값 반환
            logger.info(f"Grounding response received (metadata extraction not yet implemented)")

            # 토큰 사용량 로깅 (새 SDK - usage_metadata)
            input_tokens = 0
            output_tokens = 0
            if hasattr(response, 'usage_metadata'):
                input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0)
                output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0)
                self.cost_tracker.record_usage(input_tokens, output_tokens)
                logger.info(f"Grounding - Token usage: Input={input_tokens}, Output={output_tokens}")

            return {
                'text': result_text,
                'grounding_metadata': grounding_metadata,
                'search_queries': search_queries,
                'sources': sources,
                'tokens_used': input_tokens + output_tokens  # 토큰 사용량 반환
            }

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
                logger.warning(f"Service temporarily unavailable (grounding, will retry): {e}")
                raise LLMRateLimitError(str(e))

            # 일반 API 에러 (재시도 불가)
            logger.error(f"LLM API error (grounding): {e}")
            raise LLMAPIError(str(e))

    async def generate_morning_report(
        self,
        date: datetime
    ) -> Dict:
        """
        장 시작 리포트 생성 (08:30)

        Args:
            date: 오늘 날짜

        Returns:
            {
                'date': str,
                'market_forecast': str,  # 시장 전망
                'kospi_range': {'low': float, 'high': float},  # 예상 범위
                'top_stocks': List[Dict],  # 주목 종목 Top 10
                'sector_analysis': {  # 섹터 분석
                    'bullish': List[str],
                    'bearish': List[str]
                },
                'investment_strategy': str,  # 오늘의 전략
                'metadata': Dict
            }

        Example:
            >>> report = await service.generate_morning_report(datetime(2025, 11, 14))
        """
        logger.info(f"=== Morning Report 생성 시작: {date.strftime('%Y-%m-%d')} ===")

        # Phase 1: Top 10 종목 선정 (센티먼트 포함)
        logger.info("Phase 1: Top 10 종목 선정 (M:40%, V:30%, T:20%, S:10%)...")
        top_10_stocks = await self.select_top_stocks_for_morning(date, top_n=10)

        # Phase 2: 시장 데이터 수집
        logger.info("Phase 2: 시장 데이터 수집 (전일 KOSPI, 해외 시장)...")
        market_data = await self._collect_market_data(date)

        # ===== Phase 2.5: realtime_prices 조회 (시간외 데이터 포함) =====
        logger.info("Phase 2.5: realtime_prices 조회 (시간외 데이터 포함)...")
        tickers = [stock['ticker'] for stock in top_10_stocks]

        realtime_prices = await self.data_service.get_realtime_prices_bulk(
            tickers,
            staleness_threshold=86400  # 24시간
        )

        # Top 10에 realtime_prices 병합
        for stock in top_10_stocks:
            ticker = stock['ticker']
            if ticker in realtime_prices:
                rt = realtime_prices[ticker]
                if rt.get('current_price', 0) > 0:
                    stock['realtime_price'] = rt
                    logger.debug(f"{ticker}: realtime_price 추가 (등락률: {rt.get('change_rate', 0):+.2f}%)")
                else:
                    stock['realtime_price'] = None
            else:
                stock['realtime_price'] = None
                logger.debug(f"{ticker}: realtime_prices 데이터 없음")

        realtime_count = sum(1 for s in top_10_stocks if s.get('realtime_price'))
        logger.info(f"realtime_prices 병합 완료: {realtime_count}/{len(top_10_stocks)}개")

        # ===== Phase 2.6: ATR 계산 (동적 목표가/손절가용) =====
        logger.info("Phase 2.6: ATR 계산 (동적 목표가/손절가용)...")
        atr_data = await self.data_service.get_atr_batch(tickers, date, period=14)

        # Top 10에 ATR 정보 병합
        for stock in top_10_stocks:
            ticker = stock['ticker']
            stock['atr'] = atr_data.get(ticker)

            # ATR 비율 계산 (현재가 대비)
            if stock['atr'] and stock.get('realtime_price'):
                current_price = stock['realtime_price'].get('current_price', 0)
                if current_price > 0:
                    stock['atr_percent'] = round(stock['atr'] / current_price * 100, 2)
                else:
                    stock['atr_percent'] = None
            else:
                stock['atr_percent'] = None

        atr_count = sum(1 for s in top_10_stocks if s.get('atr'))
        logger.info(f"ATR 병합 완료: {atr_count}/{len(top_10_stocks)}개")

        # Phase 3: 프롬프트 구성
        logger.info("Phase 3: Morning Report 프롬프트 구성...")
        prompt = self._build_morning_report_prompt(date, market_data, top_10_stocks)

        # Phase 4: LLM 호출 (Google Search Grounding)
        logger.info("Phase 4: LLM 호출 (Google Search Grounding)...")
        try:
            response = await self._generate_with_grounding(prompt, temperature=0.3)
            response_text = response['text']

            # JSON 파싱
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)

            # LLM이 생성한 top_stocks에 score 추가 (병합)
            top_stocks_from_llm = result.get('top_stocks', [])

            # ticker를 키로 하는 score 매핑 생성
            score_map = {stock['ticker']: stock for stock in top_10_stocks}

            # 각 종목에 score를 올바른 위치에 삽입 (current_price 다음)
            top_stocks_reordered = []
            for llm_stock in top_stocks_from_llm:
                ticker = llm_stock.get('ticker')
                original_stock = score_map.get(ticker, {})

                # TopStock 모델 순서에 맞게 재구성
                reordered = {
                    'rank': llm_stock.get('rank'),
                    'ticker': llm_stock.get('ticker'),
                    'name': llm_stock.get('name'),
                    'current_price': llm_stock.get('current_price'),
                    'score': original_stock.get('final_score'),  # ← 여기에 삽입!
                    'reason': llm_stock.get('reason'),
                    'entry_strategy': llm_stock.get('entry_strategy')
                }
                top_stocks_reordered.append(reordered)

            # 재정렬된 top_stocks로 교체
            result['top_stocks'] = top_stocks_reordered

            # 메타데이터 추가
            result['date'] = date.strftime('%Y-%m-%d')
            result['generated_at'] = datetime.now().isoformat()  # ISO 문자열 (JSON 직렬화 가능, Pydantic 자동 변환)
            result['metadata'] = {
                'market_data': market_data,
                'grounding_sources': response.get('sources', []),
                'tokens_used': response.get('tokens_used', 0)  # 토큰 사용량 추가
            }

            logger.info("Morning Report 생성 완료!")
            return result

        except Exception as e:
            logger.error(f"Morning Report 생성 실패: {e}")

            # top_10_stocks를 TopStock 모델 형식으로 변환
            formatted_stocks = []
            for idx, stock in enumerate(top_10_stocks[:10], 1):
                formatted_stocks.append({
                    'rank': idx,
                    'ticker': stock.get('ticker', ''),
                    'name': stock.get('name', ''),
                    'current_price': 0,  # 에러 시 0으로 설정
                    'score': stock.get('final_score', 5.0),
                    'reason': '데이터 수집 중 오류가 발생했습니다.',
                    'entry_strategy': None  # Optional이므로 None 허용
                })

            # 기본 응답 반환 (MorningReport 모델 호환)
            return {
                'date': date.strftime('%Y-%m-%d'),
                'generated_at': datetime.now().isoformat(),
                'market_forecast': '시장 데이터 수집 중 오류가 발생했습니다.',
                'kospi_range': {'low': 0.0, 'high': 0.0, 'reasoning': '오류 발생'},
                'market_risks': [],
                'top_stocks': formatted_stocks,
                'sector_analysis': {'bullish': [], 'bearish': []},
                'investment_strategy': '오늘은 관망세를 유지하세요.',
                'daily_schedule': {},
                'metadata': {'error': str(e)}
            }

    async def generate_afternoon_report(
        self,
        date: datetime,
        market_summary: Dict,
        surge_stocks: List[Dict]
    ) -> Dict:
        """
        장 마감 리포트 생성 (15:40)

        Args:
            date: 날짜
            market_summary: 시장 요약
                {
                    'kospi_close': float,
                    'kospi_change': float,
                    'trading_value': int,
                    'foreign_net': int,
                    'institution_net': int
                }
            surge_stocks: 급등주 목록 (오후 트리거 결과)

        Returns:
            {
                'market_summary_text': str,  # 시장 요약
                'surge_analysis': List[Dict],  # 급등주 분석
                'tomorrow_strategy': str,  # 내일 전략
                'metadata': Dict
            }

        Example:
            >>> report = await service.generate_afternoon_report(
            ...     datetime(2025, 11, 6),
            ...     summary,
            ...     surge_stocks
            ... )
        """
        logger.info(f"=== Afternoon Report 생성 시작: {date.strftime('%Y-%m-%d')} ===")

        # 1. 프롬프트 구성
        prompt = self._build_afternoon_report_prompt(
            date,
            market_summary,
            surge_stocks
        )
        # 2. LLM 호출 (Grounding 필수 - 뉴스를 통해 상승 이유 파악)
        logger.info("Phase 2: LLM 호출 (Google Search Grounding) - 시장 이슈 분석...")
        try:
            # 장 마감은 사실 관계가 중요하므로 temperature를 낮게 설정
            response = await self._generate_with_grounding(prompt, temperature=0.3)
            response_text = response['text']

            #JSON 파싱
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)

            # 필수 필드 추가
            result['report_type'] = 'afternoon'
            result['date'] = date.strftime('%Y-%m-%d')
            result['generated_at'] = datetime.now().isoformat()
            # market_summary (ExtendedMarketSummary) - 입력값을 그대로 포함
            result['market_summary'] = market_summary
            # 메타데이터
            result['metadata'] = {
                'grounding_sources': response.get('sources', []),
                'tokens_used': response.get('tokens_used', 0)
            }

            logger.info("Afternoon Report 생성 완료!")
            return result
        except Exception as e:
            logger.error(f"Afternoon Report 생성 실패: {e}", exc_info=True)

            # 에러 발생 시 기본 구조 반환
            return {
                'report_type': 'afternoon',
                'date': date.strftime('%Y-%m-%d'),
                'generated_at': datetime.now().isoformat(),
                'market_summary': market_summary,  # 입력값 그대로 포함
                'market_summary_text': '리포트 생성 중 오류가 발생했습니다.',
                'market_breadth': None,
                'sector_analysis': None,
                'supply_demand_analysis': '',
                'today_themes': [],
                'surge_analysis': [],
                'tomorrow_strategy': '데이터를 확인할 수 없습니다.',
                'check_points': [],
                'metadata': {'error': str(e)}
            }

    # ============= 주목 종목 선정 =============

    async def select_top_stocks_for_morning(
        self,
        date: datetime,
        top_n: int = 10
    ) -> List[Dict]:
        """
        주목 종목 Top 10 선정 (단기 예측 기반)

        학술 근거: 단기 예측(1-7일)에서 Fundamental metrics는 0% 중요도
        - Financial Innovation 2023: Momentum 35-40% 중요도
        - Journal of Big Data 2020: Volume Patterns 25-30%
        - PMC 2023: Sentiment + Technical = 90% 정확도

        Process:
            1. DB 조회 (700개 필터링된 종목)
            2. 3개 점수 계산 + 정규화
               - Momentum (40%): D-1(40%), D-5(35%), D-20(25%) 수익률
               - Volume (30%): 거래량 증가율(60%) + 거래대금(40%), percentile 정규화
               - Technical (20%): RSI/MACD/MA 기술적 조정
            3. 가중 평균 (M:40%, V:30%, T:20%) → Top 50 선정
            4. 50개 뉴스 크롤링
            5. 5개씩 배치 센티먼트 분석
            6. 센티먼트 통합 (기존 90% + 센티먼트 10%) → Top 10 선정

        Args:
            date: 기준 날짜 (전날 D-1 데이터 기준)
            top_n: 선정 개수 (기본값: 10)

        Returns:
            Top N 종목 리스트 [
                {
                    'ticker': str,
                    'name': str,
                    'momentum_score': float,
                    'volume_score': float,
                    'technical_score': float,
                    'sentiment_score': float,
                    'final_score': float
                }
            ]
        """
        logger.info(f"=== Phase 1.1: 시장 스냅샷 + DB 데이터 조회 시작 ===")

        # Phase 1.1-1: 시장 스냅샷 조회 (OHLCV 데이터)
        df_market = await self.data_service.get_market_snapshot(date)
        logger.info(f"시장 스냅샷 조회 완료: {len(df_market)}개 종목")

        # Phase 1.1-2: DB에서 재무 데이터 조회
        with get_db() as db:
            all_stocks = db.query(FinancialData).all()
            # 세션 내에서 to_dict() 호출 (detached 오류 방지)
            df_financial = pd.DataFrame([stock.to_dict() for stock in all_stocks])
        logger.info(f"DB 조회 완료: {len(df_financial)}개 종목")

        # Phase 1.1-3: 시장 스냅샷과 재무 데이터 merge (inner join)
        df = df_market.merge(df_financial, on='ticker', how='inner')
        initial_count = len(df)
        logger.info(f"Merge 완료: {initial_count}개 종목 (시장 데이터 + 재무 데이터)")

        # 유효성 검증 (PER > 0, PBR > 0, 종가 > 0)
        df = df[
            (df['per'] > 0) &
            (df['pbr'] > 0) &
            (df['market_cap'] > 0) &
            (df['종가'] > 0)
        ].copy()

        valid_count = len(df)
        logger.info(f"유효성 검증 완료: {valid_count}개 종목 (제외: {initial_count - valid_count}개)")

        if df.empty:
            logger.error("유효한 종목이 없습니다!")
            return []

        # Phase 1.2-1.4: 3개 점수 계산 (Momentum, Volume, Technical)
        # 학술 근거: 단기 예측(1-7일)에서 Fundamental metrics는 0% 중요도
        logger.info(f"=== Phase 1.2-1.4: 3개 점수 계산 시작 ===")
        df = await self._calculate_all_scores(df, date)

        # Phase 2.1: 가중 평균 및 Top 50 선정
        # M:40%, V:30%, T:20% (Sentiment 10%는 Top 50 선정 후 추가)
        logger.info(f"=== Phase 2.1: Top 50 선정 ===")
        df['base_score'] = (
            df['momentum_score'] * 0.40 +
            df['volume_score'] * 0.30 +
            df['technical_score'] * 0.20
        )

        top_50 = df.nlargest(50, 'base_score').copy()
        logger.info(f"Top 50 선정 완료: 평균 점수 {top_50['base_score'].mean():.2f}")

        # Phase 2.2-2.4: 센티먼트 분석 및 Top 10 선정
        logger.info(f"=== Phase 2.2-2.4: 센티먼트 분석 시작 ===")
        top_10 = await self._analyze_sentiment_and_select_top(top_50, top_n)

        logger.info(f"=== Top {top_n} 선정 완료 ===")
        return top_10

    async def _calculate_all_scores(
        self,
        df: pd.DataFrame,
        date: datetime
    ) -> pd.DataFrame:
        """3개 점수 계산 (각 0-10 스케일)"""
        # Phase 1.2: Momentum 점수
        logger.info("Phase 1.2: Momentum 점수 계산 중...")
        df['momentum_score'] = await self._calculate_momentum_scores(df, date)

        # Phase 1.3: Volume 점수
        logger.info("Phase 1.3: Volume 점수 계산 중...")
        df['volume_score'] = await self._calculate_volume_scores(df, date)

        # Phase 1.4: Technical 점수 (RSI/MACD/MA)
        logger.info("Phase 1.4: Technical 점수 계산 중...")
        df['technical_score'] = await self._calculate_technical_scores(df, date)

        return df

    async def _calculate_momentum_scores(
        self,
        df: pd.DataFrame,
        date: datetime
    ) -> pd.Series:
        """
        Momentum 점수 계산 (D-1/D-5/D-20 수익률)

        학술 근거: Financial Innovation 2023
        - Short-term Reversal(D-1)이 가장 강력한 단변량 예측 변수
        - D-5, D-20 조합 시 단기 예측력 향상

        가중치:
        - D-1  (1 거래일 전 대비): 40%
        - D-5  (5 거래일 전 대비): 35%
        - D-20 (20 거래일 전 대비): 25%
        """
        try:
            # KOSPI 인덱스로 최근 25 거래일 조회 (D-20 + 여유분)
            date_str = date.strftime("%Y%m%d")
            start_date = (date - timedelta(days=50)).strftime("%Y%m%d")  # 50일 전부터

            logger.info(f"Momentum 계산: 최근 거래일 목록 조회 ({start_date} ~ {date_str})")

            # KOSPI 인덱스 OHLCV로 거래일 목록 확인
            kospi_df = self.data_service._retry_request(
                lambda: stock.get_index_ohlcv_by_date(start_date, date_str, "1001")  # KOSPI
            )

            if kospi_df.empty:
                logger.warning("거래일 목록 조회 실패, 중립 점수 반환")
                return pd.Series(5.0, index=df.index)

            # 거래일 날짜 목록 (최신순 정렬)
            trading_days = kospi_df.index.tolist()
            trading_days.sort(reverse=True)

            # 오늘이 목록에 없으면 가장 최신 거래일을 오늘로 간주
            if date.date() not in [d.date() if isinstance(d, datetime) else d for d in trading_days]:
                today_idx = 0
            else:
                today_idx = next(i for i, d in enumerate(trading_days)
                               if (d.date() if isinstance(d, datetime) else d) == date.date())

            # D-1, D-5, D-20 거래일 찾기
            if len(trading_days) < today_idx + 21:
                logger.warning(f"거래일 부족 (필요: {today_idx + 21}일, 보유: {len(trading_days)}일)")
                return pd.Series(5.0, index=df.index)

            d1_date = trading_days[today_idx + 1]    # 1 거래일 전
            d5_date = trading_days[today_idx + 5]    # 5 거래일 전
            d20_date = trading_days[today_idx + 20]  # 20 거래일 전

            logger.info(f"Momentum 기준일: D-1={d1_date}, D-5={d5_date}, D-20={d20_date}")

            # 각 날짜의 시장 스냅샷 조회
            df_d1 = await self.data_service.get_market_snapshot(pd.Timestamp(d1_date).to_pydatetime())
            df_d5 = await self.data_service.get_market_snapshot(pd.Timestamp(d5_date).to_pydatetime())
            df_d20 = await self.data_service.get_market_snapshot(pd.Timestamp(d20_date).to_pydatetime())

            # ticker 기준으로 merge (left join)
            df_merged = df[['ticker', '종가']].copy()
            df_merged = df_merged.merge(
                df_d1[['ticker', '종가']].rename(columns={'종가': '종가_d1'}),
                on='ticker', how='left'
            )
            df_merged = df_merged.merge(
                df_d5[['ticker', '종가']].rename(columns={'종가': '종가_d5'}),
                on='ticker', how='left'
            )
            df_merged = df_merged.merge(
                df_d20[['ticker', '종가']].rename(columns={'종가': '종가_d20'}),
                on='ticker', how='left'
            )

            # 수익률 계산 (%) - 0으로 나누기 방지
            df_merged['return_d1'] = ((df_merged['종가'] / df_merged['종가_d1'].replace(0, np.nan)) - 1) * 100
            df_merged['return_d5'] = ((df_merged['종가'] / df_merged['종가_d5'].replace(0, np.nan)) - 1) * 100
            df_merged['return_d20'] = ((df_merged['종가'] / df_merged['종가_d20'].replace(0, np.nan)) - 1) * 100

            # 결측값을 0으로 대체 (과거 데이터 없는 경우)
            df_merged = df_merged.fillna(0)

            # 각 수익률을 robust normalize (음수 수익률 처리 가능)
            return_d1_robust = ScoreCalculator.robust_normalize(df_merged['return_d1'])
            return_d5_robust = ScoreCalculator.robust_normalize(df_merged['return_d5'])
            return_d20_robust = ScoreCalculator.robust_normalize(df_merged['return_d20'])

            # min-max normalize (0-1)
            return_d1_norm = ScoreCalculator.min_max_normalize(return_d1_robust)
            return_d5_norm = ScoreCalculator.min_max_normalize(return_d5_robust)
            return_d20_norm = ScoreCalculator.min_max_normalize(return_d20_robust)

            # 가중 평균 (0-1) → 0-10 스케일
            momentum_score = (
                return_d1_norm * 0.40 +
                return_d5_norm * 0.35 +
                return_d20_norm * 0.25
            ) * 10.0

            logger.info(f"Momentum 점수 - 평균: {momentum_score.mean():.2f}, "
                       f"D-1 평균수익률: {df_merged['return_d1'].mean():.2f}%, "
                       f"D-5 평균수익률: {df_merged['return_d5'].mean():.2f}%, "
                       f"D-20 평균수익률: {df_merged['return_d20'].mean():.2f}%")
            return pd.Series(momentum_score.values, index=df.index)

        except Exception as e:
            logger.error(f"Momentum 점수 계산 실패: {e}", exc_info=True)
            # 실패 시 중립 점수 반환
            return pd.Series(5.0, index=df.index)

    async def _calculate_volume_scores(
        self,
        df: pd.DataFrame,
        date: datetime
    ) -> pd.Series:
        """
        Volume 점수 계산 (거래량 증가율 + 거래대금)

        학술 근거: Journal of Big Data 2020 - Feature Engineering
        - Trading Volume Patterns이 단기 예측에 중요
        - Percentile normalization으로 이상치 영향 최소화

        가중치:
        - 거래량 증가율 (현재 vs 20일 평균): 60%
        - 거래대금 (절대값): 40%
        """
        try:
            # KOSPI 인덱스로 최근 30 거래일 조회 (20일 평균 + 여유분)
            date_str = date.strftime("%Y%m%d")
            start_date = (date - timedelta(days=45)).strftime("%Y%m%d")

            logger.info(f"Volume 계산: 최근 거래일 목록 조회 ({start_date} ~ {date_str})")

            # KOSPI 인덱스 OHLCV로 거래일 목록 확인
            kospi_df = self.data_service._retry_request(
                lambda: stock.get_index_ohlcv_by_date(start_date, date_str, "1001")
            )

            if kospi_df.empty:
                logger.warning("거래일 목록 조회 실패, 중립 점수 반환")
                return pd.Series(5.0, index=df.index)

            # 거래일 날짜 목록 (최신순 정렬)
            trading_days = kospi_df.index.tolist()
            trading_days.sort(reverse=True)

            # 오늘 제외 최근 20 거래일 선택
            if len(trading_days) < 21:
                logger.warning(f"거래일 부족 (필요: 21일, 보유: {len(trading_days)}일)")
                return pd.Series(5.0, index=df.index)

            past_20_days = trading_days[1:21]  # 오늘 제외하고 1~20 거래일 전

            # 최근 20일간 각 날짜의 거래량 조회
            volume_dfs = []
            for trade_date in past_20_days:
                try:
                    df_day = await self.data_service.get_market_snapshot(
                        pd.Timestamp(trade_date).to_pydatetime()
                    )
                    volume_dfs.append(df_day[['ticker', '거래량']])
                except Exception as e:
                    logger.warning(f"{trade_date} 거래량 조회 실패: {e}")
                    continue

            if not volume_dfs:
                logger.warning("과거 거래량 데이터 조회 실패, 중립 점수 반환")
                return pd.Series(5.0, index=df.index)

            # 20일간 거래량 평균 계산
            volume_combined = pd.concat(volume_dfs, ignore_index=True)
            avg_volume_20d = volume_combined.groupby('ticker')['거래량'].mean().reset_index()
            avg_volume_20d.columns = ['ticker', '평균거래량_20d']

            # 현재 데이터와 merge
            df_merged = df[['ticker', '거래량', '거래대금']].copy()
            df_merged = df_merged.merge(avg_volume_20d, on='ticker', how='left')

            # 거래량 증가율 계산 (%) - 0으로 나누기 방지
            df_merged['거래량증가율'] = ((df_merged['거래량'] / df_merged['평균거래량_20d'].replace(0, np.nan)) - 1) * 100
            df_merged = df_merged.fillna(0)

            # Offset 추가 (음수 제거용): 증가율에 100 더하기
            # -50% → 50, 0% → 100, +100% → 200
            # 상대적 관계는 유지하면서 모두 양수로 변환
            df_merged['거래량증가율_adjusted'] = df_merged['거래량증가율'] + 100

            # 로그 변환 (분포 개선용)
            # 거래량, 거래대금은 왜도가 큰 분포이므로 로그 변환으로 정규분포에 가깝게
            df_merged['거래량증가율_log'] = np.log(df_merged['거래량증가율_adjusted'].clip(lower=1))
            df_merged['거래대금_log'] = np.log(df_merged['거래대금'].clip(lower=1))

            # percentile normalize (5%-95% clipping)
            # robust normalize는 중앙값 기준이라 음수 값이 많을 때 점수가 낮게 나옴
            volume_increase_norm = ScoreCalculator.clip_and_normalize(df_merged['거래량증가율_log'])
            trading_value_norm = ScoreCalculator.clip_and_normalize(df_merged['거래대금_log'])

            # 가중 평균 (0-1) → 0-10 스케일
            volume_score = (
                volume_increase_norm * 0.60 +
                trading_value_norm * 0.40
            ) * 10.0

            logger.info(f"Volume 점수 - 평균: {volume_score.mean():.2f}, "
                       f"평균 거래량증가율: {df_merged['거래량증가율'].mean():.2f}%")
            return pd.Series(volume_score.values, index=df.index)

        except Exception as e:
            logger.error(f"Volume 점수 계산 실패: {e}", exc_info=True)
            # 실패 시 중립 점수 반환
            return pd.Series(5.0, index=df.index)

    async def _calculate_technical_scores(self, df: pd.DataFrame, date: datetime) -> pd.Series:
        """
        Technical 점수 계산 (RSI/MACD/MA)

        학술 근거: arXiv 2024 - Price-based features > Technical indicators
        - 기술적 지표는 단기 예측에 보조적 역할 (20%)
        - 과매수/과매도 신호로 리스크 조정

        company_analysis._calculate_technical_adjustment() 로직을 배치로 적용

        가중치:
        - RSI: -5~+5 (과매수/과매도)
        - MACD: -5~+5 (골든/데드 크로스)
        - MA: -3~+3 (이동평균 위치)
        - 총합: -13~+13 → 0~10 스케일

        Args:
            df: DataFrame (필수 컬럼: ticker)
            date: 기준일

        Returns:
            Technical 점수 (0-10)
        """
        logger.info(f"Technical 점수 계산 시작 (RSI/MACD/MA) - {len(df)}개 종목")

        # 배치 기술적 지표 조회
        tech_df = await self.data_service.get_technical_indicators_batch(
            df['ticker'].tolist(),
            date
        )

        # df와 tech_df merge (ticker 기준)
        df_merged = df.set_index('ticker').join(tech_df, how='left')

        # RSI 조정 점수 (-5 ~ +5)
        def get_rsi_adj(rsi):
            if rsi > 70:
                return -5  # 과매수
            elif rsi < 30:
                return 5   # 과매도
            else:
                return 0

        df_merged['rsi_adj'] = df_merged['rsi'].apply(get_rsi_adj)

        # MACD 조정 점수 (-5 ~ +5)
        def get_macd_adj(status):
            if status == 'golden_cross':
                return 5
            elif status == 'dead_cross':
                return -5
            else:
                return 0

        df_merged['macd_adj'] = df_merged['macd_status'].apply(get_macd_adj)

        # MA 위치 조정 점수 (-3 ~ +3)
        def get_ma_adj(position):
            if '상회' in str(position):
                return 3
            elif '하회' in str(position):
                return -3
            else:
                return 0

        df_merged['ma_adj'] = df_merged['ma_position'].apply(get_ma_adj)

        # 총 조정 (-13 ~ +13)
        df_merged['tech_adjustment'] = (
            df_merged['rsi_adj'] +
            df_merged['macd_adj'] +
            df_merged['ma_adj']
        )

        # 정규화: -13~+13 → 0~10
        technical_score = ((df_merged['tech_adjustment'] + 13) / 26) * 10.0

        logger.info(f"Technical 점수 - 평균: {technical_score.mean():.2f}, 평균 조정: {df_merged['tech_adjustment'].mean():.2f}")
        return technical_score.reset_index(drop=True)

    async def _analyze_sentiment_and_select_top(
        self,
        top_50: pd.DataFrame,
        top_n: int
    ) -> List[Dict]:
        """
        센티먼트 분석 및 Top N 선정

        Process:
            1. 50개 종목 뉴스 크롤링 (5일치)
            2. 각 종목별 STS 중복 제거 (ko-sbert-sts, threshold=0.66)
            3. 하나의 프롬프트로 LLM에게 1~50위 순위 요청
            4. 순위 → 점수 변환 (1위=10점, 50위=0점, 선형)
            5. 최종 점수 합산 (base 90% + sentiment 10%)
        """
        # Phase 2.2: 뉴스 크롤링 + 중복 제거
        logger.info("Phase 2.2: 50개 종목 뉴스 크롤링 (5일치) + STS 중복 제거...")
        news_by_ticker = await self._crawl_and_deduplicate_news(top_50)

        # Phase 2.3: 하나의 프롬프트로 LLM 센티먼트 순위 분석
        logger.info("Phase 2.3: LLM 센티먼트 순위 분석 (1-50위)...")
        sentiment_ranks = await self._analyze_sentiment_batch_all(news_by_ticker)

        # 순위 → 점수 변환 (1위=10점, 50위=0점)
        sentiment_scores = self._convert_ranks_to_scores(sentiment_ranks)

        # top_50에 센티먼트 점수 추가
        top_50['sentiment_score'] = top_50['ticker'].map(sentiment_scores).fillna(5.0)

        # Phase 2.4: 최종 점수 통합 (base 90% + sentiment 10%)
        logger.info("Phase 2.4: 최종 점수 통합 및 Top N 재선정...")
        top_50['final_score'] = (
            top_50['base_score'] * 0.90 +
            top_50['sentiment_score'] * 0.10
        )

        # Top N 선정
        top_n_df = top_50.nlargest(top_n, 'final_score')

        # 결과 포맷팅
        results = []
        for idx, row in top_n_df.iterrows():
            results.append({
                'ticker': row['ticker'],
                'name': row['name'],
                'market_cap': row['market_cap'],
                'momentum_score': round(row.get('momentum_score', 5.0), 2),
                'volume_score': round(row.get('volume_score', 5.0), 2),
                'technical_score': round(row['technical_score'], 2),
                'sentiment_score': round(row['sentiment_score'], 2),
                'base_score': round(row['base_score'], 2),
                'final_score': round(row['final_score'], 2)
            })

        return results

    # ============= 프롬프트 템플릿 =============

    def _build_morning_report_prompt(
        self,
        date: datetime,
        market_data: Dict,
        top_stocks: List[Dict]
    ) -> str:
        """
        장 시작 리포트 프롬프트 생성 (상세 진입 전략 포함)

        Returns:
            완성된 프롬프트 문자열
        """
        # Top 10 종목 포맷팅 (간결하게 한 줄씩)
        stocks_text = ""
        for i, stock in enumerate(top_stocks, 1):
            # 기본 정보
            line = f"{i}. {stock['name']} ({stock['ticker']}) - "
            line += f"점수: {stock['final_score']:.2f} "
            line += f"(M:{stock['momentum_score']:.1f}, V:{stock['volume_score']:.1f}, "
            line += f"T:{stock['technical_score']:.1f}, S:{stock['sentiment_score']:.1f})"

            # 가격 정보 (realtime_prices) + ATR
            if stock.get('realtime_price'):
                rt = stock['realtime_price']
                current_price = rt.get('current_price', 0)
                change_rate = rt.get('change_rate', 0)  # 전일 대비 등락률
                open_price = rt.get('open_price', 0)    # 시간외 시가 ≈ 정규장 종가

                # D-2 종가 역산: D-2 종가 = 현재가 / (1 + 등락률/100)
                if change_rate != 0:
                    d2_close = int(current_price / (1 + change_rate / 100))
                else:
                    d2_close = current_price

                # ATR 정보
                atr_info = ""
                if stock.get('atr'):
                    atr_info = f" | ATR {stock['atr']:,.0f}원 ({stock.get('atr_percent', 0):.1f}%)"

                if open_price > 0:
                    # 시간외 거래 있음
                    regular_change = (open_price - d2_close) / d2_close * 100 if d2_close > 0 else 0
                    after_hours_change = (current_price - open_price) / open_price * 100 if open_price > 0 else 0

                    line += f"{atr_info}\n"
                    line += f"   Price History:\n"
                    line += f"   - D-2 종가: {d2_close:,}원\n"
                    line += f"   - D-1 정규장 종가: {open_price:,}원 ({regular_change:+.1f}%)\n"
                    line += f"   - D-1 시간외 종가: {current_price:,}원 ({after_hours_change:+.1f}%)"
                else:
                    # 시간외 거래 없음
                    line += f"{atr_info}\n"
                    line += f"   Price History:\n"
                    line += f"   - D-2 종가: {d2_close:,}원\n"
                    line += f"   - D-1 정규장 종가: {current_price:,}원 ({change_rate:+.1f}%)"
            else:
                line += " | 가격정보 없음"

            stocks_text += line + "\n"

        prompt = f"""당신은 한국 주식 시장의 전문 전략가이자 단기 트레이딩 전문가입니다.

오늘({date.strftime('%Y-%m-%d')}) 장 시작 전 투자자가 알아야 할 정보를 분석하세요.

[전일 시장 데이터]
- KOSPI 종가: {market_data.get('kospi_close', 'N/A')}
- KOSPI 등락률: {market_data.get('kospi_change', 'N/A')}%
- 거래대금: {market_data.get('trading_value', 0):,}억원
- 외국인 순매수: {market_data.get('foreign_net', 0):,}억원
- 기관 순매수: {market_data.get('institution_net', 0):,}억원

[주목 종목 Top 10] (Momentum 40%, Volume 30%, Technical 20%, Sentiment 10% 기반)
{stocks_text}
※ D-2 = 그저께, D-1 = 어제 (오늘 장 시작 기준)
※ 시간외 거래가 있으면 오늘 장 시작가는 D-1 시간외 종가 부근에서 형성
※ ATR = 14일 평균 변동폭 (목표가/손절가 산정 기준)

**Google Search를 활용하여** 다음 정보를 수집하고 분석하세요:
1. 전일 미국 증시 (S&P500, 나스닥, VIX) 동향 및 시사점
2. 현재 달러/원 환율 및 외환시장 동향
3. 오늘의 주요 국제 이슈 (미국 금리, FOMC, 중국 경제지표, 지정학적 리스크 등)
4. 한국 주식 시장 주요 뉴스 및 업종별 이슈
5. 각 종목의 **최신 주가 정보** (현재가, 전일 종가, 지지선, 저항선)
6. 증권사 리포트 및 애널리스트 의견 (목표가 컨센서스)

다음 JSON 형식으로 응답하세요:

```json
{{
  "market_forecast": "오늘 시장 전망을 **상세하게** 분석 (5-7문장: 해외시장 영향, 환율, 외국인/기관 동향, 주요 이슈, 지수 방향성)",
  "kospi_range": {{"low": 예상_하단, "high": 예상_상단, "reasoning": "예상 근거 (2-3문장)"}},
  "market_risks": [
    "주요 리스크 요인 1",
    "주요 리스크 요인 2",
    "주요 리스크 요인 3"
  ],
  "top_stocks": [
    {{
      "rank": 1,
      "ticker": "종목코드",
      "name": "종목명",
      "current_price": 현재가_숫자 (Google Search로 조회),
      "reason": "오늘 주목해야 하는 구체적 이유 (3-4문장: 뉴스, 실적, 기술적 지표, 업종 동향 등)",
      "entry_strategy": {{
        "analysis": "【먼저 분석】 시간외 동향, ATR 변동성, 지지/저항 위치, 거래량 패턴 등 진입 판단 근거를 2-3문장으로 서술",
        "entry_price": 진입가_숫자 (원 단위, 예: 65000),
        "entry_timing": "진입 타이밍 (예: '시초가 9시 직후 진입' 또는 '전일 종가 돌파 시 진입')",
        "target_price_1": 1차_목표가_숫자 (진입가 + ATR×1.5~2.0),
        "target_price_2": 2차_목표가_숫자 (진입가 + ATR×2.5~3.0),
        "stop_loss": 손절가_숫자 (진입가 - ATR×1.5),
        "risk_reward_ratio": "손익비 (예: '1:2' 또는 '1:3')",
        "holding_period": "예상 보유기간 (예: '1-3일' 또는 '당일 청산')",
        "technical_basis": "기술적 근거 (지지선/저항선, 이동평균, RSI 등 2-3문장)",
        "volume_strategy": "거래량 전략 (예: '전일 평균 거래량 20% 이상 시 진입' 또는 '초반 거래량 급증 확인 후 진입')",
        "exit_condition": "청산 조건 (목표가 도달 외 추가 조건, 예: '상승 모멘텀 둔화 시 분할 매도')",
        "confidence": 0.85
      }}
    }},
    {{
      "rank": 2,
      "ticker": "종목코드",
      "name": "종목명",
      "current_price": 현재가_숫자,
      "reason": "주목 이유 (3-4문장)",
      "entry_strategy": {{
        "analysis": "【먼저 분석】 진입 판단 근거 2-3문장",
        "entry_price": 진입가_숫자,
        "entry_timing": "진입 타이밍",
        "target_price_1": 1차_목표가_숫자,
        "target_price_2": 2차_목표가_숫자,
        "stop_loss": 손절가_숫자,
        "risk_reward_ratio": "손익비",
        "holding_period": "예상 보유기간",
        "technical_basis": "기술적 근거 (2-3문장)",
        "volume_strategy": "거래량 전략",
        "exit_condition": "청산 조건",
        "confidence": 0.75
      }}
    }},
    ...  # Top 10 종목 모두 (10개)
  ],
  "sector_analysis": {{
    "bullish": [
      {{"sector": "강세 예상 업종1", "reason": "상승 근거 (1-2문장)"}},
      {{"sector": "강세 예상 업종2", "reason": "상승 근거 (1-2문장)"}},
      {{"sector": "강세 예상 업종3", "reason": "상승 근거 (1-2문장)"}}
    ],
    "bearish": [
      {{"sector": "약세 예상 업종1", "reason": "하락 근거 (1-2문장)"}},
      {{"sector": "약세 예상 업종2", "reason": "하락 근거 (1-2문장)"}}
    ]
  }},
  "investment_strategy": "오늘의 구체적 투자 전략 (6-8문장: 시장 대응 방안, 포지션 비중, 섹터 로테이션, 리스크 관리, 단기/중기 관점 제시)",
  "daily_schedule": {{
    "09:00_09:30": "장 시작 직후 전략 (예: 'Top 3 종목 시초가 확인 및 진입 기회 포착')",
    "10:00_11:30": "오전장 전략 (예: '외국인 매수 흐름 확인, 수급 강한 종목 추가 진입')",
    "13:00_15:00": "오후장 전략 (예: '목표가 도달 종목 분할 매도, 손절선 준수')",
    "15:00_15:30": "장 마감 전략 (예: '당일 청산 종목 정리, 익일 전략 수립')"
  }}
}}
```

**중요 지침:**
1. **top_stocks는 반드시 Top 10 종목 전체(10개)를 순서대로 분석**
2. **entry_strategy의 모든 가격(entry_price, target_price_1/2, stop_loss)은 Google Search로 최신 주가를 조회한 후 구체적 숫자로 제시**
3. **ATR 기반 목표가/손절가 설정 방법:**
   - 단기(1-3일): 목표가 = 진입가 + (ATR × 1.5~2.0), 손절가 = 진입가 - (ATR × 1.5)
   - 스윙(3-7일): 목표가 = 진입가 + (ATR × 2.5~3.0), 손절가 = 진입가 - (ATR × 2.0)
   - ATR이 클수록 변동성 높음 → 보수적 진입, ATR이 작으면 → 타이트한 손절
   - [시간외O] 종목: 시간외 급등/급락 시 갭 리스크 고려, 조정 대기 또는 관망 권고
4. **confidence (0.0~1.0) 산정 기준:**
   - 0.8~1.0: ATR 목표가가 지지/저항과 일치 + 강한 모멘텀 + 수급 양호
   - 0.6~0.8: 일부 불확실성 (시간외 급등, 외부 변수, 거래량 부족)
   - 0.4~0.6: 데이터 부족, 고변동성, 역추세 진입
5. **손익비 최소 1:1.5 이상 유지**
6. **반드시 최신 정보 반영 (Google Search 활용 필수)**

JSON만 반환하세요 (추가 설명 없이).
"""
        return prompt

    def _build_afternoon_report_prompt(
        self,
        date: datetime,
        market_summary: Dict,
        surge_stocks: List[Dict]
    ) -> str:
        '''
        장 마감 리포트 프롬프트 생성 (증권사 장마감 시황 보고서 형식)

        Args:
            date: 보고서 날짜
            market_summary: 확장된 시장 데이터 (get_market_index_extended() 결과)
                - KOSPI/KOSDAQ 지수
                - 외국인/기관/개인 수급 (시장별)
                - 시장 폭 (상승/하락/보합 종목 수)
            surge_stocks: 급등주 리스트
        '''
        # 급등주 데이터 포맷팅 (상위 10개)
        surge_text = ""
        for i, stock in enumerate(surge_stocks, 1):
            surge_text += f"{i}. {stock['name']} ({stock['ticker']}) - "
            surge_text += f"등락률: {stock.get('change_rate', 0):.2f}%, "
            surge_text += f"거래량: {stock.get('volume', 0):,}주\n"

        # 확장된 시장 데이터 추출
        kospi_close = market_summary.get('kospi_close', 0)
        kospi_change = market_summary.get('kospi_change', 0)
        kospi_point = market_summary.get('kospi_point_change', 0)

        kosdaq_close = market_summary.get('kosdaq_close', 0)
        kosdaq_change = market_summary.get('kosdaq_change', 0)
        kosdaq_point = market_summary.get('kosdaq_point_change', 0)

        trading_value = market_summary.get('trading_value', 0) # 억원 단위

        # 수급 데이터 (억원 단위 변환)
        foreign_kospi = market_summary.get('foreign_net_kospi', 0)
        institution_kospi = market_summary.get('institution_net_kospi', 0)
        individual_kospi = market_summary.get('individual_net_kospi', 0)

        foreign_kosdaq = market_summary.get('foreign_net_kosdaq', 0)
        institution_kosdaq = market_summary.get('institution_net_kosdaq', 0)
        individual_kosdaq = market_summary.get('individual_net_kosdaq', 0)

        # 시장 폭
        advance = market_summary.get('advance_count', 0)
        decline = market_summary.get('decline_count', 0)
        unchanged = market_summary.get('unchanged_count', 0)

        prompt = f"""당신은 한국 주식 시장의 마감 시황 전문 애널리스트입니다.

오늘({date.strftime('%Y-%m-%d')}) 장 마감 후 투자자들을 위한 일일 리포트를 작성하세요.

[오늘의 시장 데이터]

■ 지수 동향
- KOSPI: {kospi_close:,.2f} ({kospi_change:+.2f}%, {kospi_point:+.2f}p)
- KOSDAQ: {kosdaq_close:,.2f} ({kosdaq_change:+.2f}%, {kosdaq_point:+.2f}p)
- 거래대금: {trading_value:,}억원

■ 수급 동향 (KOSPI / KOSDAQ)
- 외국인: {foreign_kospi:+,}억 / {foreign_kosdaq:+,}억원
- 기관: {institution_kospi:+,}억 / {institution_kosdaq:+,}억원
- 개인: {individual_kospi:+,}억 / {individual_kosdaq:+,}억원

■ 시장 폭 (Market Breadth)
- 상승: {advance:,}개 / 하락: {decline:,}개 / 보합: {unchanged:,}개

[오늘 포착된 주요 급등주 (Top 10)]
{surge_text}

**Google Search를 활용하여** 다음 정보를 심층 분석하고, 결과를 활용하여 응답하세요:
1. 오늘 시장의 등락 원인 (해외 증시 영향, 주요 경제 지표 발표, 수급 쏠림 등)
2. **업종별 등락률 분석** - 강세/약세 업종 TOP 3씩 (전기전자, 바이오, 금융 등)
3. **수급 해석** - 외국인/기관/개인의 포지션 의미 (매수/매도 이유 추론)
4. **오늘 급등한 종목들의 구체적인 상승 재료** (공시, 뉴스, 테마, 실적 등)
5. 시간외 거래 특이사항 및 내일 시장에 영향을 줄 주요 일정

다음 JSON 형식으로 응답하세요:

```json
{{
  "market_summary_text": "KOSPI/KOSDAQ 동향 요약 (3-4문장: 지수 등락 원인과 특징)",

  "market_breadth": {{
    "sentiment": "강세장 | 약세장 | 혼조세",
    "interpretation": "상승/하락 종목 비율 기반 시장 분위기 해석 (1-2문장)"
  }},

  "sector_analysis": {{
    "bullish": [
      {{"sector": "강세 업종명", "change": "+2.5", "reason": "상승 이유 (1문장)"}}
    ],
    "bearish": [
      {{"sector": "약세 업종명", "change": "-1.8", "reason": "하락 이유 (1문장)"}}
    ]
  }},

  "supply_demand_analysis": "외국인/기관/개인 수급 해석 (2-3문장: 누가 왜 샀고/팔았는지)",

  "today_themes": [
    {{
      "theme": "오늘의 주도 테마명",
      "drivers": "상승 원인",
      "leading_stocks": ["대장주1", "대장주2"]
    }}
  ],

  "surge_analysis": [
    {{
      "ticker": "종목코드",
      "name": "종목명",
      "category": "테마/업종",
      "reason": "구체적인 급등 사유 (뉴스/공시 기반 1-2문장)",
      "outlook": "단기 전망"
    }}
  ],

  "tomorrow_strategy": "내일 투자 전략 (4-5문장: 예상 시장 방향, 주목 섹터, 리스크 관리)",

  "check_points": [
    "내일 확인해야 할 주요 일정/이슈 1",
    "내일 확인해야 할 주요 일정/이슈 2"
  ]
}}
```

**중요 지침:**
1. 단순히 수치를 나열하지 말고, **'왜' 올랐는지 뉴스 검색 결과를 바탕으로 해석**하세요.
2. `sector_analysis`에는 실제 업종별 등락률을 검색하여 강세/약세 각 2-3개씩 제시하세요.
3. `supply_demand_analysis`에서 수급 데이터의 의미를 해석하세요 (예: 외국인 대량 매도는 글로벌 리스크 회피 심리).
4. `surge_analysis`에는 특별한 재료(뉴스, 공시)가 있는 종목 위주로 3-5개 분석하세요.
5. 투자자에게 실질적인 도움이 되는 인사이트를 제공하세요.

JSON만 반환하세요.
"""
        return prompt
    # ============= 데이터 포맷팅 =============

    def _format_top_stocks(self, stocks: List[Dict]) -> str:
        """주목 종목을 텍스트로 포맷 (Top 5)"""
        if not stocks:
            return "주목 종목 없음"

        result = []
        for i, stock in enumerate(stocks[:5], 1):
            result.append(
                f"{i}. {stock.get('name', 'N/A')} ({stock.get('ticker', 'N/A')}) - "
                f"점수: {stock.get('score', 0):.2f}, "
                f"현재가: {stock.get('current_price', 0):,}원"
            )
        return "\n".join(result)

    # ============= Morning Report 헬퍼 메서드 =============

    async def _collect_market_data(self, date: datetime) -> Dict:
        """
        시장 데이터 수집 (전일 KOSPI)

        Args:
            date: 오늘 날짜 (이 날짜 기준 전일 거래일 데이터 조회)

        Returns:
            {
                'kospi_close': float,
                'kospi_change': float,
                'trading_value': int,
                'foreign_net': int,
                'institution_net': int
            }
        """
        try:
            # 전일 거래일 찾기 (오늘 기준)
            prev_trading_day = await self.data_service.get_previous_trading_day(date)
            logger.info(f"전일 거래일: {prev_trading_day.strftime('%Y-%m-%d')}")

            # 전일 KOSPI 데이터 조회
            market_index = await self.data_service.get_market_index(prev_trading_day)

            result = {
                'kospi_close': market_index.get('kospi_close', 0.0),
                'kospi_change': market_index.get('kospi_change', 0.0),
                'trading_value': market_index.get('trading_value', 0) // 100000000,  # 억원 단위
                'foreign_net': market_index.get('foreign_net', 0) // 100000000,  # 억원 단위
                'institution_net': market_index.get('institution_net', 0) // 100000000  # 억원 단위
            }

            logger.info(f"KOSPI: {result['kospi_close']:.2f} ({result['kospi_change']:+.2f}%)")
            return result

        except Exception as e:
            logger.error(f"시장 데이터 수집 실패: {e}")
            return {
                'kospi_close': 0.0,
                'kospi_change': 0.0,
                'trading_value': 0,
                'foreign_net': 0,
                'institution_net': 0
            }

    # ============= 센티먼트 분석 헬퍼 메서드 =============

    async def _crawl_and_deduplicate_news(
        self,
        top_50: pd.DataFrame
    ) -> Dict[str, List[Dict]]:
        """
        50개 종목의 뉴스 크롤링 + STS 중복 제거

        Args:
            top_50: Top 50 종목 DataFrame (ticker, name 컬럼 필수)

        Returns:
            {ticker: [중복 제거된 뉴스 목록]}
        """
        news_by_ticker = {}

        for idx, row in top_50.iterrows():
            ticker = row['ticker']
            name = row.get('name', ticker)

            try:
                # 뉴스 크롤링 (최신 10페이지)
                news_list = await self.data_service.get_news_data(ticker, days=5)

                if not news_list:
                    logger.warning(f"{ticker} ({name}): 뉴스 없음")
                    news_by_ticker[ticker] = []
                    continue

                # 5일 이내 뉴스만 필터링
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=5)
                recent_news = [
                    news for news in news_list
                    if news.get('published_at', datetime.min) >= cutoff_date
                ]

                logger.info(f"{ticker} ({name}): 뉴스 {len(news_list)}개 → 5일 이내 {len(recent_news)}개")

                # STS 중복 제거 (ko-sbert-sts, threshold=0.66)
                deduplicated_news = deduplicate_news(
                    recent_news,
                    threshold=0.66
                )

                logger.info(f"{ticker} ({name}): 중복 제거 후 {len(deduplicated_news)}개")
                news_by_ticker[ticker] = deduplicated_news

            except Exception as e:
                logger.error(f"{ticker} ({name}): 뉴스 크롤링 실패 - {e}")
                news_by_ticker[ticker] = []

        return news_by_ticker

    async def _analyze_sentiment_batch_all(
        self,
        news_by_ticker: Dict[str, List[Dict]]
    ) -> Dict[str, int]:
        """
        하나의 프롬프트로 LLM에게 50개 종목의 센티먼트 순위 요청

        Args:
            news_by_ticker: {ticker: [뉴스 목록]}

        Returns:
            {ticker: rank}  # rank: 1 (가장 긍정) ~ 50 (가장 부정)
        """
        # 프롬프트 구성: 50개 종목의 뉴스 제목을 모두 포함
        prompt = """다음 50개 종목의 최근 5일 뉴스를 분석하여, **뉴스 센티먼트가 가장 긍정적인 순서대로 1~50위까지 순위를 매겨주세요.**

각 종목의 뉴스 제목을 기반으로:
- 긍정적 뉴스 (실적 개선, 신기술, 신규 계약, 정부 지원 등)가 많을수록 높은 순위
- 부정적 뉴스 (실적 악화, 소송, 규제, 경영 리스크 등)가 많을수록 낮은 순위
- 뉴스가 없거나 중립적인 경우 중간 순위

**중요**: 1위가 가장 긍정적이고, 50위가 가장 부정적입니다.

"""

        # 종목별 뉴스 제목 추가
        for ticker, news_list in news_by_ticker.items():
            if not news_list:
                prompt += f"\n[{ticker}]\n뉴스 없음\n"
            else:
                titles = [news.get('title', '') for news in news_list[:20]]  # 최대 20개 제목
                prompt += f"\n[{ticker}]\n"
                for i, title in enumerate(titles, 1):
                    prompt += f"{i}. {title}\n"

        # JSON 형식 요청
        prompt += """

**응답 형식 (JSON)**:
```json
{
  "rankings": [
    {"ticker": "005930", "rank": 1, "reason": "긍정적 실적 발표 및 신기술 개발 뉴스"},
    {"ticker": "000660", "rank": 2, "reason": "..."},
    ...
    {"ticker": "123456", "rank": 50, "reason": "부정적 경영 리스크 및 실적 악화"}
  ]
}
```

JSON만 반환하세요 (추가 설명 없이).
"""

        try:
            # LLM 호출 (JSON 모드)
            logger.info("LLM에게 50개 종목 센티먼트 순위 요청 중...")
            response_text = await self.generate(prompt, temperature=0.3)

            # JSON 파싱
            # Gemini는 ```json ... ``` 로 감쌀 수 있으므로 제거
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            result = json.loads(response_text)
            rankings = result.get('rankings', [])

            # {ticker: rank} 딕셔너리 생성
            sentiment_ranks = {}
            for item in rankings:
                ticker = item.get('ticker')
                rank = item.get('rank')
                if ticker and rank:
                    sentiment_ranks[ticker] = int(rank)

            logger.info(f"센티먼트 순위 분석 완료: {len(sentiment_ranks)}개 종목")
            return sentiment_ranks

        except Exception as e:
            logger.error(f"센티먼트 순위 분석 실패: {e}")
            # 실패 시 모두 중립 순위 반환
            return {ticker: 25 for ticker in news_by_ticker.keys()}

    def _convert_ranks_to_scores(
        self,
        sentiment_ranks: Dict[str, int]
    ) -> Dict[str, float]:
        """
        순위를 점수로 변환 (1위=10점, 50위=0점, 선형)

        Args:
            sentiment_ranks: {ticker: rank}  # 1~50

        Returns:
            {ticker: score}  # 0.0~10.0
        """
        sentiment_scores = {}

        for ticker, rank in sentiment_ranks.items():
            # 선형 변환: rank 1 → 10.0, rank 50 → 0.0
            # score = 10 - (rank - 1) * (10 / 49)
            score = 10.0 - (rank - 1) * (10.0 / 49.0)
            score = max(0.0, min(10.0, score))  # 0-10 범위 클리핑
            sentiment_scores[ticker] = round(score, 2)

        return sentiment_scores
