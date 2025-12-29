# 참고: docs/backend/04-scoring.md
# 참고: docs/backend/02-trigger-detection.md

"""
정규화 및 점수 계산 유틸리티

Min-Max 정규화, Z-Score 정규화, 복합 점수 계산
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ScoreCalculator:
    """점수 계산 클래스"""

    @staticmethod
    def min_max_normalize(
        values: pd.Series,
        new_min: float = 0.0,
        new_max: float = 1.0
    ) -> pd.Series:
        """
        Min-Max 정규화 (0-1 스케일 또는 사용자 지정 범위)

        공식: (x - min) / (max - min) × (new_max - new_min) + new_min

        Args:
            values: 정규화할 값들
            new_min: 새로운 최소값 (기본값: 0.0)
            new_max: 새로운 최대값 (기본값: 1.0)

        Returns:
            정규화된 값들

        Example:
            >>> values = pd.Series([10, 20, 30, 40, 50])
            >>> normalized = ScoreCalculator.min_max_normalize(values)
            >>> print(normalized)  # [0.0, 0.25, 0.5, 0.75, 1.0]
        """
        min_val = values.min()
        max_val = values.max()

        # 모든 값이 동일한 경우
        if max_val == min_val:
            return pd.Series(0.5, index=values.index)

        # 0-1 정규화
        normalized = (values - min_val) / (max_val - min_val)

        # new_min, new_max 범위로 변환
        normalized = normalized * (new_max - new_min) + new_min

        return normalized

    @staticmethod
    def z_score_normalize(values: pd.Series) -> pd.Series:
        """
        Z-Score 정규화 (평균 0, 표준편차 1)

        공식: (x - mean) / std

        Args:
            values: 정규화할 값들

        Returns:
            정규화된 값들

        Example:
            >>> values = pd.Series([10, 20, 30, 40, 50])
            >>> z_scores = ScoreCalculator.z_score_normalize(values)
        """
        mean = values.mean()
        std = values.std()

        # std == 0인 경우 처리 (모두 0 반환)
        if std == 0 or np.isnan(std):
            return pd.Series(0.0, index=values.index)

        # (values - mean) / std
        return (values - mean) / std

    @staticmethod
    def normalize_and_score(
        df: pd.DataFrame,
        columns: List[str],
        weights: List[float],
        output_col: str = 'composite_score'
    ) -> pd.DataFrame:
        """
        여러 컬럼을 정규화하고 가중 복합 점수 계산

        Args:
            df: 데이터프레임
            columns: 점수화할 컬럼 리스트
            weights: 각 컬럼의 가중치 (합 = 1.0)
            output_col: 출력 컬럼명 (기본값: 'composite_score')

        Returns:
            복합 점수가 추가된 데이터프레임

        Raises:
            ValueError: weights 합이 1.0이 아닐 때

        Example:
            >>> df = ScoreCalculator.normalize_and_score(
            ...     df,
            ...     columns=['거래량증가율', '거래량'],
            ...     weights=[0.6, 0.4]
            ... )
            >>> print(df['composite_score'].mean())
        """
        if not np.isclose(sum(weights), 1.0):
            raise ValueError(f"Weights must sum to 1.0, got {sum(weights)}")

        # 각 컬럼 Min-Max 정규화
        normalized_cols = []
        for col in columns:
            norm_col_name = f"{col}_norm"
            df[norm_col_name] = ScoreCalculator.min_max_normalize(df[col])
            normalized_cols.append(norm_col_name)

        # 가중 평균 계산
        df[output_col] = sum(
            df[norm_col] * weight
            for norm_col, weight in zip(normalized_cols, weights)
        )

        return df

    @staticmethod
    def calculate_weighted_score(
        scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """
        가중 점수 계산

        Args:
            scores: {지표명: 점수} 딕셔너리
            weights: {지표명: 가중치} 딕셔너리

        Returns:
            가중 점수

        Example:
            >>> score = ScoreCalculator.calculate_weighted_score(
            ...     scores={'momentum': 8.0, 'volume': 9.0, 'sentiment': 7.0},
            ...     weights={'momentum': 0.3, 'volume': 0.25, 'sentiment': 0.2}
            ... )
            >>> print(score)  # 8.05
        """
        # 각 지표의 점수 × 가중치 합산
        weighted_score = 0.0

        for metric, weight in weights.items():
            # weights에 없는 지표는 무시
            if metric in scores:
                weighted_score += scores[metric] * weight

        return round(weighted_score, 2)

    @staticmethod
    def rank_normalize(
        values: pd.Series,
        ascending: bool = True
    ) -> pd.Series:
        """
        순위 기반 정규화 (0-1 스케일)

        Args:
            values: 정규화할 값들
            ascending: 오름차순 여부 (True: 낮을수록 0에 가까움)

        Returns:
            정규화된 값들 (0-1)

        Example:
            >>> values = pd.Series([10, 50, 30, 40, 20])
            >>> ranked = ScoreCalculator.rank_normalize(values, ascending=True)
            >>> print(ranked)  # [0.0, 1.0, 0.5, 0.75, 0.25]
        """
        # 순위 계산 (rank())
        ranks = values.rank(method='min', ascending=ascending)

        # (순위 - 1) / (N - 1)로 0-1 정규화
        n = len(values)
        if n <= 1:
            return pd.Series(0.5, index=values.index)

        normalized = (ranks - 1) / (n - 1)
        return normalized

    @staticmethod
    def percentile_rank(
        values: pd.Series,
        value: float
    ) -> float:
        """
        특정 값의 백분위 순위 계산

        Args:
            values: 값 분포
            value: 순위를 계산할 값

        Returns:
            백분위 순위 (0-100)

        Example:
            >>> values = pd.Series([10, 20, 30, 40, 50])
            >>> percentile = ScoreCalculator.percentile_rank(values, 35)
            >>> print(percentile)  # 70.0 (상위 30%)
        """
        # value보다 작거나 같은 값의 비율 계산
        count_below = (values <= value).sum()

        # (count(values <= value) / len(values)) × 100
        percentile = (count_below / len(values)) * 100

        return float(percentile)

    @staticmethod
    def sigmoid_normalize(
        values: pd.Series,
        midpoint: float = 0.0,
        steepness: float = 1.0
    ) -> pd.Series:
        """
        Sigmoid 정규화 (0-1 스케일, S자 곡선)

        공식: 1 / (1 + exp(-steepness × (x - midpoint)))

        Args:
            values: 정규화할 값들
            midpoint: S자 곡선의 중심점
            steepness: 곡선의 가파름 정도

        Returns:
            정규화된 값들 (0-1)

        Example:
            >>> values = pd.Series([-2, -1, 0, 1, 2])
            >>> normalized = ScoreCalculator.sigmoid_normalize(values)
        """
        # 1 / (1 + exp(-steepness × (values - midpoint)))
        sigmoid = 1 / (1 + np.exp(-steepness * (values - midpoint)))
        return sigmoid

    @staticmethod
    def log_normalize(
        values: pd.Series,
        base: float = np.e
    ) -> pd.Series:
        """
        로그 변환 정규화 (큰 값의 영향 감소)

        Args:
            values: 정규화할 값들 (양수)
            base: 로그 밑 (기본값: 자연로그)

        Returns:
            로그 변환된 값들

        Example:
            >>> values = pd.Series([1, 10, 100, 1000])
            >>> log_values = ScoreCalculator.log_normalize(values, base=10)
            >>> print(log_values)  # [0, 1, 2, 3]
        """
        # 0 이하 값 처리 (작은 양수로 대체)
        values_positive = values.clip(lower=1e-10)

        # log(values) / log(base)
        if base == np.e:
            log_values = np.log(values_positive)
        else:
            log_values = np.log(values_positive) / np.log(base)

        return log_values

    @staticmethod
    def clip_and_normalize(
        values: pd.Series,
        lower_percentile: float = 5.0,
        upper_percentile: float = 95.0
    ) -> pd.Series:
        """
        이상치 제거 후 정규화

        하위/상위 백분위수로 값을 잘라낸 후 0-1 정규화

        Args:
            values: 정규화할 값들
            lower_percentile: 하위 백분위수 (기본값: 5%)
            upper_percentile: 상위 백분위수 (기본값: 95%)

        Returns:
            정규화된 값들

        Example:
            >>> values = pd.Series([1, 2, 3, 4, 5, 100])  # 100은 이상치
            >>> normalized = ScoreCalculator.clip_and_normalize(values)
        """
        # 백분위수 계산
        lower_bound = values.quantile(lower_percentile / 100.0)
        upper_bound = values.quantile(upper_percentile / 100.0)

        # 값 clipping
        clipped = values.clip(lower=lower_bound, upper=upper_bound)

        # Min-Max 정규화
        normalized = ScoreCalculator.min_max_normalize(clipped)

        return normalized

    @staticmethod
    def scale_to_range(
        value: float,
        old_min: float,
        old_max: float,
        new_min: float = 0.0,
        new_max: float = 10.0
    ) -> float:
        """
        단일 값을 새로운 범위로 스케일링

        Args:
            value: 스케일링할 값
            old_min: 이전 범위 최소값
            old_max: 이전 범위 최대값
            new_min: 새로운 범위 최소값 (기본값: 0.0)
            new_max: 새로운 범위 최대값 (기본값: 10.0)

        Returns:
            스케일링된 값

        Example:
            >>> scaled = ScoreCalculator.scale_to_range(
            ...     value=75,
            ...     old_min=0,
            ...     old_max=100,
            ...     new_min=0,
            ...     new_max=10
            ... )
            >>> print(scaled)  # 7.5
        """
        # 범위가 0인 경우 처리
        if old_max == old_min:
            return (new_min + new_max) / 2.0

        # (value - old_min) / (old_max - old_min)
        normalized = (value - old_min) / (old_max - old_min)

        # × (new_max - new_min) + new_min
        scaled = normalized * (new_max - new_min) + new_min

        return float(scaled)

    @staticmethod
    def inverse_normalize(
        values: pd.Series
    ) -> pd.Series:
        """
        역정규화 (낮을수록 좋은 지표용, 예: 부채비율)

        Args:
            values: 정규화할 값들

        Returns:
            역정규화된 값들 (1 - normalized)

        Example:
            >>> debt_ratios = pd.Series([20, 40, 60, 80, 100])
            >>> scores = ScoreCalculator.inverse_normalize(debt_ratios)
            >>> # 부채비율이 낮을수록 점수가 높음
        """
        # Min-Max 정규화
        normalized = ScoreCalculator.min_max_normalize(values)

        # 1 - normalized (역전)
        inverse = 1 - normalized

        return inverse

    @staticmethod
    def robust_normalize(
        values: pd.Series
    ) -> pd.Series:
        """
        Robust 정규화 (중앙값과 IQR 사용, 이상치에 강함)

        공식: (x - median) / IQR

        Args:
            values: 정규화할 값들

        Returns:
            정규화된 값들

        Example:
            >>> values = pd.Series([1, 2, 3, 4, 5, 100])  # 100은 이상치
            >>> normalized = ScoreCalculator.robust_normalize(values)
        """
        # 중앙값(median) 계산
        median = values.median()

        # IQR = Q3 - Q1 계산
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1

        # IQR == 0인 경우 처리 (모든 값이 동일)
        if iqr == 0 or np.isnan(iqr):
            return pd.Series(0.0, index=values.index)

        # (values - median) / IQR
        robust = (values - median) / iqr

        return robust
