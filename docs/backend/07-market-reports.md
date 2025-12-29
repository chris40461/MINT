# 장 시작/마감 리포트 (Market Reports)

## 📌 문서 목적

장 시작 및 마감 리포트 생성 프로세스, 주목 종목 선정 알고리즘, LLM 프롬프트, 자동 실행 스케줄을 설명합니다.

---

## 🎯 리포트 개요

### 장 시작 리포트 (Morning Report)
- **실행 시간**: 08:30 (장 시작 30분 전)
- **목적**: 투자자가 장 시작 전 알아야 할 정보 제공
- **내용**: 시장 전망, 주목 종목, 섹터 분석, 투자 전략

### 장 마감 리포트 (Afternoon Report)
- **실행 시간**: 15:40 (장 마감 10분 후)
- **목적**: 당일 시장 분석 및 내일 전략
- **내용**: 시장 요약, 급등주 분석, 내일 전략

---

## 📊 장 시작 리포트

### 1. 데이터 수집

```python
async def collect_morning_report_data() -> Dict:
    """
    장 시작 리포트용 데이터 수집
    """
    # 1. 전일 한국 시장
    kospi_data = await get_index_data("KOSPI", yesterday)
    kosdaq_data = await get_index_data("KOSDAQ", yesterday)

    # 2. 전일 미국 시장 (크롤링)
    us_market_data = await crawl_us_market()

    # 3. 환율
    exchange_rate = await get_exchange_rate("USD/KRW")

    # 4. 주요 뉴스 (밤새 발생한 뉴스)
    overnight_news = await crawl_overnight_news()

    # 5. 주목 종목 선정
    top_stocks = await select_top_stocks_for_morning()

    return {
        "korean_market": {
            "kospi": kospi_data,
            "kosdaq": kosdaq_data
        },
        "us_market": us_market_data,
        "exchange_rate": exchange_rate,
        "overnight_news": overnight_news,
        "top_stocks": top_stocks
    }
```

### 2. 주목 종목 선정 알고리즘

**Metric 기반 점수화**:

```python
async def select_top_stocks_for_morning(top_n: int = 5) -> List[Dict]:
    """
    주목 종목 Top 5 선정

    점수 = 모멘텀(30%) + 거래량(25%) + 센티먼트(20%) + 기술적(15%) + 재무(10%)
    """
    all_stocks = await get_all_active_stocks()

    scored_stocks = []

    for stock in all_stocks:
        # 1. 모멘텀 점수 (30%)
        momentum_score = calculate_momentum_score(stock)

        # 2. 거래량 점수 (25%)
        volume_score = calculate_volume_score(stock)

        # 3. 뉴스 센티먼트 점수 (20%)
        sentiment_score = await calculate_sentiment_score(stock)

        # 4. 기술적 지표 점수 (15%)
        technical_score = calculate_technical_score(stock)

        # 5. 재무 건전성 점수 (10%)
        financial_score = calculate_financial_score(stock)

        # 총점 계산
        total_score = (
            momentum_score * 0.30 +
            volume_score * 0.25 +
            sentiment_score * 0.20 +
            technical_score * 0.15 +
            financial_score * 0.10
        )

        scored_stocks.append({
            "ticker": stock['ticker'],
            "name": stock['name'],
            "total_score": total_score,
            "scores": {
                "momentum": momentum_score,
                "volume": volume_score,
                "sentiment": sentiment_score,
                "technical": technical_score,
                "financial": financial_score
            }
        })

    # Top N 선정
    scored_stocks.sort(key=lambda x: x['total_score'], reverse=True)
    return scored_stocks[:top_n]
```

**점수 계산 상세**:

```python
def calculate_momentum_score(stock: Dict) -> float:
    """
    모멘텀 점수 (0-1)

    = D-1 수익률 * 0.5 + D-7 수익률 * 0.3 + D-30 수익률 * 0.2
    """
    d1_return = stock['d1_return']  # %
    d7_return = stock['d7_return']
    d30_return = stock['d30_return']

    # 정규화 (0-1)
    d1_norm = normalize_return(d1_return, max_return=10)
    d7_norm = normalize_return(d7_return, max_return=30)
    d30_norm = normalize_return(d30_return, max_return=50)

    score = d1_norm * 0.5 + d7_norm * 0.3 + d30_norm * 0.2
    return score

def calculate_volume_score(stock: Dict) -> float:
    """
    거래량 점수 (0-1)

    = (현재 거래량 / 평균 거래량 - 1)
    """
    avg_volume = stock['avg_volume_20d']  # 20일 평균
    recent_volume = stock['yesterday_volume']

    ratio = recent_volume / avg_volume

    # 2배 이상이면 만점
    score = min(ratio / 2, 1.0)
    return score

async def calculate_sentiment_score(stock: Dict) -> float:
    """
    뉴스 센티먼트 점수 (0-1)

    LLM으로 최근 뉴스 분석
    """
    recent_news = await get_recent_news(stock['ticker'], days=3)

    if not recent_news:
        return 0.5  # 중립

    # LLM 분석
    prompt = f"""
    다음 뉴스들의 전체적인 센티먼트를 0-1 점수로 평가하세요.
    (0: 매우 부정, 0.5: 중립, 1: 매우 긍정)

    {format_news_for_prompt(recent_news)}

    점수만 반환하세요.
    """

    response = await llm_service.generate(prompt)
    score = float(response.strip())

    return score

def calculate_technical_score(stock: Dict) -> float:
    """
    기술적 지표 점수 (0-1)

    RSI + MACD + 이동평균 종합
    """
    rsi = stock['rsi']
    macd = stock['macd']
    ma_position = stock['ma_position']  # 상회/하회

    # RSI 점수 (30-70 범위 선호)
    if 30 <= rsi <= 70:
        rsi_score = 1.0
    elif rsi < 30:
        rsi_score = rsi / 30  # 과매도
    else:
        rsi_score = (100 - rsi) / 30  # 과매수

    # MACD 점수
    macd_score = 1.0 if macd['signal'] == 'golden_cross' else 0.5

    # 이동평균 점수
    ma_score = 1.0 if ma_position == '상회' else 0.3

    # 가중 평균
    score = rsi_score * 0.3 + macd_score * 0.4 + ma_score * 0.3
    return score

def calculate_financial_score(stock: Dict) -> float:
    """
    재무 건전성 점수 (0-1)

    ROE + 부채비율 + 매출성장률
    """
    roe = stock['roe']
    debt_ratio = stock['debt_ratio']
    revenue_growth = stock['revenue_growth_yoy']

    # ROE 점수 (15% 이상이면 만점)
    roe_score = min(roe / 15, 1.0)

    # 부채비율 점수 (50% 이하 선호)
    if debt_ratio <= 50:
        debt_score = 1.0
    else:
        debt_score = max(1 - (debt_ratio - 50) / 100, 0)

    # 매출성장률 점수 (10% 이상이면 만점)
    growth_score = min(revenue_growth / 10, 1.0)

    score = roe_score * 0.5 + debt_score * 0.3 + growth_score * 0.2
    return score
```

### 3. LLM 리포트 생성

```python
async def generate_morning_report(data: Dict) -> Dict:
    """
    장 시작 리포트 생성
    """
    # 프롬프트 구성
    prompt = MARKET_OPENING_PROMPT.format(
        date=datetime.now().strftime("%Y년 %m월 %d일"),
        kospi_close=data['korean_market']['kospi']['close'],
        kospi_change=data['korean_market']['kospi']['change_rate'],
        # ... 나머지 데이터
        top_stocks=format_top_stocks(data['top_stocks']),
        major_news=format_news(data['overnight_news'])
    )

    # LLM 호출
    response = await llm_service.generate(prompt)

    # 파싱
    parsed = parse_morning_report(response)

    return {
        "report_type": "morning",
        "date": datetime.now().date().isoformat(),
        "generated_at": datetime.now().isoformat(),
        "market_overview": data['korean_market'],
        "market_forecast": parsed['market_forecast'],
        "top_stocks": data['top_stocks'],
        "sector_analysis": parsed['sector_analysis'],
        "investment_strategy": parsed['investment_strategy'],
        "key_events": parsed['key_events'],
        "metadata": {
            "model": "gemini-2.5-flash",
            "tokens_used": response.usage_metadata.total_token_count
        }
    }
```

---

## 📉 장 마감 리포트

### 1. 데이터 수집

```python
async def collect_afternoon_report_data() -> Dict:
    """
    장 마감 리포트용 데이터 수집
    """
    # 1. 당일 시장 데이터
    kospi_data = await get_index_data("KOSPI", today)

    # 2. 급등주 (오후 트리거 결과)
    trigger_stocks = await get_afternoon_trigger_results()

    # 3. 섹터별 성과
    sector_performance = await get_sector_performance()

    # 4. 외국인/기관 매매
    foreign_net = await get_foreign_trading(today)
    institution_net = await get_institution_trading(today)

    # 5. 주요 뉴스
    major_news = await get_todays_major_news()

    return {
        "market_summary": {
            "kospi": kospi_data,
            "foreign_net": foreign_net,
            "institution_net": institution_net,
            "sector_performance": sector_performance
        },
        "trigger_stocks": trigger_stocks,
        "major_news": major_news
    }
```

### 2. 급등주 상세 분석

```python
async def analyze_trigger_stocks(
    trigger_stocks: List[Dict]
) -> List[Dict]:
    """
    급등주에 대한 상세 분석
    """
    analyzed = []

    for stock in trigger_stocks:
        # 급등 이유 분석
        reason = await analyze_surge_reason(stock)

        # 향후 전망
        outlook = await analyze_outlook(stock)

        # 투자 전략
        strategy = generate_trading_strategy(stock, reason, outlook)

        analyzed.append({
            "ticker": stock['ticker'],
            "name": stock['name'],
            "trigger_type": stock['trigger_type'],
            "price_change": stock['change_rate'],
            "reason": reason,
            "outlook": outlook,
            "strategy": strategy
        })

    return analyzed
```

---

## 💾 저장 및 캐싱

```python
async def save_report(report: Dict):
    """
    리포트 저장
    """
    # 1. DB 저장
    await db.execute("""
        INSERT INTO reports (
            date, report_type, market_overview,
            market_forecast, top_stocks, sector_analysis,
            investment_strategy, key_events,
            model, tokens_used, created_at, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report['date'],
        report['report_type'],
        json.dumps(report['market_overview']),
        # ...
    ))

    # 2. Redis 캐싱 (TTL: 12시간)
    cache_key = f"report:{report['report_type']}:{report['date']}"
    await redis.setex(
        cache_key,
        43200,  # 12시간
        json.dumps(report, ensure_ascii=False)
    )
```

---

## ⏰ 스케줄러 설정

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

def setup_report_scheduler():
    """
    리포트 생성 스케줄러 설정
    """
    scheduler = AsyncIOScheduler()

    # 장 시작 리포트 (평일 08:30)
    scheduler.add_job(
        func=generate_and_save_morning_report,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=8,
            minute=30,
            timezone='Asia/Seoul'
        ),
        id='morning_report',
        name='장 시작 리포트 생성',
        replace_existing=True
    )

    # 장 마감 리포트 (평일 15:40)
    scheduler.add_job(
        func=generate_and_save_afternoon_report,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=15,
            minute=40,
            timezone='Asia/Seoul'
        ),
        id='afternoon_report',
        name='장 마감 리포트 생성',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Report scheduler started")
```

---

## 📊 성능 측정

```python
async def generate_and_save_morning_report():
    """
    장 시작 리포트 생성 및 저장 (타이머 포함)
    """
    start_time = time.time()

    try:
        # 데이터 수집
        data = await collect_morning_report_data()
        logger.info(f"Data collection: {time.time() - start_time:.2f}s")

        # 리포트 생성
        report = await generate_morning_report(data)
        logger.info(f"Report generation: {time.time() - start_time:.2f}s")

        # 저장
        await save_report(report)
        logger.info(f"Save report: {time.time() - start_time:.2f}s")

        total_time = time.time() - start_time
        logger.info(f"Morning report completed in {total_time:.2f}s")

        # 메트릭 기록
        report_generation_time.labels(report_type='morning').observe(total_time)

    except Exception as e:
        logger.error(f"Failed to generate morning report: {e}", exc_info=True)
        raise
```

---

## 📚 참고 자료

- [APScheduler 문서](https://apscheduler.readthedocs.io/)

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
