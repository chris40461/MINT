# 참고: docs/backend/02-trigger-detection.md
# 참고: docs/backend/04-scoring.md

"""
지표 계산 유틸리티

기술적 지표, 트리거 지표 등을 계산합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """지표 계산 클래스"""

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
        """
        RSI (Relative Strength Index) 계산

        Args:
            prices: 종가 시계열 (최소 period+1 일치)
            period: 기간 (기본값: 14일)

        Returns:
            RSI 값 (0-100)

        Example:
            >>> prices = pd.Series([70000, 71000, 72000, 71500, 73000])
            >>> rsi = MetricsCalculator.calculate_rsi(prices, period=14)
            >>> print(rsi)  # 65.5
        """
        if len(prices) < period + 1:
            logger.warning(f"RSI 계산에 충분한 데이터가 없습니다 (필요: {period + 1}, 실제: {len(prices)})")
            return 50.0  # 중립값 반환

        # 가격 변화량 계산
        delta = prices.diff()

        # 상승분/하락분 분리
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 평균 상승분/하락분 계산 (지수이동평균)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Division by Zero 방지: avg_loss가 0이면 작은 양수로 대체
        avg_loss = avg_loss.replace(0, 1e-10)

        # RS = 평균상승분 / 평균하락분
        rs = avg_gain / avg_loss

        # RSI = 100 - (100 / (1 + RS))
        rsi = 100 - (100 / (1 + rs))

        # 최신 RSI 값 반환
        return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0

    @staticmethod
    def calculate_macd(
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, float]:
        """
        MACD (Moving Average Convergence Divergence) 계산

        Args:
            prices: 종가 시계열
            fast_period: 빠른 EMA 기간 (기본값: 12)
            slow_period: 느린 EMA 기간 (기본값: 26)
            signal_period: 시그널선 기간 (기본값: 9)

        Returns:
            {
                'macd': float,
                'signal': float,
                'histogram': float,
                'status': str  # 'golden_cross', 'dead_cross', 'neutral'
            }

        Example:
            >>> result = MetricsCalculator.calculate_macd(prices)
            >>> print(result['status'])  # 'golden_cross'
        """
        if len(prices) < slow_period + signal_period:
            logger.warning(f"MACD 계산에 충분한 데이터가 없습니다")
            return {
                'macd': 0.0,
                'signal': 0.0,
                'histogram': 0.0,
                'status': 'neutral'
            }

        # Fast EMA 계산 (12일)
        fast_ema = MetricsCalculator.calculate_ema(prices, fast_period)

        # Slow EMA 계산 (26일)
        slow_ema = MetricsCalculator.calculate_ema(prices, slow_period)

        # MACD = Fast EMA - Slow EMA
        macd_line = fast_ema - slow_ema

        # Signal = MACD의 9일 EMA
        signal_line = MetricsCalculator.calculate_ema(macd_line, signal_period)

        # Histogram = MACD - Signal
        histogram = macd_line - signal_line

        # 최신 값들
        macd_current = float(macd_line.iloc[-1])
        signal_current = float(signal_line.iloc[-1])
        histogram_current = float(histogram.iloc[-1])

        # 골든크로스/데드크로스 판단 (전일과 비교)
        if len(histogram) >= 2:
            histogram_prev = float(histogram.iloc[-2])

            if histogram_prev < 0 and histogram_current > 0:
                status = 'golden_cross'  # 골든크로스 (매수 신호)
            elif histogram_prev > 0 and histogram_current < 0:
                status = 'dead_cross'    # 데드크로스 (매도 신호)
            else:
                status = 'neutral'
        else:
            status = 'neutral'

        return {
            'macd': macd_current,
            'signal': signal_current,
            'histogram': histogram_current,
            'status': status
        }

    @staticmethod
    def calculate_moving_averages(
        prices: pd.Series,
        periods: list[int] = [5, 20, 60]
    ) -> Dict[int, float]:
        """
        이동평균선 계산

        Args:
            prices: 종가 시계열
            periods: 이동평균 기간 리스트 (기본값: [5, 20, 60])

        Returns:
            {5: 71000.0, 20: 70500.0, 60: 69000.0}

        Example:
            >>> mas = MetricsCalculator.calculate_moving_averages(prices)
            >>> print(mas[20])  # 20일 이동평균
        """
        result = {}

        # 각 기간별 단순이동평균 계산
        for period in periods:
            if len(prices) >= period:
                # SMA = sum(prices[-period:]) / period
                ma = prices.rolling(window=period).mean().iloc[-1]
                result[period] = float(ma) if not np.isnan(ma) else 0.0
            else:
                logger.warning(f"{period}일 이동평균 계산에 충분한 데이터가 없습니다")
                result[period] = 0.0

        return result

    @staticmethod
    def calculate_gap_ratio(
        current_df: pd.DataFrame,
        prev_df: pd.DataFrame
    ) -> pd.Series:
        """
        갭 상승률 계산 (DataFrame 버전)

        Args:
            current_df: 금일 데이터프레임 (시가 포함)
            prev_df: 전일 데이터프레임 (종가 포함)

        Returns:
            갭 상승률 (%) Series

        Example:
            >>> gap_ratio = MetricsCalculator.calculate_gap_ratio(current, prev)
            >>> print(gap_ratio.mean())
        """
        # 인덱스 기준으로 조인 (ticker)
        merged = current_df.join(prev_df['종가'], rsuffix='_prev')
        gap_ratio = (merged['시가'] / merged['종가_prev'] - 1) * 100
        return gap_ratio

    @staticmethod
    def calculate_intraday_change(df: pd.DataFrame) -> pd.Series:
        """
        장중 등락률 계산 (DataFrame 버전)

        Args:
            df: 데이터프레임 (종가, 시가 포함)

        Returns:
            장중 등락률 (%) Series

        Example:
            >>> intraday = MetricsCalculator.calculate_intraday_change(df)
            >>> print(intraday.mean())
        """
        return (df['종가'] / df['시가'] - 1) * 100

    @staticmethod
    def calculate_volume_change(
        current_df: pd.DataFrame,
        prev_df: pd.DataFrame
    ) -> pd.Series:
        """
        거래량 증가율 계산 (DataFrame 버전)

        Args:
            current_df: 금일 데이터프레임 (거래량 포함)
            prev_df: 전일 데이터프레임 (거래량 포함)

        Returns:
            거래량 증가율 (%) Series

        Example:
            >>> volume_change = MetricsCalculator.calculate_volume_change(current, prev)
            >>> print(volume_change.mean())
        """
        merged = current_df.join(prev_df['거래량'], rsuffix='_prev')
        volume_change = (merged['거래량'] / merged['거래량_prev'] - 1) * 100
        return volume_change

    @staticmethod
    def calculate_closing_strength(df: pd.DataFrame) -> pd.Series:
        """
        마감 강도 계산 (DataFrame 버전)

        1에 가까울수록 강력한 매수세

        Args:
            df: 데이터프레임 (종가, 고가, 저가 포함)

        Returns:
            마감 강도 (0-1) Series

        Example:
            >>> strength = MetricsCalculator.calculate_closing_strength(df)
            >>> print(strength.mean())
        """
        numerator = df['종가'] - df['저가']
        denominator = df['고가'] - df['저가']

        # 0으로 나누기 방지 (상하한가 등)
        denominator = denominator.replace(0, 0.01)

        strength = numerator / denominator
        return strength.clip(0, 1)  # 0-1 범위로 제한

    @staticmethod
    def calculate_fund_inflow_ratio(
        trading_value: int,
        market_cap: int
    ) -> float:
        """
        자금유입비율 계산 (시총 대비 거래대금)

        Args:
            trading_value: 거래대금
            market_cap: 시가총액

        Returns:
            자금유입비율 (%)

        Example:
            >>> ratio = MetricsCalculator.calculate_fund_inflow_ratio(
            ...     trading_value=1_000_000_000_000,  # 1조
            ...     market_cap=430_000_000_000_000    # 430조
            ... )
            >>> print(ratio)  # 0.233
        """
        if market_cap == 0:
            return 0.0

        # (거래대금 / 시가총액) × 100
        return (trading_value / market_cap) * 100

    @staticmethod
    def calculate_momentum_score(
        returns_1d: float,
        returns_7d: float,
        returns_30d: float
    ) -> float:
        """
        모멘텀 점수 계산 (0-10)

        가중치: 1일(50%), 7일(30%), 30일(20%)

        Args:
            returns_1d: 1일 수익률 (%)
            returns_7d: 7일 수익률 (%)
            returns_30d: 30일 수익률 (%)

        Returns:
            모멘텀 점수 (0-10)

        Example:
            >>> score = MetricsCalculator.calculate_momentum_score(
            ...     returns_1d=5.0,
            ...     returns_7d=15.0,
            ...     returns_30d=25.0
            ... )
            >>> print(score)  # 8.5
        """
        # 각 수익률을 0-10 스케일로 변환
        # 변환 로직: -20% = 0점, 0% = 5점, +20% = 10점
        def returns_to_score(returns: float) -> float:
            # -20 ~ +20 범위를 0-10으로 변환
            score = 5.0 + (returns / 20.0) * 5.0
            return max(0.0, min(10.0, score))  # 0-10 범위로 제한

        score_1d = returns_to_score(returns_1d)
        score_7d = returns_to_score(returns_7d)
        score_30d = returns_to_score(returns_30d)

        # 가중 평균 계산 (1일 50%, 7일 30%, 30일 20%)
        momentum_score = (
            score_1d * 0.5 +
            score_7d * 0.3 +
            score_30d * 0.2
        )

        return round(momentum_score, 2)

    @staticmethod
    def calculate_technical_score(
        rsi: float,
        macd_status: str,
        ma_position: str
    ) -> float:
        """
        기술적 지표 종합 점수 (0-10)

        Args:
            rsi: RSI 값 (0-100)
            macd_status: MACD 상태 ('golden_cross', 'dead_cross', 'neutral')
            ma_position: 이동평균선 위치 ('상회', '하회', '중립')

        Returns:
            기술적 점수 (0-10)

        Example:
            >>> score = MetricsCalculator.calculate_technical_score(
            ...     rsi=65.0,
            ...     macd_status='golden_cross',
            ...     ma_position='상회'
            ... )
            >>> print(score)  # 8.5
        """
        # RSI 점수화 (30-70이 중립, 70+ 과매수, 30- 과매도)
        if rsi >= 70:
            rsi_score = 3.0  # 과매수 (긍정)
        elif rsi <= 30:
            rsi_score = 7.0  # 과매도 (반등 기회)
        else:
            # 30-70 범위: 5점 기준으로 ±2점
            rsi_score = 5.0 + ((rsi - 50) / 20.0) * 2.0

        # MACD 점수화 (골든크로스 +3, 데드크로스 -3, 중립 0)
        if macd_status == 'golden_cross':
            macd_score = 3.0
        elif macd_status == 'dead_cross':
            macd_score = -3.0
        else:
            macd_score = 0.0

        # MA 위치 점수화 (상회 +3, 하회 -3, 중립 0)
        if ma_position == '상회':
            ma_score = 3.0
        elif ma_position == '하회':
            ma_score = -3.0
        else:
            ma_score = 0.0

        # 종합 점수 계산 (0-10 스케일)
        total_score = rsi_score + macd_score + ma_score

        # 0-10 범위로 정규화
        normalized_score = max(0.0, min(10.0, total_score))

        return round(normalized_score, 2)

    @staticmethod
    def calculate_financial_score(
        roe: float,
        debt_ratio: float,
        revenue_growth: float
    ) -> float:
        """
        재무 건전성 점수 (0-10)

        Args:
            roe: ROE (%)
            debt_ratio: 부채비율 (%)
            revenue_growth: 매출 성장률 (%)

        Returns:
            재무 점수 (0-10)

        Example:
            >>> score = MetricsCalculator.calculate_financial_score(
            ...     roe=15.0,
            ...     debt_ratio=45.0,
            ...     revenue_growth=12.0
            ... )
            >>> print(score)  # 8.2
        """
        # ROE 점수화 (10% 이상 우수)
        # 0% = 0점, 10% = 5점, 20% = 10점
        roe_score = min(10.0, max(0.0, (roe / 20.0) * 10.0))

        # 부채비율 점수화 (낮을수록 좋음)
        # 0% = 10점, 100% = 5점, 200% = 0점
        debt_score = 10.0 - (debt_ratio / 200.0) * 10.0
        debt_score = max(0.0, min(10.0, debt_score))

        # 매출성장률 점수화 (높을수록 좋음)
        # -20% = 0점, 0% = 5점, +20% = 10점
        revenue_score = 5.0 + (revenue_growth / 20.0) * 5.0
        revenue_score = max(0.0, min(10.0, revenue_score))

        # 가중 평균 (ROE 40%, 부채비율 30%, 매출성장률 30%)
        financial_score = (
            roe_score * 0.4 +
            debt_score * 0.3 +
            revenue_score * 0.3
        )

        return round(financial_score, 2)

    @staticmethod
    def calculate_volume_score(
        volume: int,
        avg_volume: int,
        volume_increase_rate: float
    ) -> float:
        """
        거래량 점수 (0-10)

        Args:
            volume: 현재 거래량
            avg_volume: 평균 거래량 (20일)
            volume_increase_rate: 전일 대비 증가율 (%)

        Returns:
            거래량 점수 (0-10)

        Example:
            >>> score = MetricsCalculator.calculate_volume_score(
            ...     volume=20_000_000,
            ...     avg_volume=15_000_000,
            ...     volume_increase_rate=33.3
            ... )
            >>> print(score)  # 8.0
        """
        # 평균 거래량 대비 비율 점수화
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        # 0.5배 = 0점, 1배 = 5점, 2배 = 10점
        ratio_score = min(10.0, max(0.0, (volume_ratio - 0.5) / 1.5 * 10.0))

        # 증가율 점수화
        # 0% = 5점, 50% = 10점, -50% = 0점
        increase_score = 5.0 + (volume_increase_rate / 50.0) * 5.0
        increase_score = max(0.0, min(10.0, increase_score))

        # 종합 점수 (비율 60%, 증가율 40%)
        volume_score = (
            ratio_score * 0.6 +
            increase_score * 0.4
        )

        return round(volume_score, 2)

    @staticmethod
    def calculate_sentiment_score(
        positive_count: int,
        negative_count: int,
        neutral_count: int
    ) -> float:
        """
        뉴스 센티먼트 점수 (0-10)

        Args:
            positive_count: 긍정 뉴스 개수
            negative_count: 부정 뉴스 개수
            neutral_count: 중립 뉴스 개수

        Returns:
            센티먼트 점수 (0-10)

        Example:
            >>> score = MetricsCalculator.calculate_sentiment_score(
            ...     positive_count=8,
            ...     negative_count=2,
            ...     neutral_count=3
            ... )
            >>> print(score)  # 7.5
        """
        total_count = positive_count + negative_count + neutral_count

        # 뉴스가 없으면 5.0 (중립)
        if total_count == 0:
            return 5.0

        # 긍정/부정 비율 계산
        positive_ratio = positive_count / total_count
        negative_ratio = negative_count / total_count

        # 0-10 스케일로 변환
        # 모두 부정 = 0점, 50%씩 = 5점, 모두 긍정 = 10점
        sentiment_score = positive_ratio * 10.0

        # 부정이 30% 이상이면 페널티
        if negative_ratio > 0.3:
            sentiment_score *= (1.0 - (negative_ratio - 0.3))

        return round(max(0.0, min(10.0, sentiment_score)), 2)

    @staticmethod
    def calculate_ema(
        prices: pd.Series,
        period: int
    ) -> pd.Series:
        """
        지수이동평균 (EMA) 계산

        Args:
            prices: 가격 시계열
            period: 기간

        Returns:
            EMA 시계열

        Example:
            >>> ema = MetricsCalculator.calculate_ema(prices, period=12)
        """
        # pandas의 ewm() 사용
        # EMA = prices.ewm(span=period, adjust=False).mean()
        return prices.ewm(span=period, adjust=False).mean()
