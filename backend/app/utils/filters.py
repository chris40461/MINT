# 참고: docs/backend/03-filtering.md
# 참고: docs/backend/02-trigger-detection.md

"""
필터링 유틸리티

종목 필터링 조건 적용
"""

import pandas as pd
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class StockFilter:
    """종목 필터링 클래스"""

    @staticmethod
    def apply_absolute_filters(
        df: pd.DataFrame,
        min_trading_value: Optional[int] = None,
        min_market_cap: Optional[int] = None,
        min_volume_ratio: float = 0.2
    ) -> pd.DataFrame:
        """
        절대적 필터링 조건 적용

        조건:
        1. 최소 거래대금 (기본값: 5억원)
        2. 최소 시가총액 (기본값: 500억원, 동전주 제외)
        3. 시장 평균 거래량의 20% 이상

        Args:
            df: 데이터프레임 (columns: 거래대금, 시가총액, 거래량)
            min_trading_value: 최소 거래대금 (None이면 settings)
            min_market_cap: 최소 시가총액 (None이면 settings)
            min_volume_ratio: 시장 평균 거래량 대비 최소 비율

        Returns:
            필터링된 데이터프레임

        Example:
            >>> filtered = StockFilter.apply_absolute_filters(df)
            >>> print(len(filtered))  # 필터링 후 종목 수
        """
        if min_trading_value is None:
            min_trading_value = settings.MIN_TRADING_VALUE

        if min_market_cap is None:
            min_market_cap = settings.MIN_MARKET_CAP

        initial_count = len(df)

        # 거래대금 필터
        df = df[df['거래대금'] >= min_trading_value].copy()

        # 시가총액 필터 (동전주 제외)
        df = df[df['시가총액'] >= min_market_cap].copy()

        # 시장 평균 거래량의 min_volume_ratio 이상
        avg_volume = df['거래량'].mean()
        df = df[df['거래량'] >= avg_volume * min_volume_ratio].copy()

        filtered_count = len(df)
        logger.info(
            f"절대 필터링: {initial_count}개 → {filtered_count}개 "
            f"(거래대금>={min_trading_value:,}, 시총>={min_market_cap:,})"
        )

        return df

    @staticmethod
    def filter_uptrend_only(df: pd.DataFrame) -> pd.DataFrame:
        """
        상승 종목만 필터링 (종가 > 시가)

        Args:
            df: 데이터프레임 (columns: 종가, 시가)

        Returns:
            상승 종목만 포함된 데이터프레임

        Example:
            >>> uptrend = StockFilter.filter_uptrend_only(df)
        """
        initial_count = len(df)
        df = df[df['종가'] > df['시가']].copy()
        filtered_count = len(df)

        logger.debug(f"상승 종목 필터: {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_downtrend_only(df: pd.DataFrame) -> pd.DataFrame:
        """
        하락 종목만 필터링 (종가 < 시가)

        Args:
            df: 데이터프레임

        Returns:
            하락 종목만 포함된 데이터프레임
        """
        initial_count = len(df)
        df = df[df['종가'] < df['시가']].copy()
        filtered_count = len(df)

        logger.debug(f"하락 종목 필터: {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_sideways(
        df: pd.DataFrame,
        threshold: float = 5.0
    ) -> pd.DataFrame:
        """
        횡보 종목 필터링 (등락률 ±threshold% 이내)

        Args:
            df: 데이터프레임 (columns: 종가, 시가)
            threshold: 등락률 임계값 (기본값: 5%)

        Returns:
            횡보 종목만 포함된 데이터프레임

        Example:
            >>> sideways = StockFilter.filter_sideways(df, threshold=5.0)
        """
        initial_count = len(df)

        # 등락률 계산 = (종가 / 시가 - 1) × 100
        intraday_change = (df['종가'] / df['시가'] - 1) * 100

        # abs(등락률) <= threshold 조건
        df = df[intraday_change.abs() <= threshold].copy()
        filtered_count = len(df)

        logger.debug(f"횡보 종목 필터 (±{threshold}%): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_by_volume_increase(
        df: pd.DataFrame,
        current_col: str = '거래량',
        prev_col: str = '거래량_전일',
        min_increase_rate: float = 30.0
    ) -> pd.DataFrame:
        """
        거래량 증가율 필터링

        Args:
            df: 데이터프레임
            current_col: 현재 거래량 컬럼명
            prev_col: 전일 거래량 컬럼명
            min_increase_rate: 최소 증가율 (%, 기본값: 30%)

        Returns:
            필터링된 데이터프레임

        Example:
            >>> filtered = StockFilter.filter_by_volume_increase(df, min_increase_rate=30.0)
        """
        initial_count = len(df)

        # 거래량 증가율 계산 = (현재 / 전일 - 1) × 100
        volume_increase_rate = (df[current_col] / df[prev_col] - 1) * 100

        # min_increase_rate 이상 필터링
        df = df[volume_increase_rate >= min_increase_rate].copy()
        filtered_count = len(df)

        logger.debug(f"거래량 증가율 필터 (>={min_increase_rate}%): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_by_gap(
        df: pd.DataFrame,
        min_gap_ratio: float = 1.0
    ) -> pd.DataFrame:
        """
        갭 상승률 필터링

        Args:
            df: 데이터프레임 (columns: 시가, 전일종가)
            min_gap_ratio: 최소 갭 상승률 (%, 기본값: 1%)

        Returns:
            필터링된 데이터프레임

        Example:
            >>> filtered = StockFilter.filter_by_gap(df, min_gap_ratio=1.0)
        """
        initial_count = len(df)

        # 갭 상승률 계산 = (시가 / 전일종가 - 1) × 100
        # 전일종가가 없으면 컬럼명이 다를 수 있으므로 유연하게 처리
        if '전일종가' in df.columns:
            prev_close_col = '전일종가'
        elif '종가_prev' in df.columns:
            prev_close_col = '종가_prev'
        else:
            logger.warning("전일종가 컬럼을 찾을 수 없습니다. 빈 데이터프레임 반환")
            return pd.DataFrame()

        gap_ratio = (df['시가'] / df[prev_close_col] - 1) * 100

        # min_gap_ratio 이상 필터링
        df = df[gap_ratio >= min_gap_ratio].copy()
        filtered_count = len(df)

        logger.debug(f"갭 상승률 필터 (>={min_gap_ratio}%): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_by_intraday_rise(
        df: pd.DataFrame,
        min_rise_rate: float = 3.0
    ) -> pd.DataFrame:
        """
        일중 상승률 필터링

        Args:
            df: 데이터프레임 (columns: 종가, 시가)
            min_rise_rate: 최소 상승률 (%, 기본값: 3%)

        Returns:
            필터링된 데이터프레임

        Example:
            >>> filtered = StockFilter.filter_by_intraday_rise(df, min_rise_rate=3.0)
        """
        initial_count = len(df)

        # 일중 등락률 계산 = (종가 / 시가 - 1) × 100
        intraday_change = (df['종가'] / df['시가'] - 1) * 100

        # min_rise_rate 이상 필터링
        df = df[intraday_change >= min_rise_rate].copy()
        filtered_count = len(df)

        logger.debug(f"일중 상승률 필터 (>={min_rise_rate}%): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_by_market(
        df: pd.DataFrame,
        market: str
    ) -> pd.DataFrame:
        """
        시장별 필터링 (KOSPI/KOSDAQ)

        Args:
            df: 데이터프레임 (columns: market or 시장)
            market: 'KOSPI' or 'KOSDAQ'

        Returns:
            필터링된 데이터프레임

        Example:
            >>> kospi = StockFilter.filter_by_market(df, market='KOSPI')
        """
        initial_count = len(df)

        # market 컬럼명 유연하게 처리
        if 'market' in df.columns:
            market_col = 'market'
        elif '시장' in df.columns:
            market_col = '시장'
        else:
            logger.warning("시장 컬럼을 찾을 수 없습니다. 빈 데이터프레임 반환")
            return pd.DataFrame()

        # market 컬럼이 일치하는 종목만 필터링
        df = df[df[market_col] == market].copy()
        filtered_count = len(df)

        logger.debug(f"시장 필터 ({market}): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_by_sector(
        df: pd.DataFrame,
        sectors: list[str]
    ) -> pd.DataFrame:
        """
        업종별 필터링

        Args:
            df: 데이터프레임 (columns: sector or 업종)
            sectors: 업종 리스트

        Returns:
            필터링된 데이터프레임

        Example:
            >>> tech = StockFilter.filter_by_sector(df, sectors=['반도체', '전기전자'])
        """
        initial_count = len(df)

        # sector 컬럼명 유연하게 처리
        if 'sector' in df.columns:
            sector_col = 'sector'
        elif '업종' in df.columns:
            sector_col = '업종'
        else:
            logger.warning("업종 컬럼을 찾을 수 없습니다. 빈 데이터프레임 반환")
            return pd.DataFrame()

        # sector 컬럼이 sectors에 포함된 종목만 필터링
        df = df[df[sector_col].isin(sectors)].copy()
        filtered_count = len(df)

        logger.debug(f"업종 필터 ({len(sectors)}개 업종): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def filter_by_price_range(
        df: pd.DataFrame,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None
    ) -> pd.DataFrame:
        """
        가격대 필터링

        Args:
            df: 데이터프레임 (columns: 종가 or close)
            min_price: 최소 가격 (None이면 제한 없음)
            max_price: 최대 가격 (None이면 제한 없음)

        Returns:
            필터링된 데이터프레임

        Example:
            >>> mid_cap = StockFilter.filter_by_price_range(df, min_price=10000, max_price=100000)
        """
        initial_count = len(df)

        # 종가 컬럼명 유연하게 처리
        if '종가' in df.columns:
            price_col = '종가'
        elif 'close' in df.columns:
            price_col = 'close'
        else:
            logger.warning("가격 컬럼을 찾을 수 없습니다. 빈 데이터프레임 반환")
            return pd.DataFrame()

        # min_price 이상 필터링
        if min_price is not None:
            df = df[df[price_col] >= min_price].copy()

        # max_price 이하 필터링
        if max_price is not None:
            df = df[df[price_col] <= max_price].copy()

        filtered_count = len(df)
        logger.debug(f"가격대 필터 ({min_price}-{max_price}): {initial_count}개 → {filtered_count}개")
        return df

    @staticmethod
    def exclude_administrative_stocks(df: pd.DataFrame) -> pd.DataFrame:
        """
        관리종목 제외

        Args:
            df: 데이터프레임

        Returns:
            관리종목 제외된 데이터프레임

        Note:
            종목명에 '관리', '정리', '거래정지' 등의 키워드가 포함된 종목 제외
        """
        initial_count = len(df)

        # 종목명 컬럼 찾기
        if 'name' in df.columns:
            name_col = 'name'
        elif '종목명' in df.columns:
            name_col = '종목명'
        else:
            logger.warning("종목명 컬럼을 찾을 수 없습니다. 전체 데이터프레임 반환")
            return df

        # 키워드: '관리', '정리', '거래정지', '투자위험', '투자경고'
        admin_keywords = ['관리', '정리', '거래정지', '투자위험', '투자경고']

        # 키워드가 포함된 종목 제외
        mask = ~df[name_col].str.contains('|'.join(admin_keywords), na=False)
        df = df[mask].copy()

        filtered_count = len(df)
        excluded_count = initial_count - filtered_count
        logger.debug(f"관리종목 제외: {initial_count}개 → {filtered_count}개 (제외: {excluded_count}개)")
        return df

    @staticmethod
    def filter_top_n(
        df: pd.DataFrame,
        column: str,
        n: int,
        ascending: bool = False
    ) -> pd.DataFrame:
        """
        특정 컬럼 기준 상위 N개 선정

        Args:
            df: 데이터프레임
            column: 정렬 기준 컬럼
            n: 선정 개수
            ascending: 오름차순 여부 (기본값: False, 내림차순)

        Returns:
            상위 N개 데이터프레임

        Example:
            >>> top10 = StockFilter.filter_top_n(df, column='거래대금', n=10)
        """
        initial_count = len(df)

        # column 기준 정렬
        df_sorted = df.sort_values(by=column, ascending=ascending)

        # 상위 n개 반환
        df_top = df_sorted.head(n).copy()

        logger.debug(f"상위 {n}개 선정 ({column} 기준): {initial_count}개 → {len(df_top)}개")
        return df_top

    @staticmethod
    def combine_filters(
        df: pd.DataFrame,
        filters: list[callable]
    ) -> pd.DataFrame:
        """
        여러 필터 조합 적용

        Args:
            df: 데이터프레임
            filters: 필터 함수 리스트

        Returns:
            모든 필터 적용된 데이터프레임

        Example:
            >>> filtered = StockFilter.combine_filters(
            ...     df,
            ...     filters=[
            ...         lambda x: StockFilter.apply_absolute_filters(x),
            ...         lambda x: StockFilter.filter_uptrend_only(x)
            ...     ]
            ... )
        """
        initial_count = len(df)
        logger.info(f"필터 조합 시작: {initial_count}개 종목, {len(filters)}개 필터")

        # 각 필터를 순차적으로 적용
        for i, filter_func in enumerate(filters, 1):
            before_count = len(df)
            df = filter_func(df)
            after_count = len(df)

            # 각 단계별 필터링 결과 로깅
            logger.info(f"  필터 {i}/{len(filters)}: {before_count}개 → {after_count}개")

            # 빈 데이터프레임이면 조기 종료
            if df.empty:
                logger.warning("필터링 결과 종목이 없습니다. 조기 종료")
                break

        final_count = len(df)
        logger.info(f"필터 조합 완료: {initial_count}개 → {final_count}개 (제거: {initial_count - final_count}개)")
        return df
