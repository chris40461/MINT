# 지표 계산 (Metrics Calculation)

## 📌 문서 목적

급등주 감지, 기업 분석, 리포트 생성에 필요한 각종 지표 계산 방법을 정의합니다.

---

## 📊 가격 지표

### 1. 갭 상승률 (Gap Up Ratio)

```python
def calculate_gap_ratio(
    current_open: float,
    prev_close: float
) -> float:
    """
    갭 상승률 = (금일시가 / 전일종가 - 1) × 100

    Args:
        current_open: 금일 시가
        prev_close: 전일 종가

    Returns:
        갭 상승률 (%)
    """
    return (current_open / prev_close - 1) * 100
```

### 2. 장중 등락률 (Intraday Change)

```python
def calculate_intraday_change(
    current_price: float,
    open_price: float
) -> float:
    """
    장중 등락률 = (현재가 / 시가 - 1) × 100

    Returns:
        장중 등락률 (%)
    """
    return (current_price / open_price - 1) * 100
```

### 3. 마감 강도 (Closing Strength)

```python
def calculate_closing_strength(
    close: float,
    low: float,
    high: float
) -> float:
    """
    마감 강도 = (종가 - 저가) / (고가 - 저가)

    1에 가까울수록 강한 매수세
    0에 가까울수록 강한 매도세

    Returns:
        0-1 사이 값
    """
    if high == low:
        return 0.5  # 보합

    return (close - low) / (high - low)
```

---

## 📈 거래량 지표

### 1. 거래량 증가율

```python
def calculate_volume_change(
    current_volume: int,
    prev_volume: int
) -> float:
    """
    거래량 증가율 = (금일거래량 / 전일거래량 - 1) × 100

    Returns:
        거래량 증가율 (%)
    """
    if prev_volume == 0:
        return 0

    return (current_volume / prev_volume - 1) * 100
```

### 2. 평균 거래량 대비 비율

```python
def calculate_volume_ratio(
    current_volume: int,
    avg_volume: int,
    period: int = 20
) -> float:
    """
    평균 거래량 대비 비율 = 현재 거래량 / N일 평균 거래량

    Args:
        current_volume: 현재 거래량
        avg_volume: N일 평균 거래량
        period: 평균 기간 (기본값 20일)

    Returns:
        비율 (배수)
    """
    if avg_volume == 0:
        return 0

    return current_volume / avg_volume
```

### 3. 시가총액 대비 거래대금 비율

```python
def calculate_turnover_ratio(
    trading_value: int,
    market_cap: int
) -> float:
    """
    회전율 = (거래대금 / 시가총액) × 100

    자금 유입 강도를 나타냄
    높을수록 활발한 거래

    Returns:
        회전율 (%)
    """
    if market_cap == 0:
        return 0

    return (trading_value / market_cap) * 100
```

---

## 🔧 기술적 지표

### 1. RSI (Relative Strength Index)

```python
import pandas as pd

def calculate_rsi(
    prices: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    RSI = 100 - (100 / (1 + RS))
    RS = 평균 상승폭 / 평균 하락폭

    Args:
        prices: 종가 시계열
        period: 계산 기간 (기본값 14일)

    Returns:
        RSI 값 (0-100)

    해석:
        70 이상: 과매수
        30 이하: 과매도
    """
    delta = prices.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi
```

### 2. MACD (Moving Average Convergence Divergence)

```python
def calculate_macd(
    prices: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> dict:
    """
    MACD = 단기EMA - 장기EMA
    Signal = MACD의 EMA
    Histogram = MACD - Signal

    Returns:
        {
            "macd": Series,
            "signal": Series,
            "histogram": Series,
            "status": "golden_cross" | "dead_cross" | "neutral"
        }
    """
    # EMA 계산
    ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
    ema_slow = prices.ewm(span=slow_period, adjust=False).mean()

    macd = ema_fast - ema_slow
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    histogram = macd - signal

    # 최근 크로스 판단
    recent_macd = macd.iloc[-1]
    recent_signal = signal.iloc[-1]
    prev_macd = macd.iloc[-2]
    prev_signal = signal.iloc[-2]

    if prev_macd <= prev_signal and recent_macd > recent_signal:
        status = "golden_cross"  # 매수 신호
    elif prev_macd >= prev_signal and recent_macd < recent_signal:
        status = "dead_cross"    # 매도 신호
    else:
        status = "neutral"

    return {
        "macd": macd,
        "signal": signal,
        "histogram": histogram,
        "status": status
    }
```

### 3. 이동평균선 (Moving Average)

```python
def calculate_moving_averages(
    prices: pd.Series,
    periods: list = [5, 20, 60, 120]
) -> dict:
    """
    여러 기간의 이동평균선 계산

    Args:
        prices: 종가 시계열
        periods: 계산할 기간 리스트

    Returns:
        {
            "ma_5": float,
            "ma_20": float,
            "ma_60": float,
            "ma_120": float,
            "position": "상회" | "하회" | "중립"
        }
    """
    mas = {}

    for period in periods:
        ma_value = prices.rolling(window=period).mean().iloc[-1]
        mas[f"ma_{period}"] = ma_value

    # 현재가와 20일선 비교
    current_price = prices.iloc[-1]
    ma_20 = mas.get("ma_20")

    if current_price > ma_20 * 1.01:
        position = "상회"
    elif current_price < ma_20 * 0.99:
        position = "하회"
    else:
        position = "중립"

    mas["position"] = position

    return mas
```

### 4. 볼린저 밴드 (Bollinger Bands)

```python
def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    num_std: float = 2.0
) -> dict:
    """
    중심선 = N일 이동평균
    상단밴드 = 중심선 + (N일 표준편차 × K)
    하단밴드 = 중심선 - (N일 표준편차 × K)

    Returns:
        {
            "upper": float,
            "middle": float,
            "lower": float,
            "position": "상단돌파" | "하단돌파" | "밴드내"
        }
    """
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    current_price = prices.iloc[-1]
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]
    middle_val = middle.iloc[-1]

    if current_price > upper_val:
        position = "상단돌파"
    elif current_price < lower_val:
        position = "하단돌파"
    else:
        position = "밴드내"

    return {
        "upper": upper_val,
        "middle": middle_val,
        "lower": lower_val,
        "position": position
    }
```

---

## 💰 재무 지표

### 1. ROE (Return on Equity)

```python
def calculate_roe(
    net_income: int,
    shareholders_equity: int
) -> float:
    """
    ROE = (순이익 / 자기자본) × 100

    자기자본 대비 수익성
    15% 이상이면 우량 기업

    Returns:
        ROE (%)
    """
    if shareholders_equity == 0:
        return 0

    return (net_income / shareholders_equity) * 100
```

### 2. PER (Price to Earnings Ratio)

```python
def calculate_per(
    market_cap: int,
    net_income: int,
    shares_outstanding: int = None
) -> float:
    """
    PER = 시가총액 / 당기순이익
    또는 PER = 주가 / 주당순이익(EPS)

    주가가 1년 순이익의 몇 배인지
    낮을수록 저평가

    Returns:
        PER (배)
    """
    if net_income <= 0:
        return float('inf')

    return market_cap / net_income
```

### 3. PBR (Price to Book Ratio)

```python
def calculate_pbr(
    market_cap: int,
    book_value: int
) -> float:
    """
    PBR = 시가총액 / 순자산(자기자본)

    주가가 순자산의 몇 배인지
    1 이하면 저평가

    Returns:
        PBR (배)
    """
    if book_value <= 0:
        return float('inf')

    return market_cap / book_value
```

### 4. 부채비율

```python
def calculate_debt_ratio(
    total_liabilities: int,
    shareholders_equity: int
) -> float:
    """
    부채비율 = (부채총계 / 자기자본) × 100

    자기자본 대비 부채 수준
    100% 이하가 안정적

    Returns:
        부채비율 (%)
    """
    if shareholders_equity <= 0:
        return float('inf')

    return (total_liabilities / shareholders_equity) * 100
```

### 5. 매출 성장률

```python
def calculate_revenue_growth(
    current_revenue: int,
    prev_revenue: int
) -> float:
    """
    매출 성장률 = (당기매출 / 전기매출 - 1) × 100

    Returns:
        성장률 (%)
    """
    if prev_revenue <= 0:
        return 0

    return (current_revenue / prev_revenue - 1) * 100
```

---

## 📐 정규화 (Normalization)

### 1. Min-Max 정규화

```python
def normalize_min_max(
    value: float,
    min_val: float,
    max_val: float
) -> float:
    """
    Min-Max 정규화 = (값 - 최소값) / (최대값 - 최소값)

    0-1 범위로 변환

    Returns:
        정규화된 값 (0-1)
    """
    if max_val == min_val:
        return 0.5

    normalized = (value - min_val) / (max_val - min_val)

    # 범위 제한
    return max(0, min(1, normalized))
```

### 2. Z-Score 정규화

```python
def normalize_z_score(
    value: float,
    mean: float,
    std: float
) -> float:
    """
    Z-Score = (값 - 평균) / 표준편차

    평균 0, 표준편차 1로 변환

    Returns:
        Z-Score
    """
    if std == 0:
        return 0

    return (value - mean) / std
```

### 3. 로그 변환

```python
import math

def normalize_log(
    value: float,
    base: float = 10
) -> float:
    """
    로그 변환 = log(값 + 1)

    왜도가 큰 데이터 정규분포화

    Returns:
        로그 변환된 값
    """
    if value <= 0:
        return 0

    return math.log(value + 1, base)
```

---

## 🎯 복합 지표 계산

### 1. 모멘텀 점수 (장 시작 리포트용)

```python
def calculate_momentum_score(
    d1_return: float,
    d7_return: float,
    d30_return: float,
    max_d1: float = 10,
    max_d7: float = 30,
    max_d30: float = 50
) -> float:
    """
    모멘텀 점수 = D-1 수익률(50%) + D-7 수익률(30%) + D-30 수익률(20%)

    각 수익률을 0-1로 정규화 후 가중 평균

    Returns:
        모멘텀 점수 (0-1)
    """
    d1_norm = normalize_min_max(d1_return, 0, max_d1)
    d7_norm = normalize_min_max(d7_return, 0, max_d7)
    d30_norm = normalize_min_max(d30_return, 0, max_d30)

    score = d1_norm * 0.5 + d7_norm * 0.3 + d30_norm * 0.2

    return score
```

### 2. 기술적 종합 점수

```python
def calculate_technical_score(
    rsi: float,
    macd_status: str,
    ma_position: str
) -> float:
    """
    기술적 종합 점수 = RSI(30%) + MACD(40%) + 이동평균(30%)

    Returns:
        기술적 점수 (0-1)
    """
    # RSI 점수 (30-70 범위 선호)
    if 30 <= rsi <= 70:
        rsi_score = 1.0
    elif rsi < 30:
        rsi_score = rsi / 30
    else:
        rsi_score = (100 - rsi) / 30

    # MACD 점수
    macd_score = 1.0 if macd_status == "golden_cross" else 0.5

    # 이동평균 점수
    ma_score = 1.0 if ma_position == "상회" else 0.3

    # 가중 평균
    total_score = rsi_score * 0.3 + macd_score * 0.4 + ma_score * 0.3

    return total_score
```

### 3. 재무 건전성 점수

```python
def calculate_financial_score(
    roe: float,
    debt_ratio: float,
    revenue_growth: float
) -> float:
    """
    재무 건전성 점수 = ROE(50%) + 부채비율(30%) + 매출성장률(20%)

    Returns:
        재무 점수 (0-1)
    """
    # ROE 점수 (15% 이상이면 만점)
    roe_score = min(roe / 15, 1.0)

    # 부채비율 점수 (50% 이하 선호)
    if debt_ratio <= 50:
        debt_score = 1.0
    else:
        debt_score = max(1 - (debt_ratio - 50) / 100, 0)

    # 매출성장률 점수 (10% 이상이면 만점)
    growth_score = min(revenue_growth / 10, 1.0) if revenue_growth > 0 else 0

    # 가중 평균
    total_score = roe_score * 0.5 + debt_score * 0.3 + growth_score * 0.2

    return total_score
```

---

## 📦 통합 계산 서비스

```python
# backend/app/services/metrics_service.py

class MetricsService:
    """
    모든 지표 계산을 통합 관리
    """

    @staticmethod
    def calculate_all_price_metrics(
        current_df: pd.DataFrame,
        prev_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        가격 관련 모든 지표 일괄 계산
        """
        df = current_df.copy()

        # 갭 상승률
        df['갭상승률'] = (df['시가'] / prev_df['종가'] - 1) * 100

        # 장중 등락률
        df['장중등락률'] = (df['종가'] / df['시가'] - 1) * 100

        # 마감 강도
        df['마감강도'] = (df['종가'] - df['저가']) / (df['고가'] - df['저가'])

        return df

    @staticmethod
    def calculate_all_volume_metrics(
        current_df: pd.DataFrame,
        prev_df: pd.DataFrame,
        avg_volume_20d: pd.Series
    ) -> pd.DataFrame:
        """
        거래량 관련 모든 지표 일괄 계산
        """
        df = current_df.copy()

        # 거래량 증가율
        df['거래량증가율'] = (df['거래량'] / prev_df['거래량'] - 1) * 100

        # 평균 거래량 대비
        df['거래량비율'] = df['거래량'] / avg_volume_20d

        # 회전율
        df['회전율'] = (df['거래대금'] / df['시가총액']) * 100

        return df

    @staticmethod
    async def calculate_technical_indicators(
        ticker: str,
        prices: pd.Series
    ) -> dict:
        """
        기술적 지표 통합 계산
        """
        return {
            "rsi": calculate_rsi(prices).iloc[-1],
            "macd": calculate_macd(prices),
            "moving_averages": calculate_moving_averages(prices),
            "bollinger_bands": calculate_bollinger_bands(prices)
        }
```

---

## ⚠️ 주의사항

### 1. 0으로 나누기 방지

모든 나눗셈에서 분모가 0인지 체크:
```python
if denominator == 0:
    return 0  # 또는 적절한 기본값
```

### 2. NaN 처리

```python
import numpy as np

# NaN 체크
if np.isnan(value):
    value = 0

# DataFrame NaN 처리
df.fillna(0, inplace=True)
```

### 3. 무한대 처리

```python
if value == float('inf') or value == float('-inf'):
    value = 0
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
