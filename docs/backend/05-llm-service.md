# LLM 서비스 (Gemini 2.5 Pro)

## 📌 문서 목적

Gemini 2.5 Pro API 통합 방법, 프롬프트 템플릿 설계, 토큰 최적화 전략, Rate Limiting, 에러 핸들링을 상세히 설명합니다.

---

## 🎯 LLM 서비스 개요

### 사용 목적
1. **기업 분석**: 재무+기술+뉴스 종합 분석
2. **장 리포트**: 시장 전망 및 주목 종목 선정
3. **급등주 분석**: 급등 이유 및 전략 제시

### Gemini 2.5 Pro 선정 이유
- **비용**: GPT-4 대비 50% 저렴
- **성능**: 긴 컨텍스트 지원 (1M 토큰)
- **속도**: 평균 응답 시간 3-5초
- **안정성**: Google 인프라

---

## 🔧 Gemini API 통합

### 설치

```bash
pip install google-generativeai
```

### 초기화

```python
import google.generativeai as genai
import os
from typing import Optional, Dict, Any

class GeminiService:
    def __init__(self):
        # API 키 설정
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        genai.configure(api_key=api_key)

        # 모델 설정
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "temperature": 0.3,  # 창의성 낮춤 (일관성↑)
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 4000,
            },
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        )

        # Rate Limiter
        self.rate_limiter = RateLimiter(
            max_requests=60,  # 분당 60회
            time_window=60
        )

    async def generate(
        self,
        prompt: str,
        stream: bool = False
    ) -> str:
        """
        Gemini API 호출

        Args:
            prompt: 입력 프롬프트
            stream: 스트리밍 모드 (기본 False)

        Returns:
            생성된 텍스트
        """
        # Rate Limiting
        await self.rate_limiter.acquire()

        try:
            if stream:
                # 스트리밍 모드
                response = await self.model.generate_content_async(
                    prompt,
                    stream=True
                )
                chunks = []
                async for chunk in response:
                    chunks.append(chunk.text)
                return "".join(chunks)
            else:
                # 일반 모드
                response = await self.model.generate_content_async(prompt)
                return response.text

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise LLMAPIError(f"Failed to generate content: {e}")
```

---

## 📝 프롬프트 템플릿

### 1. 기업 분석 프롬프트

```python
COMPANY_ANALYSIS_PROMPT = """
당신은 한국 주식 시장의 전문 애널리스트입니다. 다음 기업에 대한 종합 분석 보고서를 작성하세요.

# 기업 정보
- 종목명: {company_name}
- 종목코드: {company_code}
- 현재가: {current_price:,}원
- 시가총액: {market_cap:,}억원
- 업종: {sector}

# 재무 데이터
{financial_data}

# 최근 뉴스 (최근 7일)
{news_summary}

# 기술적 지표
{technical_indicators}

---

다음 형식으로 분석 보고서를 작성하세요:

## 1. 요약
- **투자의견**: [강력 매수 / 매수 / 중립 / 매도 / 강력 매도] 중 하나 선택
- **목표가**: 구체적인 금액 (예: 85,000원)
- **핵심 근거**: 3줄로 요약

## 2. 재무 분석
### 수익성
- 매출, 영업이익, 순이익 분석
- ROE, ROA 등 수익성 지표 평가

### 성장성
- 최근 3년 성장률
- 향후 성장 전망

### 안정성
- 부채비율, 유동비율 평가
- 재무 건전성 종합 판단

### 밸류에이션
- PER, PBR 분석
- 업종 평균 대비 평가 (저평가/적정/고평가)

## 3. 산업 및 경쟁 분석
- 업종 트렌드
- 시장 점유율 및 경쟁 우위
- 주요 경쟁사 비교

## 4. 뉴스 분석
- 주요 이슈 요약
- 센티먼트 분석 (긍정/부정/중립)
- 향후 영향 전망

## 5. 기술적 분석
- 현재 추세 (상승/하락/횡보)
- 주요 지표 (RSI, MACD, 이동평균) 해석
- 지지/저항선 분석

## 6. 리스크 요인
최소 3가지 리스크를 구체적으로 제시:
1. [리스크 유형]: 설명
2. [리스크 유형]: 설명
3. [리스크 유형]: 설명

## 7. 투자 전략
### 단기 (1-3개월)
- 진입 가격대
- 목표가
- 손절가
- 포지션 크기

### 중기 (3-12개월)
- 모니터링 포인트
- 재평가 시점

### 장기 (1년 이상)
- 장기 보유 근거
- 리밸런싱 전략

---

**중요**:
- 모든 주장에는 구체적인 수치와 근거를 제시하세요
- 리스크를 명확히 언급하세요
- 투자 권유가 아닌 참고 자료임을 명시하세요
- 한국어로 작성하되, 전문 용어를 적절히 사용하세요
"""
```

**프롬프트 구성 함수**:
```python
def build_company_analysis_prompt(
    ticker: str,
    stock_data: Dict,
    financial_data: Dict,
    news_data: List[Dict],
    technical_data: Dict
) -> str:
    """
    기업 분석 프롬프트 생성

    Args:
        ticker: 종목 코드
        stock_data: 기본 정보
        financial_data: 재무 데이터
        news_data: 뉴스 데이터
        technical_data: 기술적 지표

    Returns:
        완성된 프롬프트
    """
    # 재무 데이터 포맷팅
    financial_str = f"""
- 매출액: {financial_data['revenue']:,}억원
- 영업이익: {financial_data['operating_profit']:,}억원 (영업이익률: {financial_data['operating_margin']:.1f}%)
- 순이익: {financial_data['net_profit']:,}억원 (순이익률: {financial_data['net_margin']:.1f}%)
- ROE: {financial_data['roe']:.1f}%
- ROA: {financial_data['roa']:.1f}%
- 부채비율: {financial_data['debt_ratio']:.1f}%
- PER: {financial_data['per']:.1f}
- PBR: {financial_data['pbr']:.1f}
"""

    # 뉴스 요약
    news_str = "\n".join([
        f"[{news['date']}] {news['title']}\n  → {news['summary']}"
        for news in news_data[:5]  # 최근 5개
    ])

    # 기술적 지표 포맷팅
    technical_str = f"""
- RSI (14일): {technical_data['rsi']:.1f}
- MACD: {technical_data['macd']['value']:.1f} (Signal: {technical_data['macd']['signal']:.1f})
- 이동평균:
  - 5일: {technical_data['ma_5']:,}원
  - 20일: {technical_data['ma_20']:,}원
  - 60일: {technical_data['ma_60']:,}원
- 현재가 vs MA20: {"상회" if stock_data['current_price'] > technical_data['ma_20'] else "하회"}
"""

    # 프롬프트 완성
    return COMPANY_ANALYSIS_PROMPT.format(
        company_name=stock_data['name'],
        company_code=ticker,
        current_price=stock_data['current_price'],
        market_cap=stock_data['market_cap'] // 100000000,  # 억원 단위
        sector=stock_data['sector'],
        financial_data=financial_str,
        news_summary=news_str,
        technical_indicators=technical_str
    )
```

---

### 2. 장 시작 리포트 프롬프트

```python
MARKET_OPENING_PROMPT = """
당신은 한국 주식 시장의 전문 전략가입니다. 오늘({date}) 장 시작 전 투자자가 알아야 할 정보를 제공하세요.

# 전일 시장 데이터
- KOSPI: {kospi_close:,} ({kospi_change:+.2f}%)
- KOSDAQ: {kosdaq_close:,} ({kosdaq_change:+.2f}%)
- 거래대금: {trading_value:,}억원
- 외국인 순매수: {foreign_net:+,}억원
- 기관 순매수: {institution_net:+,}억원

# 해외 시장
- 미국 S&P500: {sp500_change:+.2f}%
- 미국 NASDAQ: {nasdaq_change:+.2f}%
- 달러/원: {usd_krw:,}원 ({usd_krw_change:+.0f}원)

# 주목 종목 Top 5 (Metric 기반)
{top_stocks}

# 주요 뉴스
{major_news}

---

다음 형식으로 리포트를 작성하세요:

## 1. 시장 전망
- 오늘의 시장 방향성 예측 (상승/하락/횡보)
- 예상 변동 범위 (KOSPI 기준)
- 핵심 영향 요인 3가지

## 2. 주목 종목 Top 5
각 종목에 대해:
- **종목명 (티커)**
- 선정 이유 (구체적 수치 포함)
- 진입 전략 (가격대, 타이밍)
- 목표가 및 손절가
- 주요 촉매 (Catalyst)

## 3. 섹터 분석
- 강세 예상 섹터 (3개)
  - 섹터명, 이유, 대표 종목
- 약세 예상 섹터 (2개)
  - 섹터명, 이유, 회피 종목

## 4. 투자 전략
- 전체적인 스탠스 (공격적/중립적/보수적)
- 추천 포트폴리오 구성 비율
- 주의사항 및 리스크 요인

## 5. 주요 일정
오늘 주목해야 할 이벤트 (시간대별)

---

**작성 가이드**:
- 구체적인 수치와 근거 제시
- 낙관/비관 양쪽 시나리오 고려
- 투자 권유가 아닌 참고 자료임을 명시
"""
```

---

### 3. 장 마감 리포트 프롬프트

```python
MARKET_CLOSING_PROMPT = """
당신은 한국 주식 시장의 전문 애널리스트입니다. 오늘({date}) 장 마감 후 시장 분석과 내일 전략을 제시하세요.

# 당일 시장 데이터
- KOSPI: {kospi_close:,} ({kospi_change:+.2f}%)
- KOSDAQ: {kosdaq_close:,} ({kosdaq_change:+.2f}%)
- 거래대금: {trading_value:,}억원
- 외국인 순매수: {foreign_net:+,}억원
- 상승 종목 수: {up_stocks}개 / 하락 종목 수: {down_stocks}개

# 급등주 분석 (오후 트리거)
{trigger_stocks}

# 주요 뉴스
{major_news}

---

다음 형식으로 리포트를 작성하세요:

## 1. 당일 시장 요약
- 시장 방향성 평가
- 주요 움직임 (외국인/기관/개인)
- 강세/약세 섹터

## 2. 급등주 상세 분석
각 급등주에 대해:
- **종목명 (티커)** - 급등 이유
- 기술적 분석
- 향후 전망
- 투자 전략 (진입 여부, 익절 타이밍)

## 3. 내일 전략
- 예상 시장 방향
- 주목 종목 및 섹터
- 투자 포인트
- 주의사항

## 4. 주요 이벤트 (내일)
내일 주목해야 할 일정
"""
```

---

## 💰 토큰 최적화 전략

### 1. 프롬프트 압축

```python
def compress_news_data(news_list: List[Dict]) -> str:
    """
    뉴스 데이터 압축

    전략:
    - 최근 5개만 선택
    - 중복 제거
    - 요약만 포함 (본문 제외)
    """
    # 중복 제거 (제목 기준)
    unique_news = {news['title']: news for news in news_list}
    unique_list = list(unique_news.values())

    # 최신순 정렬
    sorted_news = sorted(
        unique_list,
        key=lambda x: x['date'],
        reverse=True
    )[:5]

    # 압축 포맷
    compressed = []
    for news in sorted_news:
        # 본문 제외, 제목과 요약만
        compressed.append(
            f"[{news['date']}] {news['title'][:50]}..."  # 50자 제한
        )

    return "\n".join(compressed)
```

### 2. 캐싱 활용

```python
async def get_analysis_with_cache(
    ticker: str,
    date: str
) -> Dict:
    """
    캐시 우선 조회 → LLM 호출 최소화
    """
    # 1. 캐시 조회
    cache_key = f"analysis:{ticker}:{date}"
    cached = await redis.get(cache_key)

    if cached:
        logger.info(f"Cache hit for {ticker}")
        return json.loads(cached)

    # 2. LLM 호출 (캐시 미스)
    logger.info(f"Cache miss for {ticker}, calling LLM...")
    analysis = await generate_analysis_with_llm(ticker)

    # 3. 캐시 저장 (TTL: 24시간)
    await redis.setex(cache_key, 86400, json.dumps(analysis))

    return analysis
```

### 3. 배치 처리

```python
async def analyze_multiple_stocks_batch(
    tickers: List[str]
) -> List[Dict]:
    """
    여러 종목을 한 번의 LLM 호출로 분석

    장점: API 호출 횟수 감소
    단점: 응답 시간 증가, 정확도 약간 하락
    """
    # 배치 프롬프트 생성
    batch_prompt = "다음 종목들을 각각 간략히 분석하세요:\n\n"

    for ticker in tickers:
        stock_data = await get_stock_data(ticker)
        batch_prompt += f"### {stock_data['name']} ({ticker})\n"
        batch_prompt += f"현재가: {stock_data['price']:,}원\n"
        batch_prompt += f"PER: {stock_data['per']:.1f}\n\n"

    # 한 번에 호출
    response = await gemini_service.generate(batch_prompt)

    # 응답 파싱
    return parse_batch_response(response)
```

---

## 🚦 Rate Limiting

### 구현

```python
import asyncio
from collections import deque
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, time_window: int):
        """
        Args:
            max_requests: 최대 요청 수
            time_window: 시간 윈도우 (초)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Rate limit 체크 및 대기"""
        async with self.lock:
            now = datetime.now()

            # 오래된 요청 제거
            while self.requests:
                if (now - self.requests[0]) > timedelta(seconds=self.time_window):
                    self.requests.popleft()
                else:
                    break

            # Rate limit 체크
            if len(self.requests) >= self.max_requests:
                # 대기 시간 계산
                oldest_request = self.requests[0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                wait_seconds = (wait_until - now).total_seconds()

                if wait_seconds > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_seconds:.1f}s")
                    await asyncio.sleep(wait_seconds)

            # 요청 기록
            self.requests.append(now)
```

### 사용 예시

```python
# 분당 60회 제한
rate_limiter = RateLimiter(max_requests=60, time_window=60)

async def call_llm_with_limit(prompt: str) -> str:
    await rate_limiter.acquire()
    return await gemini_service.generate(prompt)
```

---

## ⚠️ 에러 핸들링

### 재시도 로직

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

class LLMAPIError(Exception):
    pass

class LLMRateLimitError(Exception):
    pass

@retry(
    retry=retry_if_exception_type((LLMAPIError, LLMRateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=60)
)
async def generate_with_retry(prompt: str) -> str:
    """
    재시도 로직이 포함된 LLM 호출

    - LLMAPIError: 일반 에러 → 3회 재시도
    - LLMRateLimitError: Rate Limit → 지수 백오프
    """
    try:
        response = await gemini_service.generate(prompt)
        return response

    except genai.types.RateLimitError as e:
        logger.warning(f"Rate limit error: {e}")
        raise LLMRateLimitError(str(e))

    except Exception as e:
        logger.error(f"LLM API error: {e}")
        raise LLMAPIError(str(e))
```

### Fallback 전략

```python
async def generate_analysis_with_fallback(
    ticker: str
) -> Dict:
    """
    LLM 실패 시 Fallback

    1순위: Gemini
    2순위: 캐시된 유사 분석
    3순위: Rule-based 분석
    """
    try:
        # 1순위: Gemini
        return await generate_with_llm(ticker)

    except LLMAPIError:
        # 2순위: 캐시된 유사 분석
        logger.warning(f"LLM failed for {ticker}, using cached similar analysis")
        cached = await get_similar_cached_analysis(ticker)
        if cached:
            return cached

        # 3순위: Rule-based 분석
        logger.warning(f"No cache for {ticker}, using rule-based analysis")
        return generate_rule_based_analysis(ticker)
```

---

## 📊 비용 추정 및 모니터링

### 비용 계산

```python
class CostTracker:
    # Gemini 2.5 Pro 가격 (2025년 기준 예시)
    INPUT_COST_PER_1K = 0.000125  # USD
    OUTPUT_COST_PER_1K = 0.000375  # USD

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_usage(self, input_tokens: int, output_tokens: int):
        """토큰 사용량 기록"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def get_total_cost(self) -> float:
        """총 비용 계산 (USD)"""
        input_cost = (self.total_input_tokens / 1000) * self.INPUT_COST_PER_1K
        output_cost = (self.total_output_tokens / 1000) * self.OUTPUT_COST_PER_1K
        return input_cost + output_cost

    def get_daily_report(self) -> Dict:
        """일일 사용량 리포트"""
        return {
            "date": datetime.now().date(),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_cost_usd": self.get_total_cost(),
            "total_cost_krw": self.get_total_cost() * 1320  # 환율 적용
        }
```

### 예상 비용 (월 기준)

```python
# 기업 분석
# - 프롬프트: 약 1500 토큰
# - 응답: 약 2000 토큰
# - 100개 종목 × 30일 = 3000회

input_tokens = 1500 * 3000 = 4,500,000
output_tokens = 2000 * 3000 = 6,000,000

input_cost = (4,500,000 / 1000) * 0.000125 = $0.56
output_cost = (6,000,000 / 1000) * 0.000375 = $2.25
total_analysis = $2.81

# 장 리포트
# - 프롬프트: 약 800 토큰
# - 응답: 약 1500 토큰
# - 2회 × 30일 = 60회

input_tokens = 800 * 60 = 48,000
output_tokens = 1500 * 60 = 90,000

input_cost = (48,000 / 1000) * 0.000125 = $0.006
output_cost = (90,000 / 1000) * 0.000375 = $0.034
total_reports = $0.04

# 총 예상 비용
월 총비용 = $2.81 + $0.04 = $2.85 (약 3,762원)
```

**결론**: 캐싱 전략 적용 시 월 $3 이하로 운영 가능

---

## 📚 참고 자료

- [Gemini API 공식 문서](https://ai.google.dev/docs)
- [google-generativeai Python SDK](https://github.com/google/generative-ai-python)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
