"""
normalization.py 단위 테스트

모든 정규화 함수에 대한 단위 테스트
"""

import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from app.utils.normalization import ScoreCalculator


@pytest.fixture
def sample_values():
    """테스트용 샘플 값들"""
    return pd.Series([10, 20, 30, 40, 50])


@pytest.fixture
def sample_df():
    """테스트용 샘플 데이터프레임"""
    return pd.DataFrame({
        'ticker': ['A001', 'A002', 'A003', 'A004', 'A005'],
        '거래량증가율': [10, 30, 50, 70, 90],
        '거래량': [100000, 200000, 300000, 400000, 500000]
    })


class TestScoreCalculator:
    """ScoreCalculator 테스트 클래스"""

    def test_min_max_normalize(self, sample_values):
        """Min-Max 정규화 테스트"""
        normalized = ScoreCalculator.min_max_normalize(sample_values)

        # 0-1 범위 검증
        assert all((normalized >= 0) & (normalized <= 1))

        # 최소값은 0, 최대값은 1
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0

        # 중간값은 0.5
        assert abs(normalized.iloc[2] - 0.5) < 0.01

    def test_min_max_normalize_custom_range(self, sample_values):
        """Min-Max 정규화 - 사용자 지정 범위"""
        normalized = ScoreCalculator.min_max_normalize(
            sample_values,
            new_min=5.0,
            new_max=10.0
        )

        # 5-10 범위 검증
        assert all((normalized >= 5.0) & (normalized <= 10.0))

        # 최소값은 5, 최대값은 10
        assert abs(normalized.min() - 5.0) < 0.01
        assert abs(normalized.max() - 10.0) < 0.01

    def test_min_max_normalize_identical_values(self):
        """Min-Max 정규화 - 모든 값이 동일한 경우"""
        identical = pd.Series([42, 42, 42, 42])
        normalized = ScoreCalculator.min_max_normalize(identical)

        # 모두 0.5 반환
        assert all(normalized == 0.5)

    def test_z_score_normalize(self, sample_values):
        """Z-Score 정규화 테스트"""
        z_scores = ScoreCalculator.z_score_normalize(sample_values)

        # 평균 ~0, 표준편차 ~1
        assert abs(z_scores.mean()) < 0.01
        assert abs(z_scores.std() - 1.0) < 0.01

    def test_z_score_normalize_identical_values(self):
        """Z-Score 정규화 - 모든 값이 동일한 경우"""
        identical = pd.Series([42, 42, 42, 42])
        z_scores = ScoreCalculator.z_score_normalize(identical)

        # 모두 0 반환
        assert all(z_scores == 0.0)

    def test_normalize_and_score(self, sample_df):
        """복합 점수 계산 테스트"""
        result = ScoreCalculator.normalize_and_score(
            sample_df,
            columns=['거래량증가율', '거래량'],
            weights=[0.6, 0.4],
            output_col='composite_score'
        )

        # composite_score 컬럼 생성 확인
        assert 'composite_score' in result.columns

        # 0-1 범위 검증
        assert all((result['composite_score'] >= 0) & (result['composite_score'] <= 1))

    def test_normalize_and_score_invalid_weights(self, sample_df):
        """복합 점수 계산 - 가중치 합이 1.0이 아닌 경우"""
        with pytest.raises(ValueError, match="Weights must sum to 1.0"):
            ScoreCalculator.normalize_and_score(
                sample_df,
                columns=['거래량증가율', '거래량'],
                weights=[0.5, 0.3]  # 합 = 0.8
            )

    def test_calculate_weighted_score(self):
        """가중 점수 계산 테스트"""
        score = ScoreCalculator.calculate_weighted_score(
            scores={'momentum': 8.0, 'volume': 9.0, 'sentiment': 7.0},
            weights={'momentum': 0.3, 'volume': 0.25, 'sentiment': 0.2}
        )

        # 8.0*0.3 + 9.0*0.25 + 7.0*0.2 = 2.4 + 2.25 + 1.4 = 6.05
        expected = 2.4 + 2.25 + 1.4
        assert abs(score - expected) < 0.01

    def test_calculate_weighted_score_missing_metric(self):
        """가중 점수 계산 - 누락된 지표"""
        score = ScoreCalculator.calculate_weighted_score(
            scores={'momentum': 8.0, 'volume': 9.0},  # sentiment 없음
            weights={'momentum': 0.3, 'volume': 0.25, 'sentiment': 0.2}
        )

        # sentiment가 없으므로 제외: 8.0*0.3 + 9.0*0.25 = 4.65
        expected = 2.4 + 2.25
        assert abs(score - expected) < 0.01

    def test_rank_normalize(self, sample_values):
        """순위 정규화 테스트"""
        ranked = ScoreCalculator.rank_normalize(sample_values, ascending=True)

        # 0-1 범위 검증
        assert all((ranked >= 0) & (ranked <= 1))

        # 최소값의 순위는 0
        assert ranked.iloc[0] == 0.0

        # 최대값의 순위는 1
        assert ranked.iloc[-1] == 1.0

    def test_rank_normalize_descending(self, sample_values):
        """순위 정규화 - 내림차순"""
        ranked = ScoreCalculator.rank_normalize(sample_values, ascending=False)

        # 0-1 범위 검증
        assert all((ranked >= 0) & (ranked <= 1))

        # 최소값의 순위는 1 (내림차순)
        assert ranked.iloc[0] == 1.0

        # 최대값의 순위는 0 (내림차순)
        assert ranked.iloc[-1] == 0.0

    def test_percentile_rank(self, sample_values):
        """백분위 순위 테스트"""
        # 35는 30과 40 사이 (상위 40%)
        percentile = ScoreCalculator.percentile_rank(sample_values, 35)

        # 값 10, 20, 30은 35보다 작거나 같음 → 60%
        assert abs(percentile - 60.0) < 1.0

        # 50 이상은 100%
        percentile_max = ScoreCalculator.percentile_rank(sample_values, 50)
        assert percentile_max == 100.0

        # 10 이하는 20%
        percentile_min = ScoreCalculator.percentile_rank(sample_values, 10)
        assert percentile_min == 20.0

    def test_sigmoid_normalize(self):
        """Sigmoid 정규화 테스트"""
        values = pd.Series([-2, -1, 0, 1, 2])
        sigmoid = ScoreCalculator.sigmoid_normalize(values, midpoint=0.0, steepness=1.0)

        # 0-1 범위 검증
        assert all((sigmoid >= 0) & (sigmoid <= 1))

        # midpoint(0)에서 0.5
        assert abs(sigmoid.iloc[2] - 0.5) < 0.01

        # 양수는 0.5 이상, 음수는 0.5 이하
        assert all(sigmoid.iloc[:2] < 0.5)
        assert all(sigmoid.iloc[3:] > 0.5)

    def test_log_normalize(self):
        """로그 정규화 테스트"""
        values = pd.Series([1, 10, 100, 1000])
        log_values = ScoreCalculator.log_normalize(values, base=10)

        # 로그 변환 검증
        assert abs(log_values.iloc[0] - 0.0) < 0.01  # log10(1) = 0
        assert abs(log_values.iloc[1] - 1.0) < 0.01  # log10(10) = 1
        assert abs(log_values.iloc[2] - 2.0) < 0.01  # log10(100) = 2
        assert abs(log_values.iloc[3] - 3.0) < 0.01  # log10(1000) = 3

    def test_log_normalize_zero_values(self):
        """로그 정규화 - 0 포함"""
        values = pd.Series([0, 1, 10, 100])
        log_values = ScoreCalculator.log_normalize(values)

        # 0은 작은 양수로 대체되어 음수 로그값
        assert log_values.iloc[0] < 0

        # ln(1) = 0이므로 1의 로그는 0
        assert abs(log_values.iloc[1]) < 0.01

        # 10, 100은 양수
        assert log_values.iloc[2] > 0
        assert log_values.iloc[3] > 0

    def test_clip_and_normalize(self):
        """이상치 제거 후 정규화 테스트"""
        values = pd.Series([1, 2, 3, 4, 5, 100])  # 100은 이상치

        normalized = ScoreCalculator.clip_and_normalize(
            values,
            lower_percentile=5.0,
            upper_percentile=95.0
        )

        # 0-1 범위 검증
        assert all((normalized >= 0) & (normalized <= 1))

        # 이상치(100)는 clipping되어 상한값으로 대체
        # 따라서 마지막 값도 1.0에 가까움
        assert normalized.iloc[-1] <= 1.0

    def test_scale_to_range(self):
        """범위 스케일링 테스트"""
        # 0-100 범위의 75를 0-10 범위로 변환
        scaled = ScoreCalculator.scale_to_range(
            value=75,
            old_min=0,
            old_max=100,
            new_min=0,
            new_max=10
        )

        # 75/100 = 0.75 → 7.5
        assert abs(scaled - 7.5) < 0.01

    def test_scale_to_range_identical_bounds(self):
        """범위 스케일링 - 동일한 최소/최대값"""
        scaled = ScoreCalculator.scale_to_range(
            value=50,
            old_min=50,
            old_max=50,
            new_min=0,
            new_max=10
        )

        # 중간값 반환
        assert abs(scaled - 5.0) < 0.01

    def test_inverse_normalize(self):
        """역정규화 테스트"""
        debt_ratios = pd.Series([20, 40, 60, 80, 100])
        scores = ScoreCalculator.inverse_normalize(debt_ratios)

        # 0-1 범위 검증
        assert all((scores >= 0) & (scores <= 1))

        # 낮은 부채비율이 높은 점수
        assert scores.iloc[0] > scores.iloc[-1]

        # 최소 부채비율(20)이 최대 점수(1.0)
        assert abs(scores.iloc[0] - 1.0) < 0.01

        # 최대 부채비율(100)이 최소 점수(0.0)
        assert abs(scores.iloc[-1] - 0.0) < 0.01

    def test_robust_normalize(self):
        """Robust 정규화 테스트"""
        values = pd.Series([1, 2, 3, 4, 5, 100])  # 100은 이상치

        robust = ScoreCalculator.robust_normalize(values)

        # 중앙값 근처는 0에 가까움
        median_idx = len(values) // 2
        assert abs(robust.iloc[median_idx]) < 1.0

        # 이상치(100)는 큰 값
        assert robust.iloc[-1] > robust.iloc[:-1].max()

    def test_robust_normalize_identical_values(self):
        """Robust 정규화 - 모든 값이 동일한 경우"""
        identical = pd.Series([42, 42, 42, 42])
        robust = ScoreCalculator.robust_normalize(identical)

        # 모두 0 반환 (IQR = 0)
        assert all(robust == 0.0)

    def test_edge_case_single_value(self):
        """단일 값 테스트"""
        single = pd.Series([42])

        # Min-Max 정규화
        normalized = ScoreCalculator.min_max_normalize(single)
        assert normalized.iloc[0] == 0.5

        # 순위 정규화
        ranked = ScoreCalculator.rank_normalize(single)
        assert ranked.iloc[0] == 0.5

    def test_edge_case_negative_values(self):
        """음수 값 테스트"""
        negative = pd.Series([-50, -30, -10, 10, 30, 50])

        # Min-Max 정규화는 음수도 처리 가능
        normalized = ScoreCalculator.min_max_normalize(negative)
        assert all((normalized >= 0) & (normalized <= 1))

        # Z-Score 정규화도 음수 처리 가능
        z_scores = ScoreCalculator.z_score_normalize(negative)
        assert abs(z_scores.mean()) < 0.01

    def test_normalization_preserves_order(self, sample_values):
        """정규화가 순서를 보존하는지 테스트"""
        normalized = ScoreCalculator.min_max_normalize(sample_values)

        # 원본 순서와 동일해야 함
        for i in range(len(sample_values) - 1):
            assert normalized.iloc[i] <= normalized.iloc[i + 1]
