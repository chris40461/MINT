# 필터링 및 점수화 (Filtering & Scoring)

## 📌 문서 목적

급등주 선정을 위한 필터링 조건과 복합 점수 계산 방법을 정의합니다.

---

## 🔍 필터링 전략

### 1. 절대적 필터 (Absolute Filters)

**목적**: 동전주, 저유동성 종목 제외

```python
# backend/app/utils/filters.py

class StockFilter:
    """
    종목 필터링 유틸리티
    """

    @staticmethod
    def apply_absolute_filters(
        df: pd.DataFrame,
        min_trading_value: int = 500_000_000,   # 5억원
        min_market_cap: int = 50_000_000_000,   # 500억원
        min_price: int = 1000                    # 1천원
    ) -> pd.DataFrame:
        """
        절대적 필터링 조건 적용

        조건:
        1. 최소 거래대금 >= 5억원
        2. 최소 시가총액 >= 500억원
        3. 최소 주가 >= 1,000원 (동전주 제외)

        Returns:
            필터링된 DataFrame
        """
        # 거래대금 필터
        df = df[df['거래대금'] >= min_trading_value]

        # 시가총액 필터 (동전주 제외)
        df = df[df['시가총액'] >= min_market_cap]

        # 최소 주가 (동전주 제외)
        df = df[df['종가'] >= min_price]

        return df
```

### 2. 상대적 필터 (Relative Filters)

**목적**: 시장 평균 대비 거래 활발한 종목 선정

```python
@staticmethod
def apply_relative_filters(
    df: pd.DataFrame,
    market_avg_volume_ratio: float = 0.2  # 시장 평균의 20%
) -> pd.DataFrame:
    """
    상대적 필터링 조건 적용

    조건:
    1. 거래량 >= 시장 평균 거래량 × 20%

    Returns:
        필터링된 DataFrame
    """
    # 시장 평균 거래량 계산
    market_avg_volume = df['거래량'].mean()

    # 시장 평균의 20% 이상만 선정
    df = df[df['거래량'] >= market_avg_volume * market_avg_volume_ratio]

    return df
```

### 3. 추세 필터 (Trend Filters)

**목적**: 상승 추세 종목만 선정

```python
@staticmethod
def filter_uptrend_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    상승 종목만 필터링

    조건:
    - 시가 대비 현재가 상승 (종가 > 시가)

    Returns:
        상승 종목만 포함된 DataFrame
    """
    return df[df['종가'] > df['시가']]

@staticmethod
def filter_downtrend_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    하락 종목만 필터링 (공매도 전략용)

    조건:
    - 시가 대비 현재가 하락 (종가 < 시가)
    """
    return df[df['종가'] < df['시가']]

@staticmethod
def filter_sideways_only(
    df: pd.DataFrame,
    max_change_rate: float = 5.0
) -> pd.DataFrame:
    """
    횡보 종목만 필터링

    조건:
    - 등락률 ±5% 이내

    Returns:
        횡보 종목만 포함된 DataFrame
    """
    intraday_change = (df['종가'] / df['시가'] - 1) * 100

    return df[abs(intraday_change) <= max_change_rate]
```

### 4. 섹터 필터 (Sector Filters)

```python
@staticmethod
def filter_by_sector(
    df: pd.DataFrame,
    sector_codes: list
) -> pd.DataFrame:
    """
    특정 섹터만 필터링

    Args:
        sector_codes: ['IT', 'BIO', 'AUTO'] 등

    Returns:
        해당 섹터만 포함된 DataFrame
    """
    return df[df['섹터'].isin(sector_codes)]

@staticmethod
def exclude_sectors(
    df: pd.DataFrame,
    exclude_codes: list = ['REIT', 'ETF']
) -> pd.DataFrame:
    """
    특정 섹터 제외

    기본값:
    - REIT: 부동산 투자 신탁
    - ETF: 상장지수펀드
    """
    return df[~df['섹터'].isin(exclude_codes)]
```

---

## 🎯 점수화 (Scoring)

### 1. 정규화 함수

```python
# backend/app/utils/normalization.py

class NormalizationUtils:
    """
    점수 정규화 유틸리티
    """

    @staticmethod
    def normalize_column(
        df: pd.DataFrame,
        col: str,
        method: str = "min-max"
    ) -> pd.Series:
        """
        컬럼 정규화 (0-1)

        Args:
            col: 정규화할 컬럼명
            method: "min-max" | "z-score" | "rank"

        Returns:
            정규화된 Series (0-1)
        """
        if method == "min-max":
            min_val = df[col].min()
            max_val = df[col].max()

            if max_val == min_val:
                return pd.Series([0.5] * len(df), index=df.index)

            return (df[col] - min_val) / (max_val - min_val)

        elif method == "z-score":
            mean = df[col].mean()
            std = df[col].std()

            if std == 0:
                return pd.Series([0.5] * len(df), index=df.index)

            z_scores = (df[col] - mean) / std

            # 0-1 범위로 변환 (대략 ±3σ 기준)
            return (z_scores + 3) / 6

        elif method == "rank":
            # 순위 기반 정규화
            ranks = df[col].rank(pct=True)
            return ranks
```

### 2. 복합 점수 계산

```python
class ScoreCalculator:
    """
    복합 점수 계산기
    """

    @staticmethod
    def calculate_composite_score(
        df: pd.DataFrame,
        metrics: dict
    ) -> pd.DataFrame:
        """
        복합 점수 계산

        Args:
            df: 데이터프레임
            metrics: {
                "metric_name": {
                    "column": "컬럼명",
                    "weight": 가중치,
                    "method": "min-max" | "z-score" | "rank"
                }
            }

        Example:
            metrics = {
                "volume": {
                    "column": "거래량증가율",
                    "weight": 0.6,
                    "method": "min-max"
                },
                "trading_value": {
                    "column": "거래대금",
                    "weight": 0.4,
                    "method": "min-max"
                }
            }

        Returns:
            복합점수가 추가된 DataFrame
        """
        norm_utils = NormalizationUtils()

        # 각 지표 정규화
        for metric_name, config in metrics.items():
            col = config['column']
            method = config.get('method', 'min-max')

            # 정규화
            df[f"{col}_norm"] = norm_utils.normalize_column(df, col, method)

        # 복합 점수 계산 (가중 평균)
        df['복합점수'] = 0

        for metric_name, config in metrics.items():
            col = config['column']
            weight = config['weight']

            df['복합점수'] += df[f"{col}_norm"] * weight

        return df
```

---

## 📋 트리거별 점수 계산 예시

### 1. 거래량 급증 트리거

```python
def score_volume_surge(df: pd.DataFrame) -> pd.DataFrame:
    """
    거래량 급증 트리거 점수 계산

    점수 = 거래량증가율(60%) + 절대거래량(40%)
    """
    calculator = ScoreCalculator()

    metrics = {
        "volume_change": {
            "column": "거래량증가율",
            "weight": 0.6,
            "method": "min-max"
        },
        "volume_abs": {
            "column": "거래량",
            "weight": 0.4,
            "method": "min-max"
        }
    }

    return calculator.calculate_composite_score(df, metrics)
```

### 2. 갭 상승 트리거

```python
def score_gap_up(df: pd.DataFrame) -> pd.DataFrame:
    """
    갭 상승 트리거 점수 계산

    점수 = 갭상승률(50%) + 장중등락률(30%) + 거래대금(20%)
    """
    calculator = ScoreCalculator()

    metrics = {
        "gap_ratio": {
            "column": "갭상승률",
            "weight": 0.5,
            "method": "min-max"
        },
        "intraday_change": {
            "column": "장중등락률",
            "weight": 0.3,
            "method": "min-max"
        },
        "trading_value": {
            "column": "거래대금",
            "weight": 0.2,
            "method": "min-max"
        }
    }

    return calculator.calculate_composite_score(df, metrics)
```

### 3. 시총 대비 자금유입 트리거

```python
def score_fund_inflow(df: pd.DataFrame) -> pd.DataFrame:
    """
    시총 대비 자금유입 트리거 점수 계산

    점수 = 회전율(70%) + 거래대금(30%)
    """
    calculator = ScoreCalculator()

    metrics = {
        "turnover_ratio": {
            "column": "회전율",
            "weight": 0.7,
            "method": "min-max"
        },
        "trading_value": {
            "column": "거래대금",
            "weight": 0.3,
            "method": "min-max"
        }
    }

    return calculator.calculate_composite_score(df, metrics)
```

### 4. 일중 상승률 트리거

```python
def score_intraday_rise(df: pd.DataFrame) -> pd.DataFrame:
    """
    일중 상승률 트리거 점수 계산

    점수 = 장중등락률(60%) + 거래대금(40%)
    """
    calculator = ScoreCalculator()

    metrics = {
        "intraday_change": {
            "column": "장중등락률",
            "weight": 0.6,
            "method": "min-max"
        },
        "trading_value": {
            "column": "거래대금",
            "weight": 0.4,
            "method": "min-max"
        }
    }

    return calculator.calculate_composite_score(df, metrics)
```

### 5. 마감 강도 트리거

```python
def score_closing_strength(df: pd.DataFrame) -> pd.DataFrame:
    """
    마감 강도 트리거 점수 계산

    점수 = 마감강도(50%) + 거래량증가율(30%) + 거래대금(20%)
    """
    calculator = ScoreCalculator()

    metrics = {
        "closing_strength": {
            "column": "마감강도",
            "weight": 0.5,
            "method": "min-max"
        },
        "volume_change": {
            "column": "거래량증가율",
            "weight": 0.3,
            "method": "min-max"
        },
        "trading_value": {
            "column": "거래대금",
            "weight": 0.2,
            "method": "min-max"
        }
    }

    return calculator.calculate_composite_score(df, metrics)
```

### 6. 횡보주 거래량 트리거

```python
def score_sideways_volume(df: pd.DataFrame) -> pd.DataFrame:
    """
    횡보주 거래량 트리거 점수 계산

    점수 = 거래량증가율(60%) + 거래대금(40%)
    """
    calculator = ScoreCalculator()

    metrics = {
        "volume_change": {
            "column": "거래량증가율",
            "weight": 0.6,
            "method": "min-max"
        },
        "trading_value": {
            "column": "거래대금",
            "weight": 0.4,
            "method": "min-max"
        }
    }

    return calculator.calculate_composite_score(df, metrics)
```

---

## 🏆 Top N 선정

```python
class RankingUtils:
    """
    순위 선정 유틸리티
    """

    @staticmethod
    def select_top_n(
        df: pd.DataFrame,
        score_col: str = "복합점수",
        top_n: int = 3
    ) -> pd.DataFrame:
        """
        상위 N개 종목 선정

        Args:
            df: 데이터프레임
            score_col: 점수 컬럼명
            top_n: 선정할 개수

        Returns:
            상위 N개 종목 DataFrame
        """
        # 점수 기준 내림차순 정렬
        sorted_df = df.sort_values(by=score_col, ascending=False)

        # 상위 N개 선정
        return sorted_df.head(top_n).reset_index(drop=True)

    @staticmethod
    def select_top_n_by_group(
        df: pd.DataFrame,
        group_col: str,
        score_col: str = "복합점수",
        top_n: int = 3
    ) -> pd.DataFrame:
        """
        그룹별 상위 N개 선정

        Args:
            group_col: 그룹 컬럼 (예: "섹터", "트리거타입")
            score_col: 점수 컬럼명
            top_n: 그룹당 선정할 개수

        Returns:
            그룹별 상위 N개 DataFrame
        """
        result = df.groupby(group_col, group_keys=False).apply(
            lambda x: x.nlargest(top_n, score_col)
        )

        return result.reset_index(drop=True)
```

---

## 🔄 전체 파이프라인 통합

```python
# backend/app/services/scoring_pipeline.py

class ScoringPipeline:
    """
    필터링 → 점수화 → 선정 전체 파이프라인
    """

    def __init__(self):
        self.filter = StockFilter()
        self.scorer = ScoreCalculator()
        self.ranker = RankingUtils()

    def process(
        self,
        df: pd.DataFrame,
        trigger_type: str,
        top_n: int = 3
    ) -> pd.DataFrame:
        """
        급등주 스크리닝 전체 프로세스

        Args:
            df: 원본 시장 데이터
            trigger_type: "volume_surge" | "gap_up" | ...
            top_n: 선정할 종목 수

        Returns:
            최종 선정된 급등주 DataFrame
        """
        # 1. 절대적 필터링
        filtered = self.filter.apply_absolute_filters(df)

        # 2. 상대적 필터링
        filtered = self.filter.apply_relative_filters(filtered)

        # 3. 트리거별 추가 필터링
        if trigger_type in ["volume_surge", "gap_up", "fund_inflow"]:
            filtered = self.filter.filter_uptrend_only(filtered)
        elif trigger_type == "sideways_volume":
            filtered = self.filter.filter_sideways_only(filtered)

        # 4. 점수 계산
        if trigger_type == "volume_surge":
            scored = score_volume_surge(filtered)
        elif trigger_type == "gap_up":
            scored = score_gap_up(filtered)
        elif trigger_type == "fund_inflow":
            scored = score_fund_inflow(filtered)
        elif trigger_type == "intraday_rise":
            scored = score_intraday_rise(filtered)
        elif trigger_type == "closing_strength":
            scored = score_closing_strength(filtered)
        elif trigger_type == "sideways_volume":
            scored = score_sideways_volume(filtered)

        # 5. Top N 선정
        result = self.ranker.select_top_n(scored, top_n=top_n)

        # 6. 메타데이터 추가
        result['트리거타입'] = trigger_type
        result['선정시간'] = datetime.now()

        return result
```

---

## ⚠️ 주의사항

### 1. 데이터 품질 검증

```python
def validate_data_quality(df: pd.DataFrame) -> bool:
    """
    데이터 품질 검증

    체크 항목:
    - NaN 값 존재 여부
    - 음수 값 (가격, 거래량)
    - 이상치 (3σ 초과)
    """
    # NaN 체크
    if df.isnull().any().any():
        logger.warning("NaN values detected")
        return False

    # 음수 체크
    if (df[['시가', '고가', '저가', '종가', '거래량']] < 0).any().any():
        logger.error("Negative values detected")
        return False

    return True
```

### 2. 빈 결과 처리

```python
if len(filtered) == 0:
    logger.warning(f"No stocks passed filtering for {trigger_type}")
    return pd.DataFrame()  # 빈 DataFrame 반환
```

### 3. 점수 분포 확인

```python
# 점수 분포 로깅
logger.info(f"Score distribution: min={df['복합점수'].min():.4f}, "
            f"max={df['복합점수'].max():.4f}, "
            f"mean={df['복합점수'].mean():.4f}")
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
