"""
metrics.py 단위 테스트

모든 지표 계산 함수에 대한 단위 테스트
"""

import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from app.utils.metrics import MetricsCalculator


@pytest.fixture
def sample_prices():
    """테스트용 샘플 가격 시계열 (60일)"""
    np.random.seed(42)
    base_price = 50000
    returns = np.random.normal(0.001, 0.02, 60)  # 평균 0.1%, 표준편차 2%
    prices = [base_price]

    for ret in returns:
        prices.append(prices[-1] * (1 + ret))

    return pd.Series(prices)


@pytest.fixture
def sample_df():
    """테스트용 샘플 데이터프레임"""
    return pd.DataFrame({
        'ticker': ['A001', 'A002', 'A003'],
        '시가': [50000, 80000, 120000],
        '종가': [55000, 75000, 125000],
        '고가': [56000, 82000, 128000],
        '저가': [49000, 74000, 118000],
        '거래량': [1000000, 500000, 800000]
    }).set_index('ticker')


@pytest.fixture
def sample_prev_df():
    """테스트용 전일 데이터프레임"""
    return pd.DataFrame({
        'ticker': ['A001', 'A002', 'A003'],
        '종가': [50000, 82000, 118000],
        '거래량': [500000, 1000000, 600000]
    }).set_index('ticker')


class TestMetricsCalculator:
    """MetricsCalculator 테스트 클래스"""

    def test_calculate_rsi(self, sample_prices):
        """RSI 계산 테스트"""
        rsi = MetricsCalculator.calculate_rsi(sample_prices, period=14)

        # RSI는 0-100 범위
        assert 0 <= rsi <= 100

        # 충분한 데이터가 있으면 NaN이 아님
        assert not np.isnan(rsi)

    def test_calculate_rsi_insufficient_data(self):
        """RSI 계산 - 데이터 부족 케이스"""
        short_prices = pd.Series([100, 101, 102])

        rsi = MetricsCalculator.calculate_rsi(short_prices, period=14)

        # 데이터가 부족하면 중립값 50.0 반환
        assert rsi == 50.0

    def test_calculate_macd(self, sample_prices):
        """MACD 계산 테스트"""
        result = MetricsCalculator.calculate_macd(sample_prices)

        # 반환 구조 검증
        assert 'macd' in result
        assert 'signal' in result
        assert 'histogram' in result
        assert 'status' in result

        # status는 정해진 값 중 하나
        assert result['status'] in ['golden_cross', 'dead_cross', 'neutral']

        # MACD 값들은 float
        assert isinstance(result['macd'], float)
        assert isinstance(result['signal'], float)
        assert isinstance(result['histogram'], float)

    def test_calculate_macd_insufficient_data(self):
        """MACD 계산 - 데이터 부족 케이스"""
        short_prices = pd.Series([100] * 10)

        result = MetricsCalculator.calculate_macd(short_prices)

        # 데이터가 부족하면 기본값 반환
        assert result['macd'] == 0.0
        assert result['signal'] == 0.0
        assert result['histogram'] == 0.0
        assert result['status'] == 'neutral'

    def test_calculate_moving_averages(self, sample_prices):
        """이동평균 계산 테스트"""
        mas = MetricsCalculator.calculate_moving_averages(sample_prices, periods=[5, 20, 60])

        # 모든 기간에 대한 이동평균 반환
        assert 5 in mas
        assert 20 in mas
        assert 60 in mas

        # 이동평균 값은 양수
        assert mas[5] > 0
        assert mas[20] > 0
        assert mas[60] > 0

        # 일반적으로 5일 MA > 20일 MA (최근 상승 추세인 경우)
        # 또는 반대 (하락 추세인 경우)
        assert isinstance(mas[5], float)

    def test_calculate_gap_ratio(self, sample_df, sample_prev_df):
        """갭 상승률 계산 테스트"""
        gap_ratio = MetricsCalculator.calculate_gap_ratio(sample_df, sample_prev_df)

        # Series 반환
        assert isinstance(gap_ratio, pd.Series)

        # 모든 종목에 대해 계산됨
        assert len(gap_ratio) == 3

        # A001: 시가 50000, 전일종가 50000 → 0%
        assert abs(gap_ratio['A001'] - 0.0) < 0.1

        # A002: 시가 80000, 전일종가 82000 → -2.44%
        assert gap_ratio['A002'] < 0

        # A003: 시가 120000, 전일종가 118000 → +1.69%
        assert gap_ratio['A003'] > 0

    def test_calculate_intraday_change(self, sample_df):
        """장중 등락률 계산 테스트"""
        intraday = MetricsCalculator.calculate_intraday_change(sample_df)

        # Series 반환
        assert isinstance(intraday, pd.Series)

        # A001: (55000 / 50000 - 1) * 100 = 10%
        assert abs(intraday['A001'] - 10.0) < 0.1

        # A002: (75000 / 80000 - 1) * 100 = -6.25%
        assert abs(intraday['A002'] - (-6.25)) < 0.1

        # A003: (125000 / 120000 - 1) * 100 = 4.17%
        assert abs(intraday['A003'] - 4.17) < 0.1

    def test_calculate_volume_change(self, sample_df, sample_prev_df):
        """거래량 증가율 계산 테스트"""
        volume_change = MetricsCalculator.calculate_volume_change(sample_df, sample_prev_df)

        # Series 반환
        assert isinstance(volume_change, pd.Series)

        # A001: (1000000 / 500000 - 1) * 100 = 100%
        assert abs(volume_change['A001'] - 100.0) < 0.1

        # A002: (500000 / 1000000 - 1) * 100 = -50%
        assert abs(volume_change['A002'] - (-50.0)) < 0.1

    def test_calculate_closing_strength(self, sample_df):
        """마감 강도 계산 테스트"""
        strength = MetricsCalculator.calculate_closing_strength(sample_df)

        # Series 반환
        assert isinstance(strength, pd.Series)

        # 모든 값은 0-1 범위
        assert all((strength >= 0) & (strength <= 1))

        # A001: (55000 - 49000) / (56000 - 49000) = 6000 / 7000 = 0.857
        assert 0.8 < strength['A001'] < 0.9

    def test_calculate_fund_inflow_ratio(self):
        """자금유입비율 계산 테스트"""
        ratio = MetricsCalculator.calculate_fund_inflow_ratio(
            trading_value=1_000_000_000_000,  # 1조
            market_cap=430_000_000_000_000    # 430조
        )

        # (1조 / 430조) * 100 = 0.233%
        assert abs(ratio - 0.233) < 0.01

        # 시가총액 0일 때
        ratio_zero = MetricsCalculator.calculate_fund_inflow_ratio(
            trading_value=1_000_000_000_000,
            market_cap=0
        )
        assert ratio_zero == 0.0

    def test_calculate_momentum_score(self):
        """모멘텀 점수 계산 테스트"""
        # 모두 긍정적인 수익률
        score_positive = MetricsCalculator.calculate_momentum_score(
            returns_1d=5.0,
            returns_7d=15.0,
            returns_30d=25.0
        )

        # 0-10 범위
        assert 0 <= score_positive <= 10

        # 긍정적인 수익률이면 5점 이상
        assert score_positive > 5.0

        # 모두 부정적인 수익률
        score_negative = MetricsCalculator.calculate_momentum_score(
            returns_1d=-5.0,
            returns_7d=-10.0,
            returns_30d=-15.0
        )

        # 부정적인 수익률이면 5점 이하
        assert score_negative < 5.0

    def test_calculate_technical_score(self):
        """기술적 지표 점수 계산 테스트"""
        # 모두 긍정적인 신호
        score_bullish = MetricsCalculator.calculate_technical_score(
            rsi=65.0,
            macd_status='golden_cross',
            ma_position='상회'
        )

        # 0-10 범위
        assert 0 <= score_bullish <= 10

        # 긍정적인 신호이면 높은 점수
        assert score_bullish > 5.0

        # 모두 부정적인 신호
        score_bearish = MetricsCalculator.calculate_technical_score(
            rsi=35.0,
            macd_status='dead_cross',
            ma_position='하회'
        )

        # 부정적인 신호이면 낮은 점수
        assert score_bearish < 5.0

    def test_calculate_financial_score(self):
        """재무 점수 계산 테스트"""
        # 우수한 재무 상태
        score_good = MetricsCalculator.calculate_financial_score(
            roe=15.0,
            debt_ratio=45.0,
            revenue_growth=12.0
        )

        # 0-10 범위
        assert 0 <= score_good <= 10

        # 우수한 재무이면 높은 점수
        assert score_good > 5.0

        # 나쁜 재무 상태
        score_bad = MetricsCalculator.calculate_financial_score(
            roe=3.0,
            debt_ratio=180.0,
            revenue_growth=-10.0
        )

        # 나쁜 재무이면 낮은 점수
        assert score_bad < 5.0

    def test_calculate_volume_score(self):
        """거래량 점수 계산 테스트"""
        # 높은 거래량
        score_high = MetricsCalculator.calculate_volume_score(
            volume=20_000_000,
            avg_volume=15_000_000,
            volume_increase_rate=33.3
        )

        # 0-10 범위
        assert 0 <= score_high <= 10

        # 높은 거래량이면 높은 점수
        assert score_high > 5.0

        # 낮은 거래량
        score_low = MetricsCalculator.calculate_volume_score(
            volume=5_000_000,
            avg_volume=15_000_000,
            volume_increase_rate=-50.0
        )

        # 낮은 거래량이면 낮은 점수
        assert score_low < 5.0

    def test_calculate_sentiment_score(self):
        """센티먼트 점수 계산 테스트"""
        # 긍정적인 뉴스
        score_positive = MetricsCalculator.calculate_sentiment_score(
            positive_count=8,
            negative_count=2,
            neutral_count=3
        )

        # 0-10 범위
        assert 0 <= score_positive <= 10

        # 긍정적이면 높은 점수
        assert score_positive > 5.0

        # 부정적인 뉴스
        score_negative = MetricsCalculator.calculate_sentiment_score(
            positive_count=2,
            negative_count=8,
            neutral_count=3
        )

        # 부정적이면 낮은 점수
        assert score_negative < 5.0

        # 뉴스가 없으면 중립 (5.0)
        score_none = MetricsCalculator.calculate_sentiment_score(
            positive_count=0,
            negative_count=0,
            neutral_count=0
        )
        assert score_none == 5.0

    def test_calculate_ema(self, sample_prices):
        """EMA 계산 테스트"""
        ema_12 = MetricsCalculator.calculate_ema(sample_prices, period=12)

        # Series 반환
        assert isinstance(ema_12, pd.Series)

        # 길이는 원본과 동일
        assert len(ema_12) == len(sample_prices)

        # EMA 값들은 양수
        assert all(ema_12 > 0)

        # EMA는 최근 가격에 더 민감 (단순 이동평균과 비교)
        sma_12 = sample_prices.rolling(window=12).mean()

        # 최근 가격이 상승했다면 EMA > SMA
        # (이는 데이터에 따라 다를 수 있으므로 단순히 계산이 되었는지만 확인)
        assert not ema_12.iloc[-1] == sma_12.iloc[-1]  # 다른 값이어야 함

    def test_edge_case_zero_division(self):
        """0으로 나누기 방지 테스트"""
        # 자금유입비율 - 시가총액 0
        ratio = MetricsCalculator.calculate_fund_inflow_ratio(
            trading_value=1_000_000,
            market_cap=0
        )
        assert ratio == 0.0

        # 거래량 점수 - 평균 거래량 0
        score = MetricsCalculator.calculate_volume_score(
            volume=1_000_000,
            avg_volume=0,
            volume_increase_rate=0.0
        )
        assert 0 <= score <= 10

    def test_score_ranges(self):
        """모든 점수 함수가 0-10 범위를 지키는지 테스트"""
        # 극단적인 값들로 테스트
        scores = []

        # 모멘텀 점수
        scores.append(MetricsCalculator.calculate_momentum_score(100, 100, 100))
        scores.append(MetricsCalculator.calculate_momentum_score(-100, -100, -100))

        # 기술적 점수
        scores.append(MetricsCalculator.calculate_technical_score(
            100, 'golden_cross', '상회'))
        scores.append(MetricsCalculator.calculate_technical_score(
            0, 'dead_cross', '하회'))

        # 재무 점수
        scores.append(MetricsCalculator.calculate_financial_score(100, 0, 100))
        scores.append(MetricsCalculator.calculate_financial_score(0, 300, -100))

        # 거래량 점수
        scores.append(MetricsCalculator.calculate_volume_score(
            1000000, 100000, 1000))
        scores.append(MetricsCalculator.calculate_volume_score(
            10000, 1000000, -90))

        # 센티먼트 점수
        scores.append(MetricsCalculator.calculate_sentiment_score(100, 0, 0))
        scores.append(MetricsCalculator.calculate_sentiment_score(0, 100, 0))

        # 모든 점수가 0-10 범위 내
        for score in scores:
            assert 0 <= score <= 10, f"Score {score} is out of range [0, 10]"
