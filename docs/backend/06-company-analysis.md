# 기업 분석 서비스 (Company Analysis)

## 📌 문서 목적

기업 분석 서비스의 전체 흐름, 데이터 수집, LLM 프롬프트 구성, 분석 결과 구조, 캐싱 전략을 설명합니다.

---

## 🎯 기업 분석 개요

### 목적
종목에 대한 종합 분석 보고서 생성 (재무 + 기술 + 뉴스 + 산업 분석)

### 실행 트리거
1. **사용자 요청**: 명시적 분석 요청
2. **배치 생성**: 장 마감 후 주요 종목 자동 분석
3. **이벤트 기반**: 중요 공시 발생 시

### 캐싱 전략
- **TTL**: 24시간
- **무효화**: 중요 공시, 급등/급락 (10% 이상)

---

## 🔄 분석 흐름

```
사용자 요청
    ↓
캐시 조회 (Redis)
    ↓
┌───────────┐
│Cache Hit? │
└─────┬─────┘
      │
  YES │ NO
      │
      ↓                    ↓
  반환 ← ─────────────→ 데이터 수집
                          ├─ 재무 (DART)
                          ├─ 뉴스 (Naver/Firecrawl)
                          ├─ 기술적 (pykrx)
                          └─ 가격 (pykrx)
                          ↓
                       LLM 분석 (Gemini)
                          ↓
                       결과 저장
                          ├─ DB
                          └─ Redis (캐시)
                          ↓
                       반환
```

---

## 📊 데이터 수집

### 1. 재무 데이터 (DART API)

```python
async def collect_financial_data(ticker: str) -> Dict:
    """
    DART API를 통한 재무제표 수집
    """
    # DART API 호출
    dart_api = DartAPI(api_key=os.getenv("DART_API_KEY"))

    # 최근 분기 재무제표
    financial_stmt = await dart_api.get_financial_statement(
        corp_code=ticker,
        report_type="Q"  # 분기
    )

    return {
        "revenue": financial_stmt["매출액"],
        "operating_profit": financial_stmt["영업이익"],
        "net_profit": financial_stmt["당기순이익"],
        "operating_margin": (
            financial_stmt["영업이익"] / financial_stmt["매출액"] * 100
        ),
        "net_margin": (
            financial_stmt["당기순이익"] / financial_stmt["매출액"] * 100
        ),
        "roe": financial_stmt["ROE"],
        "roa": financial_stmt["ROA"],
        "debt_ratio": financial_stmt["부채비율"],
        "current_ratio": financial_stmt["유동비율"],
        "per": financial_stmt["PER"],
        "pbr": financial_stmt["PBR"]
    }
```

### 2. 뉴스 데이터 (크롤링)

```python
async def collect_news_data(
    company_name: str,
    days: int = 7
) -> List[Dict]:
    """
    네이버 금융 뉴스 크롤링
    """
    news_list = []

    # 네이버 금융 검색
    url = f"https://finance.naver.com/search/searchList.nhn?query={company_name}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = soup.select('.articleSubject')

        for article in articles[:10]:  # 최근 10개
            title = article.get_text(strip=True)
            link = article['href']

            # 기사 본문 수집
            detail_response = await client.get(link)
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            content = detail_soup.select_one('.article_body').get_text(strip=True)

            # LLM으로 센티먼트 분석
            sentiment = await analyze_sentiment(title + " " + content)

            news_list.append({
                "title": title,
                "link": link,
                "content": content[:500],  # 500자로 제한
                "sentiment": sentiment,  # positive/neutral/negative
                "score": sentiment['score']  # 0-1
            })

    return news_list
```

### 3. 기술적 지표 (pykrx)

```python
async def collect_technical_data(ticker: str) -> Dict:
    """
    기술적 지표 계산
    """
    from pykrx import stock
    from datetime import datetime, timedelta

    # 최근 60일 가격 데이터
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)

    df = stock.get_market_ohlcv_by_date(
        start_date.strftime("%Y%m%d"),
        end_date.strftime("%Y%m%d"),
        ticker
    )

    # 이동평균 계산
    df['MA_5'] = df['종가'].rolling(window=5).mean()
    df['MA_20'] = df['종가'].rolling(window=20).mean()
    df['MA_60'] = df['종가'].rolling(window=60).mean()

    # RSI 계산
    delta = df['종가'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # MACD 계산
    exp1 = df['종가'].ewm(span=12, adjust=False).mean()
    exp2 = df['종가'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()

    # 최신 값 반환
    latest = df.iloc[-1]

    return {
        "rsi": rsi.iloc[-1],
        "macd": {
            "value": macd.iloc[-1],
            "signal": signal.iloc[-1],
            "histogram": (macd - signal).iloc[-1]
        },
        "ma_5": latest['MA_5'],
        "ma_20": latest['MA_20'],
        "ma_60": latest['MA_60'],
        "current_vs_ma_20": "상회" if latest['종가'] > latest['MA_20'] else "하회",
        "bollinger_bands": calculate_bollinger_bands(df),
        "support_resistance": calculate_support_resistance(df)
    }
```

---

## 🤖 LLM 분석 실행

```python
async def generate_analysis(
    ticker: str,
    stock_data: Dict,
    financial_data: Dict,
    news_data: List[Dict],
    technical_data: Dict
) -> Dict:
    """
    LLM을 통한 종합 분석 생성
    """
    # 프롬프트 구성
    prompt = build_company_analysis_prompt(
        ticker=ticker,
        stock_data=stock_data,
        financial_data=financial_data,
        news_data=news_data,
        technical_data=technical_data
    )

    # Gemini API 호출
    llm_service = GeminiService()
    response = await llm_service.generate(prompt)

    # 응답 파싱
    parsed = parse_analysis_response(response)

    return {
        "ticker": ticker,
        "name": stock_data['name'],
        "date": datetime.now().date().isoformat(),
        "source": "llm",
        "analysis": {
            "summary": parsed['summary'],
            "financial_analysis": parsed['financial_analysis'],
            "industry_analysis": parsed['industry_analysis'],
            "news_analysis": parsed['news_analysis'],
            "technical_analysis": parsed['technical_analysis'],
            "risk_factors": parsed['risk_factors'],
            "investment_strategy": parsed['investment_strategy']
        },
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "model": "gemini-2.5-flash",
            "tokens_used": response.usage_metadata.total_token_count,
            "processing_time_ms": response.elapsed_time
        }
    }
```

---

## 📦 분석 결과 구조

```python
{
    "ticker": "005930",
    "name": "삼성전자",
    "date": "2025-11-06",
    "source": "llm",  # or "cache"

    "analysis": {
        "summary": {
            "investment_opinion": "BUY",  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
            "target_price": 85000,
            "current_price": 75000,
            "upside_potential": 13.33,
            "key_insights": [
                "반도체 슈퍼 사이클 진입으로 수익성 개선 전망",
                "HBM3 시장 점유율 확대로 프리미엄 확보"
            ],
            "confidence_score": 0.85
        },

        "financial_analysis": {
            "profitability": {
                "summary": "매출 성장과 함께 영업이익률 개선 중",
                "metrics": {...},
                "evaluation": "양호"
            },
            "stability": {...},
            "growth": {...},
            "valuation": {...}
        },

        "industry_analysis": {
            "sector": "IT/반도체",
            "industry_trend": "호황",
            "market_position": "글로벌 1위",
            "competitive_advantage": [...],
            "competitors": [...]
        },

        "news_analysis": {
            "period": "2025-10-30 ~ 2025-11-06",
            "sentiment": {
                "positive": 28,
                "neutral": 10,
                "negative": 4,
                "overall_score": 0.75
            },
            "major_news": [...]
        },

        "technical_analysis": {
            "trend": "상승",
            "indicators": {...},
            "support_resistance": {...}
        },

        "risk_factors": [
            {
                "type": "시장 리스크",
                "description": "...",
                "severity": "중간"
            }
        ],

        "investment_strategy": {
            "short_term": {...},
            "medium_term": {...},
            "long_term": {...}
        }
    },

    "metadata": {
        "generated_at": "2025-11-06T10:30:15",
        "expires_at": "2025-11-07T10:30:15",
        "model": "gemini-2.5-flash",
        "tokens_used": 1850,
        "processing_time_ms": 3250
    }
}
```

---

## 💾 저장 및 캐싱

```python
async def save_and_cache_analysis(
    ticker: str,
    date: str,
    analysis: Dict
):
    """
    분석 결과를 DB와 Redis에 저장
    """
    # 1. DB 저장
    await db.execute("""
        INSERT INTO analysis (
            ticker, date, investment_opinion, target_price,
            current_price, upside_potential, confidence_score,
            key_insights, financial_analysis, industry_analysis,
            news_analysis, technical_analysis, risk_factors,
            investment_strategy, model, tokens_used, processing_time_ms,
            created_at, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticker,
        date,
        analysis['analysis']['summary']['investment_opinion'],
        analysis['analysis']['summary']['target_price'],
        # ... 나머지 필드
    ))

    # 2. Redis 캐싱 (TTL: 24시간)
    cache_key = f"analysis:{ticker}:{date}"
    await redis.setex(
        cache_key,
        86400,  # 24시간
        json.dumps(analysis, ensure_ascii=False)
    )

    logger.info(f"Saved and cached analysis for {ticker}")
```

---

## 🔄 캐시 무효화

```python
async def invalidate_analysis_cache(ticker: str, reason: str):
    """
    분석 캐시 무효화

    Args:
        ticker: 종목 코드
        reason: 무효화 사유 (disclosure/price_shock/manual)
    """
    # 해당 종목의 모든 캐시 삭제
    pattern = f"analysis:{ticker}:*"
    keys = await redis.keys(pattern)

    if keys:
        await redis.delete(*keys)
        logger.warning(
            f"Invalidated {len(keys)} cache keys for {ticker}. "
            f"Reason: {reason}"
        )

    # 재분석 스케줄링
    if reason in ["disclosure", "price_shock"]:
        await schedule_reanalysis(ticker)
```

### 무효화 조건

```python
# 1. 중요 공시 발생
@app.webhook("/dart/disclosure")
async def on_disclosure(disclosure_data: Dict):
    """DART 공시 웹훅"""
    if disclosure_data['importance'] == 'high':
        await invalidate_analysis_cache(
            ticker=disclosure_data['ticker'],
            reason="disclosure"
        )

# 2. 급등/급락 (10% 이상)
async def monitor_price_changes():
    """가격 변동 모니터링"""
    stocks = await get_all_stocks()

    for stock in stocks:
        change_rate = calculate_change_rate(stock)

        if abs(change_rate) >= 10:
            await invalidate_analysis_cache(
                ticker=stock['ticker'],
                reason="price_shock"
            )
```

---

## 🚀 배치 분석

```python
async def batch_analyze_top_stocks():
    """
    장 마감 후 주요 종목 자동 분석

    실행 시간: 15:40 (장 마감 후)
    대상: 시가총액 Top 50 + 급등주
    """
    # Top 50 종목
    top_stocks = await get_top_stocks_by_market_cap(limit=50)

    # 급등주
    trigger_stocks = await get_todays_trigger_stocks()

    # 중복 제거
    all_tickers = list(set(
        [s['ticker'] for s in top_stocks] +
        [s['ticker'] for s in trigger_stocks]
    ))

    logger.info(f"Batch analyzing {len(all_tickers)} stocks")

    # 병렬 분석 (5개씩)
    for i in range(0, len(all_tickers), 5):
        batch = all_tickers[i:i+5]

        tasks = [
            analyze_stock(ticker)
            for ticker in batch
        ]

        await asyncio.gather(*tasks)

        # Rate Limit 고려 (5초 대기)
        await asyncio.sleep(5)

    logger.info("Batch analysis completed")
```

---

## 📊 성능 최적화

### 1. 데이터 수집 병렬화

```python
async def collect_all_data_parallel(ticker: str) -> Dict:
    """
    모든 데이터를 병렬로 수집

    순차 실행: 15초
    병렬 실행: 5초
    """
    tasks = [
        collect_stock_data(ticker),
        collect_financial_data(ticker),
        collect_news_data(ticker),
        collect_technical_data(ticker)
    ]

    results = await asyncio.gather(*tasks)

    return {
        "stock": results[0],
        "financial": results[1],
        "news": results[2],
        "technical": results[3]
    }
```

### 2. 프롬프트 최적화

```python
# 불필요한 데이터 제거
news_summary = compress_news_data(news_data)  # 전체 본문 → 제목 + 요약

# 토큰 수 체크
token_count = count_tokens(prompt)
if token_count > 3000:
    # 프롬프트 압축
    prompt = compress_prompt(prompt, max_tokens=3000)
```

---

## 🧪 테스트

```python
@pytest.mark.asyncio
async def test_company_analysis():
    """기업 분석 E2E 테스트"""
    analysis_service = AnalysisService()

    # 분석 실행
    result = await analysis_service.analyze("005930")

    # 검증
    assert result['ticker'] == "005930"
    assert result['analysis']['summary']['investment_opinion'] in [
        'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
    ]
    assert result['analysis']['summary']['target_price'] > 0
    assert len(result['analysis']['risk_factors']) >= 3

    # 캐시 확인
    cached = await redis.get("analysis:005930:2025-11-06")
    assert cached is not None
```

---

## 📚 참고 자료

- [DART API 문서](https://opendart.fss.or.kr/guide/main.do)
- [pykrx 문서](https://github.com/sharebook-kr/pykrx)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
