# 급등주 감지 알고리즘 (Trigger Detection)

## 📌 문서 목적

급등주 감지의 핵심 알고리즘을 상세히 설명하고, 6개 트리거의 구현 방법, 복합 점수 계산, 성능 최적화 전략을 제시합니다.

---

## 🎯 급등주 감지 개요

### 목적
- **Rule-based 100%**: LLM 비용 0원
- **빠른 스크리닝**: 3000+ 종목을 5분 내 처리
- **높은 정확도**: 검증된 prism-insight 로직 차용

### 실행 시점
- **오전 트리거**: 09:10 (장 시작 10분 후)
- **오후 트리거**: 15:30 (장 마감 직후)

---

## 📊 6개 트리거 상세

## 오전 트리거 (Morning Triggers)

### 1. 거래량 급증 (Volume Surge)

**선정 기준**: 전일 대비 거래량 30% 이상 증가

**필터링 조건**:
- 거래대금 ≥ 5억원
- 시가총액 ≥ 500억원
- 시장 평균 거래량의 20% 이상
- 시가 대비 현재가 상승

**복합 점수**:
```python
score = 거래량증가율_norm * 0.6 + 절대거래량_norm * 0.4
```

**구현**:
```python
async def morning_volume_surge(
    self,
    current_date: datetime,
    top_n: int = 3
) -> List[Dict]:
    """
    오전 트리거 1: 거래량 급증 상위주

    Args:
        current_date: 분석 날짜
        top_n: 선정 종목 수 (기본 3개)

    Returns:
        List[{ticker, name, score, indicators, ...}]
    """
    # Step 1: 데이터 수집
    current = await self.data_service.get_market_snapshot(current_date)
    prev = await self.data_service.get_market_snapshot(
        current_date - timedelta(days=1)
    )

    # Step 2: 거래량 증가율 계산
    current['거래량증가율'] = self.metrics.calculate_volume_change(
        current, prev
    )
    current['거래대금'] = current['종가'] * current['거래량']

    # Step 3: 1차 필터링 - 절대적 기준
    filtered = self.filter.apply_absolute_filters(
        current,
        min_trading_value=500_000_000,  # 5억원
        min_market_cap=50_000_000_000    # 500억원
    )

    # Step 4: 2차 필터링 - 상승 종목만
    filtered = self.filter.filter_uptrend_only(filtered)

    # Step 5: 3차 필터링 - 거래량 증가율 30% 이상
    filtered = filtered[filtered['거래량증가율'] >= 30]

    # Step 6: 시장 평균 대비 필터
    avg_volume = current['거래량'].mean()
    filtered = filtered[filtered['거래량'] >= avg_volume * 0.2]

    # Step 7: 복합 점수 계산
    filtered = self.scorer.normalize_and_score(
        filtered,
        ratio_col='거래량증가율',
        abs_col='거래량',
        ratio_weight=0.6,
        abs_weight=0.4
    )

    # Step 8: Top N 선정
    top_stocks = filtered.nlargest(top_n, '복합점수')

    # Step 9: 종목명 추가
    top_stocks = self._add_stock_names(top_stocks)

    # Step 10: 결과 변환
    return top_stocks.to_dict('records')
```

**출력 예시**:
```json
[
  {
    "ticker": "005930",
    "name": "삼성전자",
    "current_price": 75000,
    "change_rate": 3.45,
    "volume": 15000000,
    "volume_increase_rate": 45.2,
    "trading_value": 1125000000000,
    "market_cap": 450000000000000,
    "composite_score": 0.92,
    "indicators": {
      "volume_increase_norm": 0.95,
      "volume_norm": 0.88
    }
  },
  ...
]
```

---

### 2. 갭 상승 모멘텀 (Gap Up Momentum)

**선정 기준**: 전일 종가 대비 시가 1% 이상 상승

**필터링 조건**:
- 거래대금 ≥ 5억원
- 시가총액 ≥ 500억원
- 시가 대비 현재가 상승 (상승세 지속)

**복합 점수**:
```python
score = 갭상승률_norm * 0.5 + 장중등락률_norm * 0.3 + 거래대금_norm * 0.2
```

**구현**:
```python
async def morning_gap_up(
    self,
    current_date: datetime,
    top_n: int = 3
) -> List[Dict]:
    """
    오전 트리거 2: 갭 상승 모멘텀 상위주

    갭 상승: 전일 종가보다 오늘 시가가 높은 경우
    모멘텀: 시가 대비 현재가도 상승 중인 경우
    """
    # 데이터 수집
    current = await self.data_service.get_market_snapshot(current_date)
    prev = await self.data_service.get_market_snapshot(
        current_date - timedelta(days=1)
    )

    # 지표 계산
    current['갭상승률'] = self.metrics.calculate_gap_ratio(current, prev)
    current['장중등락률'] = self.metrics.calculate_intraday_change(current)
    current['거래대금'] = current['종가'] * current['거래량']

    # 필터링
    filtered = self.filter.apply_absolute_filters(current)
    filtered = self.filter.filter_uptrend_only(filtered)
    filtered = filtered[filtered['갭상승률'] >= 1.0]

    # 복합 점수 계산 (3단계)
    # 1단계: 갭상승률 + 장중등락률
    filtered = self.scorer.normalize_and_score(
        filtered,
        ratio_col='갭상승률',
        abs_col='장중등락률',
        ratio_weight=0.5,
        abs_weight=0.3
    )

    # 2단계: 거래대금 추가
    filtered['거래대금_norm'] = (
        (filtered['거래대금'] - filtered['거래대금'].min()) /
        (filtered['거래대금'].max() - filtered['거래대금'].min())
    )

    # 3단계: 최종 점수
    filtered['복합점수'] = (
        filtered['복합점수'] * 0.8 +  # 이전 점수
        filtered['거래대금_norm'] * 0.2
    )

    # Top N 선정
    top_stocks = filtered.nlargest(top_n, '복합점수')
    return top_stocks.to_dict('records')
```

**갭 상승률 계산**:
```python
def calculate_gap_ratio(
    current_df: pd.DataFrame,
    prev_df: pd.DataFrame
) -> pd.Series:
    """
    갭 상승률 = (금일시가 / 전일종가 - 1) × 100

    예시:
    전일 종가: 10,000원
    금일 시가: 10,200원
    갭 상승률: (10200 / 10000 - 1) × 100 = 2.0%
    """
    merged = current_df.join(prev_df['종가'], rsuffix='_prev')
    gap_ratio = (merged['시가'] / merged['종가_prev'] - 1) * 100

    return gap_ratio
```

---

### 3. 시총 대비 자금유입 (Fund Inflow vs Market Cap)

**선정 기준**: 거래대금/시가총액 비율이 높은 종목

**필터링 조건**:
- 거래대금 ≥ 5억원
- 시가총액 ≥ 500억원
- 시가 대비 현재가 상승

**복합 점수**:
```python
score = 자금유입비율_norm * 0.5 + 거래대금_norm * 0.3 + 장중등락률_norm * 0.2
```

**구현**:
```python
async def morning_fund_inflow(
    self,
    current_date: datetime,
    top_n: int = 3
) -> List[Dict]:
    """
    오전 트리거 3: 시총 대비 자금유입 상위주

    자금유입 비율 = (거래대금 / 시가총액) × 100
    → 시가총액 대비 얼마나 많은 자금이 유입되었는지
    """
    # 데이터 수집
    current = await self.data_service.get_market_snapshot(current_date)

    # 지표 계산
    current['거래대금'] = current['종가'] * current['거래량']
    current['자금유입비율'] = (
        current['거래대금'] / current['시가총액']
    ) * 100
    current['장중등락률'] = self.metrics.calculate_intraday_change(current)

    # 필터링
    filtered = self.filter.apply_absolute_filters(current)
    filtered = self.filter.filter_uptrend_only(filtered)

    # 복합 점수 계산
    # 정규화
    filtered['자금유입비율_norm'] = self._normalize(filtered['자금유입비율'])
    filtered['거래대금_norm'] = self._normalize(filtered['거래대금'])
    filtered['장중등락률_norm'] = self._normalize(filtered['장중등락률'])

    # 가중 평균
    filtered['복합점수'] = (
        filtered['자금유입비율_norm'] * 0.5 +
        filtered['거래대금_norm'] * 0.3 +
        filtered['장중등락률_norm'] * 0.2
    )

    # Top N 선정
    top_stocks = filtered.nlargest(top_n, '복합점수')
    return top_stocks.to_dict('records')

def _normalize(self, series: pd.Series) -> pd.Series:
    """Min-Max 정규화 (0-1)"""
    return (series - series.min()) / (series.max() - series.min())
```

---

## 오후 트리거 (Afternoon Triggers)

### 4. 일중 상승률 (Intraday Rise)

**선정 기준**: 시가 대비 3% 이상 상승

**필터링 조건**:
- 거래대금 ≥ 10억원 (오전보다 높음)
- 시가총액 ≥ 500억원

**복합 점수**:
```python
score = 장중등락률_norm * 0.6 + 거래대금_norm * 0.4
```

**구현**:
```python
async def afternoon_intraday_rise(
    self,
    current_date: datetime,
    top_n: int = 3
) -> List[Dict]:
    """
    오후 트리거 1: 일중 상승률 상위주

    장중 등락률 = (종가 / 시가 - 1) × 100
    """
    # 데이터 수집 (장 마감 후)
    current = await self.data_service.get_market_snapshot(current_date)

    # 지표 계산
    current['장중등락률'] = (
        (current['종가'] / current['시가'] - 1) * 100
    )
    current['거래대금'] = current['종가'] * current['거래량']

    # 필터링
    filtered = self.filter.apply_absolute_filters(
        current,
        min_trading_value=1_000_000_000  # 10억원
    )
    filtered = filtered[filtered['장중등락률'] >= 3.0]

    # 복합 점수
    filtered = self.scorer.normalize_and_score(
        filtered,
        ratio_col='장중등락률',
        abs_col='거래대금',
        ratio_weight=0.6,
        abs_weight=0.4
    )

    top_stocks = filtered.nlargest(top_n, '복합점수')
    return top_stocks.to_dict('records')
```

---

### 5. 마감 강도 (Closing Strength)

**선정 기준**: (종가-저가)/(고가-저가) 비율이 높은 종목

**필터링 조건**:
- 거래대금 ≥ 5억원
- 시가총액 ≥ 500억원
- 전일 대비 거래량 증가
- 시가 대비 종가 상승

**복합 점수**:
```python
score = 마감강도_norm * 0.5 + 거래량증가율_norm * 0.3 + 거래대금_norm * 0.2
```

**마감 강도 의미**:
- **1.0에 가까움**: 종가가 고가에 근접 → 강력한 매수세
- **0.5 근처**: 중간 가격대에서 마감 → 중립
- **0.0에 가까움**: 종가가 저가에 근접 → 약한 마감

**구현**:
```python
async def afternoon_closing_strength(
    self,
    current_date: datetime,
    top_n: int = 3
) -> List[Dict]:
    """
    오후 트리거 2: 마감 강도 상위주

    마감 강도 = (종가 - 저가) / (고가 - 저가)
    → 1에 가까울수록 강력한 상승 마감
    """
    # 데이터 수집
    current = await self.data_service.get_market_snapshot(current_date)
    prev = await self.data_service.get_market_snapshot(
        current_date - timedelta(days=1)
    )

    # 지표 계산
    current['마감강도'] = self.metrics.calculate_closing_strength(current)
    current['거래량증가율'] = self.metrics.calculate_volume_change(
        current, prev
    )
    current['거래대금'] = current['종가'] * current['거래량']

    # 필터링
    filtered = self.filter.apply_absolute_filters(current)

    # 거래량 증가 & 상승 종목만
    filtered = filtered[filtered['거래량증가율'] > 0]
    filtered = filtered[filtered['종가'] > filtered['시가']]

    # 복합 점수
    filtered['마감강도_norm'] = self._normalize(filtered['마감강도'])
    filtered['거래량증가율_norm'] = self._normalize(filtered['거래량증가율'])
    filtered['거래대금_norm'] = self._normalize(filtered['거래대금'])

    filtered['복합점수'] = (
        filtered['마감강도_norm'] * 0.5 +
        filtered['거래량증가율_norm'] * 0.3 +
        filtered['거래대금_norm'] * 0.2
    )

    top_stocks = filtered.nlargest(top_n, '복합점수')
    return top_stocks.to_dict('records')
```

**마감 강도 계산**:
```python
def calculate_closing_strength(df: pd.DataFrame) -> pd.Series:
    """
    마감 강도 = (종가 - 저가) / (고가 - 저가)

    예시:
    고가: 10,500원
    저가: 10,000원
    종가: 10,400원
    마감강도: (10400 - 10000) / (10500 - 10000) = 0.8
    → 고가 근처에서 마감 (강세)
    """
    numerator = df['종가'] - df['저가']
    denominator = df['고가'] - df['저가']

    # 0으로 나누기 방지 (상하한가)
    denominator = denominator.replace(0, 0.01)

    strength = numerator / denominator
    return strength.clip(0, 1)  # 0-1 범위로 제한
```

---

### 6. 횡보주 거래량 (Sideways with Volume)

**선정 기준**: 등락률 ±5% 이내 + 거래량 50% 이상 증가

**필터링 조건**:
- 거래대금 ≥ 5억원
- 시가총액 ≥ 500억원
- 장중 등락률 -5% ~ +5%
- 거래량 증가율 ≥ 50%

**복합 점수**:
```python
score = 거래량증가율_norm * 0.6 + 거래대금_norm * 0.4
```

**의미**: 가격은 횡보하지만 거래량이 급증 → 세력 개입 가능성

**구현**:
```python
async def afternoon_sideways_volume(
    self,
    current_date: datetime,
    top_n: int = 3
) -> List[Dict]:
    """
    오후 트리거 3: 횡보주 거래량 상위주

    횡보: 등락률 ±5% 이내
    거래량 급증: 전일 대비 50% 이상
    """
    # 데이터 수집
    current = await self.data_service.get_market_snapshot(current_date)
    prev = await self.data_service.get_market_snapshot(
        current_date - timedelta(days=1)
    )

    # 지표 계산
    current['장중등락률'] = (
        (current['종가'] / current['시가'] - 1) * 100
    )
    current['거래량증가율'] = self.metrics.calculate_volume_change(
        current, prev
    )
    current['거래대금'] = current['종가'] * current['거래량']

    # 필터링
    filtered = self.filter.apply_absolute_filters(current)

    # 횡보 조건: -5% ~ +5%
    filtered = filtered[
        (filtered['장중등락률'] >= -5) &
        (filtered['장중등락률'] <= 5)
    ]

    # 거래량 급증 조건: 50% 이상
    filtered = filtered[filtered['거래량증가율'] >= 50]

    # 복합 점수
    filtered = self.scorer.normalize_and_score(
        filtered,
        ratio_col='거래량증가율',
        abs_col='거래대금',
        ratio_weight=0.6,
        abs_weight=0.4
    )

    top_stocks = filtered.nlargest(top_n, '복합점수')
    return top_stocks.to_dict('records')
```

---

## 🧮 복합 점수 계산 (Composite Score)

### 정규화 (Normalization)

**Min-Max Scaling**:
```python
def normalize(series: pd.Series) -> pd.Series:
    """
    0-1 범위로 정규화

    공식: (x - min) / (max - min)
    """
    min_val = series.min()
    max_val = series.max()

    if max_val == min_val:
        # 모든 값이 동일한 경우
        return pd.Series(0.5, index=series.index)

    normalized = (series - min_val) / (max_val - min_val)
    return normalized
```

### 가중 평균 (Weighted Average)

```python
def calculate_composite_score(
    df: pd.DataFrame,
    indicators: List[Tuple[str, float]]  # [(컬럼명, 가중치)]
) -> pd.Series:
    """
    복합 점수 계산

    Args:
        df: 데이터프레임
        indicators: [("거래량증가율", 0.6), ("거래량", 0.4)]

    Returns:
        복합 점수 Series (0-1)
    """
    score = pd.Series(0.0, index=df.index)

    for col, weight in indicators:
        # 정규화
        normalized = normalize(df[col])
        # 가중치 적용
        score += normalized * weight

    return score
```

---

## ⚡ 성능 최적화

### 1. 병렬 처리

```python
async def run_morning_triggers(
    self,
    current_date: datetime
) -> Dict[str, List[Dict]]:
    """
    3개 오전 트리거 병렬 실행

    asyncio.gather로 동시 실행
    → 실행 시간: 15초 → 5초
    """
    tasks = [
        self.morning_volume_surge(current_date),
        self.morning_gap_up(current_date),
        self.morning_fund_inflow(current_date)
    ]

    results = await asyncio.gather(*tasks)

    return {
        "volume_surge": results[0],
        "gap_up": results[1],
        "fund_inflow": results[2]
    }
```

### 2. 데이터 캐싱

```python
@lru_cache(maxsize=10)
async def get_market_snapshot_cached(
    self,
    date: datetime
) -> pd.DataFrame:
    """
    시장 스냅샷 캐싱

    동일한 날짜 요청 시 캐시 반환
    → DB/API 호출 최소화
    """
    return await self.get_market_snapshot(date)
```

### 3. 벡터화 연산

```python
# ❌ 느린 방법 (반복문)
for ticker in tickers:
    volume_change = (
        current[ticker]['volume'] / prev[ticker]['volume'] - 1
    ) * 100

# ✅ 빠른 방법 (벡터화)
volume_change = (current['거래량'] / prev['거래량'] - 1) * 100
```

### 4. 인덱싱 활용

```python
# 필터링 전에 인덱스 설정
df.set_index('ticker', inplace=True)

# 빠른 조회
samsung = df.loc['005930']
```

---

## 🧪 테스트

### 단위 테스트

```python
import pytest
from datetime import datetime

class TestTriggerService:
    @pytest.mark.asyncio
    async def test_morning_volume_surge(self):
        """거래량 급증 트리거 테스트"""
        service = TriggerService()

        results = await service.morning_volume_surge(
            current_date=datetime(2025, 11, 6),
            top_n=3
        )

        # 검증
        assert len(results) <= 3
        for stock in results:
            assert stock['거래량증가율'] >= 30
            assert stock['거래대금'] >= 500_000_000
            assert stock['시가총액'] >= 50_000_000_000
            assert 0 <= stock['composite_score'] <= 1

    def test_composite_score_calculation(self):
        """복합 점수 계산 테스트"""
        df = pd.DataFrame({
            '거래량증가율': [50, 40, 30, 20],
            '거래량': [1000000, 800000, 600000, 400000]
        })

        scorer = ScoreCalculator()
        result = scorer.normalize_and_score(
            df,
            ratio_col='거래량증가율',
            abs_col='거래량',
            ratio_weight=0.6,
            abs_weight=0.4
        )

        # 점수 범위 확인
        assert result['복합점수'].max() <= 1.0
        assert result['복합점수'].min() >= 0.0

        # 최고점은 1에 가까워야
        assert result['복합점수'].max() > 0.9
```

---

## 📊 모니터링

### 로깅

```python
import logging

logger = logging.getLogger(__name__)

async def morning_volume_surge(self, current_date, top_n=3):
    logger.info(f"Starting morning volume surge for {current_date}")

    try:
        # 트리거 실행
        results = ...

        logger.info(
            f"Found {len(results)} stocks. "
            f"Top score: {results[0]['composite_score']:.2f}"
        )

        return results

    except Exception as e:
        logger.error(f"Error in volume surge: {e}", exc_info=True)
        raise
```

### 성능 측정

```python
import time

async def run_triggers_with_metrics(self):
    """실행 시간 측정"""
    start = time.time()

    results = await self.run_morning_triggers(datetime.now())

    elapsed = time.time() - start

    logger.info(f"Triggers completed in {elapsed:.2f} seconds")

    # Prometheus metrics
    trigger_execution_time.observe(elapsed)
    trigger_stocks_found.set(len(results['volume_surge']))
```

---

## 📚 참고 자료

- [prism-insight 소스 코드](https://github.com/dragon1086/prism-insight)
- [pandas 공식 문서](https://pandas.pydata.org/)
- [pykrx 사용법](https://github.com/sharebook-kr/pykrx)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
