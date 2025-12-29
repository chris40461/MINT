# 평가 시스템 (Evaluation System)

## 📌 문서 목적

프롬프트 및 추천 성능을 정량/정성적으로 평가하는 시스템을 설명합니다.

---

## 🎯 평가 목적

1. **LLM 프롬프트 품질 개선**
2. **추천 종목 성과 추적**
3. **사용자 만족도 측정**
4. **시스템 신뢰도 향상**

---

## 📊 정량적 평가 (Quantitative)

### 1. 예측 정확도 추적

```python
async def evaluate_prediction_accuracy(days: int = 1) -> Dict:
    """
    추천 종목의 D+N 수익률 추적

    Args:
        days: 평가 기간 (1, 7일)

    Returns:
        승률, 평균 수익률, 샤프 비율
    """
    # D-N일 추천 종목 조회
    target_date = datetime.now() - timedelta(days=days)
    recommendations = await db.query("""
        SELECT ticker, opinion, entry_price, target_price
        FROM recommendations
        WHERE date = ?
          AND evaluated_at IS NULL
    """, (target_date,))

    results = []

    for rec in recommendations:
        # 현재 가격 조회
        current_price = await get_current_price(rec['ticker'])

        # 수익률 계산
        actual_return = (
            (current_price / rec['entry_price'] - 1) * 100
        )

        # 예측 성공 여부
        hit = (
            (rec['opinion'] in ['BUY', 'STRONG_BUY'] and actual_return > 0) or
            (rec['opinion'] in ['SELL', 'STRONG_SELL'] and actual_return < 0)
        )

        results.append({
            "ticker": rec['ticker'],
            "actual_return": actual_return,
            "hit": hit
        })

        # DB 업데이트
        await db.execute("""
            UPDATE recommendations
            SET actual_return_d{} = ?,
                hit = ?,
                evaluated_at = NOW()
            WHERE ticker = ? AND date = ?
        """.format(days), (actual_return, hit, rec['ticker'], target_date))

    # 통계 계산
    total = len(results)
    hits = sum(1 for r in results if r['hit'])
    win_rate = hits / total if total > 0 else 0
    avg_return = sum(r['actual_return'] for r in results) / total if total > 0 else 0

    # 샤프 비율
    returns = [r['actual_return'] for r in results]
    sharpe_ratio = calculate_sharpe_ratio(returns)

    return {
        "period": f"D+{days}",
        "total_recommendations": total,
        "hits": hits,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "sharpe_ratio": sharpe_ratio
    }
```

### 2. 목표가 달성률

```python
async def evaluate_target_achievement() -> Dict:
    """
    목표가 달성률 평가
    """
    # 목표가가 설정된 추천 조회
    recs = await db.query("""
        SELECT ticker, target_price, entry_price, date
        FROM recommendations
        WHERE target_price IS NOT NULL
          AND date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)

    achieved = []

    for rec in recs:
        # 기간 내 최고가 조회
        high_price = await get_high_price_since(rec['ticker'], rec['date'])

        # 목표가 달성 여부
        if high_price >= rec['target_price']:
            # 달성 일수 계산
            achieved_date = await get_first_date_above(
                rec['ticker'],
                rec['date'],
                rec['target_price']
            )
            days_to_achieve = (achieved_date - rec['date']).days

            achieved.append({
                "ticker": rec['ticker'],
                "days": days_to_achieve
            })

    achievement_rate = len(achieved) / len(recs) if recs else 0
    avg_days = sum(a['days'] for a in achieved) / len(achieved) if achieved else 0

    return {
        "total": len(recs),
        "achieved": len(achieved),
        "achievement_rate": achievement_rate,
        "avg_days_to_achieve": avg_days
    }
```

### 3. 손절 회피율

```python
async def evaluate_stop_loss_avoidance() -> Dict:
    """
    손절가 도달 전 매도 추천 비율
    """
    # 손절가가 설정된 추천 조회
    recs = await db.query("""
        SELECT ticker, stop_loss, entry_price, date
        FROM recommendations
        WHERE stop_loss IS NOT NULL
          AND date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    """)

    avoided = 0

    for rec in recs:
        # 손절가 도달 여부 확인
        reached_stop_loss = await check_stop_loss_reached(
            rec['ticker'],
            rec['date'],
            rec['stop_loss']
        )

        if reached_stop_loss:
            # 도달 전에 매도 추천했는지 확인
            sell_recommended_before = await check_sell_before_stop_loss(
                rec['ticker'],
                rec['date'],
                reached_stop_loss
            )

            if sell_recommended_before:
                avoided += 1

    avoidance_rate = avoided / len(recs) if recs else 0

    return {
        "total_holdings": len(recs),
        "avoided_stop_loss": avoided,
        "avoidance_rate": avoidance_rate
    }
```

---

## 📝 정성적 평가 (Qualitative)

### 1. 분석 깊이 체크

```python
def evaluate_analysis_quality(analysis_text: str) -> Dict:
    """
    보고서 품질 자동 평가

    체크리스트:
    - 재무제표 언급 여부
    - 뉴스 출처 명시
    - 리스크 언급 (3개 이상)
    - 목표가 근거 제시
    """
    checklist = {
        "has_financial_data": bool(re.search(r"(ROE|PER|PBR|부채비율)", analysis_text)),
        "has_news_source": bool(re.search(r"(뉴스|기사|보도)", analysis_text)),
        "has_risk_factors": len(re.findall(r"리스크", analysis_text)) >= 3,
        "has_target_price_rationale": bool(re.search(r"목표가.*근거", analysis_text)),
        "has_technical_analysis": bool(re.search(r"(RSI|MACD|이동평균)", analysis_text)),
        "has_industry_analysis": bool(re.search(r"(업종|산업|섹터)", analysis_text))
    }

    score = sum(checklist.values()) / len(checklist) * 10

    missing = [k for k, v in checklist.items() if not v]

    return {
        "score": score,  # 0-10
        "checklist": checklist,
        "missing": missing
    }
```

### 2. 사용자 피드백

```python
async def collect_user_feedback(
    feedback_type: str,
    ticker: str,
    date: str,
    rating: int,
    comment: str
) -> str:
    """
    사용자 피드백 수집

    Args:
        feedback_type: analysis / morning_report / afternoon_report
        ticker: 종목 코드
        date: 날짜
        rating: 1-5 점수
        comment: 자유 의견

    Returns:
        feedback_id
    """
    feedback_id = generate_uuid()

    await db.execute("""
        INSERT INTO user_feedback (
            id, feedback_type, ticker, date,
            rating, comment, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, NOW())
    """, (feedback_id, feedback_type, ticker, date, rating, comment))

    return feedback_id
```

---

## 📈 주간/월간 리포트

```python
async def generate_evaluation_report(period: str = "7d") -> Dict:
    """
    평가 리포트 생성

    Args:
        period: 7d, 30d, 90d

    Returns:
        종합 평가 지표
    """
    days = int(period[:-1])

    # 1. 정량적 평가
    d1_accuracy = await evaluate_prediction_accuracy(days=1)
    d7_accuracy = await evaluate_prediction_accuracy(days=7)
    target_achievement = await evaluate_target_achievement()
    stop_loss_avoidance = await evaluate_stop_loss_avoidance()

    # 2. 정성적 평가
    avg_quality_score = await calculate_avg_quality_score(days)
    user_satisfaction = await calculate_user_satisfaction(days)

    # 3. 소스별 성과
    by_source = await calculate_performance_by_source(days)

    return {
        "period": f"{days}d",
        "start_date": (datetime.now() - timedelta(days=days)).date().isoformat(),
        "end_date": datetime.now().date().isoformat(),
        "quantitative": {
            "prediction_accuracy": {
                "d_plus_1": d1_accuracy,
                "d_plus_7": d7_accuracy
            },
            "target_price_achievement": target_achievement,
            "stop_loss_avoidance": stop_loss_avoidance
        },
        "qualitative": {
            "analysis_depth": {
                "avg_score": avg_quality_score
            },
            "user_satisfaction": user_satisfaction
        },
        "by_source": by_source
    }
```

---

## 🔄 자동 평가 스케줄

```python
def setup_evaluation_scheduler():
    """
    평가 스케줄러 설정
    """
    scheduler = AsyncIOScheduler()

    # D+1 평가 (매일 16:00)
    scheduler.add_job(
        func=lambda: evaluate_prediction_accuracy(days=1),
        trigger=CronTrigger(hour=16, minute=0),
        id='d1_evaluation'
    )

    # D+7 평가 (매일 16:10)
    scheduler.add_job(
        func=lambda: evaluate_prediction_accuracy(days=7),
        trigger=CronTrigger(hour=16, minute=10),
        id='d7_evaluation'
    )

    # 주간 리포트 (매주 월요일 09:00)
    scheduler.add_job(
        func=lambda: generate_evaluation_report(period="7d"),
        trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='weekly_evaluation'
    )

    scheduler.start()
```

---

## 📊 대시보드 시각화

```python
async def get_evaluation_dashboard_data() -> Dict:
    """
    평가 대시보드용 데이터
    """
    # 최근 30일 성과
    report = await generate_evaluation_report(period="30d")

    # 일별 승률 추이
    daily_win_rates = await get_daily_win_rates(days=30)

    # 종목별 성과
    top_performers = await get_top_performing_stocks(days=30, limit=10)
    worst_performers = await get_worst_performing_stocks(days=30, limit=10)

    return {
        "summary": report,
        "trends": {
            "daily_win_rates": daily_win_rates
        },
        "top_performers": top_performers,
        "worst_performers": worst_performers
    }
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
