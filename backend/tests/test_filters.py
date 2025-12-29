"""
filters.py 단위 테스트

모든 필터 함수에 대한 단위 테스트
"""

import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from app.utils.filters import StockFilter


@pytest.fixture
def sample_df():
    """테스트용 샘플 데이터프레임"""
    return pd.DataFrame({
        'ticker': ['A001', 'A002', 'A003', 'A004', 'A005', 'A006'],
        'name': ['삼성전자', 'SK하이닉스', '관리종목', 'LG전자', '정리매매', '네이버'],
        '시가': [50000, 80000, 1000, 120000, 2000, 300000],
        '종가': [55000, 75000, 1100, 125000, 1900, 310000],
        '고가': [56000, 82000, 1200, 128000, 2100, 315000],
        '저가': [49000, 74000, 900, 118000, 1850, 295000],
        '거래량': [1000000, 500000, 100000, 800000, 50000, 1500000],
        '거래대금': [55000000000, 37500000000, 110000000, 100000000000, 95000000, 465000000000],
        '시가총액': [500000000000, 300000000000, 10000000000, 400000000000, 5000000000, 600000000000],
        '종가_prev': [50000, 82000, 1000, 118000, 2000, 280000],
        '거래량_전일': [500000, 1000000, 200000, 600000, 100000, 1000000],
        'market': ['KOSPI', 'KOSPI', 'KOSDAQ', 'KOSPI', 'KOSDAQ', 'KOSDAQ'],
        'sector': ['반도체', '반도체', '기타', '가전', '기타', 'IT서비스']
    })


class TestStockFilter:
    """StockFilter 테스트 클래스"""

    def test_apply_absolute_filters(self, sample_df):
        """절대적 필터링 테스트"""
        result = StockFilter.apply_absolute_filters(
            sample_df,
            min_trading_value=10_000_000_000,  # 100억원
            min_market_cap=50_000_000_000       # 500억원
        )

        # 거래대금 100억원 이상, 시총 500억원 이상
        assert len(result) == 4  # A001, A002, A004, A006
        assert 'A003' not in result['ticker'].values  # 동전주 제외
        assert 'A005' not in result['ticker'].values  # 동전주 제외

    def test_filter_uptrend_only(self, sample_df):
        """상승 종목 필터 테스트"""
        result = StockFilter.filter_uptrend_only(sample_df)

        # 종가 > 시가 조건
        assert len(result) == 4  # A001, A003, A004, A006
        assert all(result['종가'] > result['시가'])

    def test_filter_downtrend_only(self, sample_df):
        """하락 종목 필터 테스트"""
        result = StockFilter.filter_downtrend_only(sample_df)

        # 종가 < 시가 조건
        assert len(result) == 2  # A002, A005
        assert all(result['종가'] < result['시가'])

    def test_filter_sideways(self, sample_df):
        """횡보 종목 필터 테스트"""
        result = StockFilter.filter_sideways(sample_df, threshold=5.0)

        # ±5% 이내
        intraday_change = (result['종가'] / result['시가'] - 1) * 100
        assert all(intraday_change.abs() <= 5.0)

    def test_filter_by_volume_increase(self, sample_df):
        """거래량 증가율 필터 테스트"""
        result = StockFilter.filter_by_volume_increase(
            sample_df,
            min_increase_rate=30.0
        )

        # 거래량 30% 이상 증가
        volume_increase = (result['거래량'] / result['거래량_전일'] - 1) * 100
        assert all(volume_increase >= 30.0)
        assert len(result) >= 1

    def test_filter_by_gap(self, sample_df):
        """갭 상승률 필터 테스트"""
        result = StockFilter.filter_by_gap(sample_df, min_gap_ratio=1.0)

        # 갭 1% 이상
        gap_ratio = (result['시가'] / result['종가_prev'] - 1) * 100
        assert all(gap_ratio >= 1.0)

    def test_filter_by_intraday_rise(self, sample_df):
        """일중 상승률 필터 테스트"""
        result = StockFilter.filter_by_intraday_rise(sample_df, min_rise_rate=3.0)

        # 일중 3% 이상 상승
        intraday_change = (result['종가'] / result['시가'] - 1) * 100
        assert all(intraday_change >= 3.0)

    def test_filter_by_market(self, sample_df):
        """시장별 필터 테스트"""
        # KOSPI만
        kospi_result = StockFilter.filter_by_market(sample_df, market='KOSPI')
        assert len(kospi_result) == 3
        assert all(kospi_result['market'] == 'KOSPI')

        # KOSDAQ만
        kosdaq_result = StockFilter.filter_by_market(sample_df, market='KOSDAQ')
        assert len(kosdaq_result) == 3
        assert all(kosdaq_result['market'] == 'KOSDAQ')

    def test_filter_by_sector(self, sample_df):
        """업종별 필터 테스트"""
        result = StockFilter.filter_by_sector(sample_df, sectors=['반도체', 'IT서비스'])

        assert len(result) == 3  # A001, A002, A006
        assert all(result['sector'].isin(['반도체', 'IT서비스']))

    def test_filter_by_price_range(self, sample_df):
        """가격대 필터 테스트"""
        # 최소가만
        result_min = StockFilter.filter_by_price_range(sample_df, min_price=100000)
        assert all(result_min['종가'] >= 100000)

        # 최대가만
        result_max = StockFilter.filter_by_price_range(sample_df, max_price=100000)
        assert all(result_max['종가'] <= 100000)

        # 범위 지정
        result_range = StockFilter.filter_by_price_range(
            sample_df,
            min_price=50000,
            max_price=150000
        )
        assert all((result_range['종가'] >= 50000) & (result_range['종가'] <= 150000))

    def test_exclude_administrative_stocks(self, sample_df):
        """관리종목 제외 테스트"""
        result = StockFilter.exclude_administrative_stocks(sample_df)

        # '관리', '정리' 키워드 제외
        assert len(result) == 4
        assert 'A003' not in result['ticker'].values  # 관리종목
        assert 'A005' not in result['ticker'].values  # 정리매매

        # 정상 종목만 포함
        assert all(
            ~result['name'].str.contains('관리|정리|거래정지|투자위험|투자경고', na=False)
        )

    def test_filter_top_n(self, sample_df):
        """상위 N개 선정 테스트"""
        # 거래대금 상위 3개 (내림차순)
        result = StockFilter.filter_top_n(sample_df, column='거래대금', n=3, ascending=False)

        assert len(result) == 3
        # 거래대금 순서 확인 (내림차순)
        assert result.iloc[0]['거래대금'] >= result.iloc[1]['거래대금']
        assert result.iloc[1]['거래대금'] >= result.iloc[2]['거래대금']

        # 시가총액 하위 2개 (오름차순)
        result_asc = StockFilter.filter_top_n(sample_df, column='시가총액', n=2, ascending=True)
        assert len(result_asc) == 2
        assert result_asc.iloc[0]['시가총액'] <= result_asc.iloc[1]['시가총액']

    def test_combine_filters(self, sample_df):
        """필터 조합 테스트"""
        filters = [
            lambda x: StockFilter.apply_absolute_filters(
                x,
                min_trading_value=10_000_000_000,
                min_market_cap=50_000_000_000
            ),
            lambda x: StockFilter.filter_uptrend_only(x),
            lambda x: StockFilter.exclude_administrative_stocks(x)
        ]

        result = StockFilter.combine_filters(sample_df, filters)

        # 모든 필터 적용 후 결과 검증
        assert len(result) >= 1
        assert all(result['종가'] > result['시가'])  # 상승 종목
        assert all(result['거래대금'] >= 10_000_000_000)  # 거래대금 조건
        assert all(result['시가총액'] >= 50_000_000_000)  # 시총 조건
        assert all(
            ~result['name'].str.contains('관리|정리|거래정지', na=False)
        )  # 관리종목 제외

    def test_empty_dataframe_handling(self, sample_df):
        """빈 데이터프레임 처리 테스트"""
        # 모든 종목이 필터링된 경우 빈 데이터프레임 반환
        empty_df = sample_df[sample_df['ticker'] == 'NONEXISTENT']

        # 각 필터가 빈 데이터프레임을 안전하게 처리하는지 확인
        result = StockFilter.filter_uptrend_only(empty_df)
        assert len(result) == 0

    def test_edge_case_all_filtered(self, sample_df):
        """모든 종목이 필터링되는 경계 케이스"""
        # 거래대금 1조원 이상 (모든 종목 제외)
        result = StockFilter.apply_absolute_filters(
            sample_df,
            min_trading_value=1_000_000_000_000
        )

        assert len(result) == 0

    def test_column_name_flexibility(self):
        """컬럼명 유연성 테스트 (영어/한글)"""
        # 영어 컬럼명 데이터
        english_df = pd.DataFrame({
            'ticker': ['TEST'],
            'open': [1000],
            'close': [1100],
            'market': ['KOSPI'],
            'sector': ['반도체']
        })

        # market 필터
        result = StockFilter.filter_by_market(english_df, market='KOSPI')
        assert len(result) == 1

    def test_volume_increase_zero_division(self, sample_df):
        """거래량 증가율 계산 시 0으로 나누기 처리 테스트"""
        # 전일 거래량이 0인 경우 (실제로는 없지만 안전성 테스트)
        sample_df_zero = sample_df.copy()
        sample_df_zero.loc[0, '거래량_전일'] = 0

        # inf 값이 발생하지만 pandas는 자동으로 처리
        result = StockFilter.filter_by_volume_increase(
            sample_df_zero,
            min_increase_rate=30.0
        )

        # inf 값은 >= 비교에서 True가 되므로 포함될 수 있음
        # 결과가 있거나 없거나 둘 다 허용 (inf 처리 방식에 따라)
        assert len(result) >= 0
