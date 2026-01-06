# 참고: docs/backend/02-trigger-detection.md
# 참고: docs/backend/03-filtering.md
# 참고: docs/backend/04-scoring.md

"""
급등주 트리거 감지 서비스

6개 트리거 타입(오전 3개, 오후 3개)을 사용하여 급등주를 감지합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import logging
import asyncio

from app.models import Trigger, TriggerType, SessionType
from app.services.data_service import DataService
from app.core.config import settings
from app.utils.filters import StockFilter
from app.utils.metrics import MetricsCalculator
from app.utils.normalization import ScoreCalculator

logger = logging.getLogger(__name__)


class TriggerService:
    """급등주 트리거 감지 서비스"""

    def __init__(self, data_service: DataService):
        """
        서비스 초기화

        Args:
            data_service: 데이터 수집 서비스
        """
        self.data_service = data_service
        self.filter = StockFilter()
        self.metrics = MetricsCalculator()
        self.scorer = ScoreCalculator()

    async def _get_current_market_data(self, date: datetime) -> pd.DataFrame:
        """
        현재 날짜의 시장 데이터 조회 (realtime_prices 우선, pykrx 폴백)

        Args:
            date: 조회 날짜 (사용 안 함, 호환성 유지용)

        Returns:
            DataFrame with columns: ticker, 시가, 고가, 저가, 종가, 거래량, 거래대금, 시가총액, 등락률
        """
        from app.db.database import get_db
        from app.db.models import FinancialData

        # 1. 필터 통과 종목 조회 (시가총액 포함)
        with get_db() as db:
            financial_data = {
                row.ticker: row.market_cap * 100_000_000  # 억원 → 원
                for row in db.query(FinancialData).filter_by(filter_status='pass').all()
            }
        tickers = list(financial_data.keys())

        if not tickers:
            logger.warning("필터 통과 종목 없음")
            return pd.DataFrame()

        # 2. 실시간 가격 배치 조회
        realtime_prices = await self.data_service.get_realtime_prices_bulk(tickers)

        if not realtime_prices:
            # 폴백: pykrx 사용
            logger.warning("realtime_prices 데이터 없음, pykrx 폴백")
            return await self.data_service.get_market_snapshot(date)

        # 3. DataFrame 변환 (시가총액은 financial_data에서 조회)
        rows = []
        for ticker, price_data in realtime_prices.items():
            rows.append({
                'ticker': ticker,
                '시가': price_data.get('open_price', 0),
                '고가': price_data.get('high_price', 0),
                '저가': price_data.get('low_price', 0),
                '종가': price_data.get('current_price', 0),  # current_price → 종가
                '거래량': price_data.get('volume', 0),
                '거래대금': price_data.get('trading_value', 0),
                '시가총액': financial_data.get(ticker, 0),  # financial_data에서 조회
                '등락률': price_data.get('change_rate', 0.0)
            })

        df = pd.DataFrame(rows)
        logger.info(f"현재 시장 데이터 조회 완료: {len(df)}개 종목 (realtime_prices)")
        return df

    # ============= 오전 트리거 (09:10) =============

    async def morning_volume_surge(
        self,
        current_date: datetime,
        top_n: int = 3
    ) -> List[Dict]:
        """
        오전 트리거 1: 거래량 급증

        조건:
        - 전일 대비 거래량 30% 이상 증가
        - 거래대금 5억원 이상
        - 시가총액 500억원 이상
        - 시가 대비 현재가 상승

        Args:
            current_date: 현재 날짜
            top_n: 상위 N개 종목 (기본값: 3)

        Returns:
            List of trigger results:
            [
                {
                    'ticker': str,
                    'name': str,
                    'current_price': int,
                    'change_rate': float,
                    'volume': int,
                    'trading_value': int,
                    'volume_increase_rate': float,
                    'composite_score': float
                }
            ]

        Example:
            >>> results = await service.morning_volume_surge(
            ...     datetime(2025, 11, 6),
            ...     top_n=3
            ... )
        """
        logger.info(f"오전 트리거 1 시작: 거래량 급증 ({current_date.strftime('%Y-%m-%d')})")

        # Step 1: 현재/전일 시장 데이터 조회
        current = await self._get_current_market_data(current_date)
        prev_date = await self.data_service.get_previous_trading_day(current_date)
        prev = await self.data_service.get_market_snapshot(prev_date)

        # ticker를 인덱스로 설정
        current = current.set_index('ticker')
        prev = prev.set_index('ticker')

        # Step 2: 거래량 증가율 계산
        current['거래량증가율'] = self.metrics.calculate_volume_change(current, prev)

        # Step 3: 상승 종목만 필터링 (절대 조건은 financial_data에서 이미 적용됨)
        filtered = self.filter.filter_uptrend_only(current)

        # Step 5: 3차 필터링 - 거래량 증가율 30% 이상
        filtered = filtered[filtered['거래량증가율'] >= 30].copy()

        if len(filtered) == 0:
            logger.warning("거래량 급증 필터링 후 종목 없음")
            return []

        # Step 6: 복합 점수 계산 (거래량증가율 60% + 거래량 40%)
        filtered = self.scorer.normalize_and_score(
            filtered,
            columns=['거래량증가율', '거래량'],
            weights=[0.6, 0.4],
            output_col='composite_score'
        )

        # Step 7: 상위 N개 선정
        top_stocks = filtered.nlargest(top_n, 'composite_score')

        # Step 8: 결과 변환
        results = []
        for ticker, row in top_stocks.iterrows():
            # 종목명 조회
            stock_info = await self.data_service.get_stock_info(ticker)

            results.append({
                'ticker': ticker,
                'name': stock_info['name'],
                'current_price': int(row['종가']),
                'change_rate': float(row['등락률']),
                'volume': int(row['거래량']),
                'trading_value': int(row['거래대금']),
                'market_cap': int(row['시가총액']),
                'volume_increase_rate': float(row['거래량증가율']),
                'composite_score': float(row['composite_score'])
            })

        logger.info(f"거래량 급증 감지 완료: {len(results)}개 종목")
        return results

    async def morning_gap_up(
        self,
        current_date: datetime,
        top_n: int = 3
    ) -> List[Dict]:
        """
        오전 트리거 2: 갭 상승 모멘텀

        조건:
        - 갭 상승률 1% 이상
        - 거래대금 5억원 이상
        - 시가총액 500억원 이상
        - 시가 대비 현재가 상승

        Args:
            current_date: 현재 날짜
            top_n: 상위 N개 종목

        Returns:
            List of trigger results with gap_ratio, intraday_change

        Example:
            >>> results = await service.morning_gap_up(
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"오전 트리거 2 시작: 갭 상승 모멘텀 ({current_date.strftime('%Y-%m-%d')})")

        # 데이터 수집
        current = await self._get_current_market_data(current_date)
        prev_date = await self.data_service.get_previous_trading_day(current_date)
        prev = await self.data_service.get_market_snapshot(prev_date)

        current = current.set_index('ticker')
        prev = prev.set_index('ticker')

        # 지표 계산
        current['갭상승률'] = self.metrics.calculate_gap_ratio(current, prev)
        current['장중등락률'] = self.metrics.calculate_intraday_change(current)

        # 필터링 (절대 조건은 financial_data에서 이미 적용됨)
        filtered = self.filter.filter_uptrend_only(current)
        filtered = filtered[filtered['갭상승률'] >= 1.0].copy()

        if len(filtered) == 0:
            logger.warning("갭 상승 필터링 후 종목 없음")
            return []

        # 복합 점수 (갭상승률 50% + 장중등락률 30% + 거래대금 20%)
        filtered = self.scorer.normalize_and_score(
            filtered,
            columns=['갭상승률', '장중등락률', '거래대금'],
            weights=[0.5, 0.3, 0.2],
            output_col='composite_score'
        )

        # Top N 선정
        top_stocks = filtered.nlargest(top_n, 'composite_score')

        # 결과 변환
        results = []
        for ticker, row in top_stocks.iterrows():
            stock_info = await self.data_service.get_stock_info(ticker)
            results.append({
                'ticker': ticker,
                'name': stock_info['name'],
                'current_price': int(row['종가']),
                'change_rate': float(row['등락률']),
                'volume': int(row['거래량']),
                'trading_value': int(row['거래대금']),
                'market_cap': int(row['시가총액']),
                'gap_ratio': float(row['갭상승률']),
                'intraday_change': float(row['장중등락률']),
                'composite_score': float(row['composite_score'])
            })

        logger.info(f"갭 상승 감지 완료: {len(results)}개 종목")
        return results

    async def morning_fund_inflow(
        self,
        current_date: datetime,
        top_n: int = 3
    ) -> List[Dict]:
        """
        오전 트리거 3: 시총 대비 자금유입

        조건:
        - 거래대금/시가총액 비율 높은 종목
        - 거래대금 5억원 이상
        - 시가총액 500억원 이상
        - 시가 대비 현재가 상승

        Args:
            current_date: 현재 날짜
            top_n: 상위 N개 종목

        Returns:
            List of trigger results with fund_inflow_ratio

        Example:
            >>> results = await service.morning_fund_inflow(
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"오전 트리거 3 시작: 자금유입 ({current_date.strftime('%Y-%m-%d')})")

        # 데이터 수집
        current = await self._get_current_market_data(current_date)
        current = current.set_index('ticker')

        # 지표 계산 (시가총액은 _get_current_market_data에서 이미 financial_data 기준으로 조회됨)
        current['자금유입비율'] = (current['거래대금'] / current['시가총액'].replace(0, float('inf'))) * 100
        current['장중등락률'] = self.metrics.calculate_intraday_change(current)

        # 필터링 (절대 조건은 financial_data에서 이미 적용됨)
        filtered = self.filter.filter_uptrend_only(current)

        if len(filtered) == 0:
            logger.warning("자금유입 필터링 후 종목 없음")
            return []

        # 복합 점수 (자금유입비율 50% + 거래대금 30% + 장중등락률 20%)
        filtered = self.scorer.normalize_and_score(
            filtered,
            columns=['자금유입비율', '거래대금', '장중등락률'],
            weights=[0.5, 0.3, 0.2],
            output_col='composite_score'
        )

        # Top N 선정
        top_stocks = filtered.nlargest(top_n, 'composite_score')

        # 결과 변환
        results = []
        for ticker, row in top_stocks.iterrows():
            stock_info = await self.data_service.get_stock_info(ticker)
            results.append({
                'ticker': ticker,
                'name': stock_info['name'],
                'current_price': int(row['종가']),
                'change_rate': float(row['등락률']),
                'volume': int(row['거래량']),
                'trading_value': int(row['거래대금']),
                'market_cap': int(row['시가총액']),
                'fund_inflow_ratio': float(row['자금유입비율']),
                'intraday_change': float(row['장중등락률']),
                'composite_score': float(row['composite_score'])
            })

        logger.info(f"자금유입 감지 완료: {len(results)}개 종목")
        return results

    # ============= 오후 트리거 (15:30) =============

    async def afternoon_intraday_rise(
        self,
        current_date: datetime,
        top_n: int = 3
    ) -> List[Dict]:
        """
        오후 트리거 1: 일중 상승률

        조건:
        - 시가 대비 3% 이상 상승
        - 거래대금 10억원 이상
        - 시가총액 500억원 이상

        Args:
            current_date: 현재 날짜
            top_n: 상위 N개 종목

        Returns:
            List of trigger results with intraday_rise_rate

        Example:
            >>> results = await service.afternoon_intraday_rise(
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"오후 트리거 1 시작: 일중 상승률 ({current_date.strftime('%Y-%m-%d')})")

        # 데이터 수집 (장 마감 후)
        current = await self._get_current_market_data(current_date)
        current = current.set_index('ticker')

        # 지표 계산
        current['장중등락률'] = self.metrics.calculate_intraday_change(current)

        # 필터링 (절대 조건은 financial_data에서 이미 적용됨)
        filtered = current[current['장중등락률'] >= 3.0].copy()

        if len(filtered) == 0:
            logger.warning("일중 상승률 필터링 후 종목 없음")
            return []

        # 복합 점수 (장중등락률 60% + 거래대금 40%)
        filtered = self.scorer.normalize_and_score(
            filtered,
            columns=['장중등락률', '거래대금'],
            weights=[0.6, 0.4],
            output_col='composite_score'
        )

        # Top N 선정
        top_stocks = filtered.nlargest(top_n, 'composite_score')

        # 결과 변환
        results = []
        for ticker, row in top_stocks.iterrows():
            stock_info = await self.data_service.get_stock_info(ticker)
            results.append({
                'ticker': ticker,
                'name': stock_info['name'],
                'current_price': int(row['종가']),
                'change_rate': float(row['등락률']),
                'volume': int(row['거래량']),
                'trading_value': int(row['거래대금']),
                'market_cap': int(row['시가총액']),
                'intraday_change': float(row['장중등락률']),
                'composite_score': float(row['composite_score'])
            })

        logger.info(f"일중 상승률 감지 완료: {len(results)}개 종목")
        return results

    async def afternoon_closing_strength(
        self,
        current_date: datetime,
        top_n: int = 3
    ) -> List[Dict]:
        """
        오후 트리거 2: 마감 강도

        조건:
        - (종가-저가)/(고가-저가) 비율 높음 (1에 가까울수록 강세)
        - 거래대금 5억원 이상
        - 시가총액 500억원 이상
        - 전일 대비 거래량 증가

        Args:
            current_date: 현재 날짜
            top_n: 상위 N개 종목

        Returns:
            List of trigger results with closing_strength

        Example:
            >>> results = await service.afternoon_closing_strength(
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"오후 트리거 2 시작: 마감 강도 ({current_date.strftime('%Y-%m-%d')})")

        # 데이터 수집
        current = await self._get_current_market_data(current_date)
        prev_date = await self.data_service.get_previous_trading_day(current_date)
        prev = await self.data_service.get_market_snapshot(prev_date)

        current = current.set_index('ticker')
        prev = prev.set_index('ticker')

        # 지표 계산
        current['마감강도'] = self.metrics.calculate_closing_strength(current)
        current['거래량증가율'] = self.metrics.calculate_volume_change(current, prev)

        # 필터링 (절대 조건은 financial_data에서 이미 적용됨)
        # 거래량 증가 & 상승 종목만
        filtered = current[current['거래량증가율'] > 0].copy()
        filtered = filtered[filtered['종가'] > filtered['시가']].copy()

        if len(filtered) == 0:
            logger.warning("마감 강도 필터링 후 종목 없음")
            return []

        # 복합 점수 (마감강도 50% + 거래량증가율 30% + 거래대금 20%)
        filtered = self.scorer.normalize_and_score(
            filtered,
            columns=['마감강도', '거래량증가율', '거래대금'],
            weights=[0.5, 0.3, 0.2],
            output_col='composite_score'
        )

        # Top N 선정
        top_stocks = filtered.nlargest(top_n, 'composite_score')

        # 결과 변환
        results = []
        for ticker, row in top_stocks.iterrows():
            stock_info = await self.data_service.get_stock_info(ticker)
            results.append({
                'ticker': ticker,
                'name': stock_info['name'],
                'current_price': int(row['종가']),
                'change_rate': float(row['등락률']),
                'volume': int(row['거래량']),
                'trading_value': int(row['거래대금']),
                'market_cap': int(row['시가총액']),
                'closing_strength': float(row['마감강도']),
                'volume_increase_rate': float(row['거래량증가율']),
                'composite_score': float(row['composite_score'])
            })

        logger.info(f"마감 강도 감지 완료: {len(results)}개 종목")
        return results

    async def afternoon_sideways_volume(
        self,
        current_date: datetime,
        top_n: int = 3
    ) -> List[Dict]:
        """
        오후 트리거 3: 횡보주 거래량

        조건:
        - 전일 대비 거래량 50% 이상 증가
        - 등락률 ±5% 이내 (횡보)
        - 거래대금 5억원 이상
        - 시가총액 500억원 이상

        Args:
            current_date: 현재 날짜
            top_n: 상위 N개 종목

        Returns:
            List of trigger results with volume_increase_rate

        Example:
            >>> results = await service.afternoon_sideways_volume(
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"오후 트리거 3 시작: 횡보주 거래량 ({current_date.strftime('%Y-%m-%d')})")

        # 데이터 수집
        current = await self._get_current_market_data(current_date)
        prev_date = await self.data_service.get_previous_trading_day(current_date)
        prev = await self.data_service.get_market_snapshot(prev_date)

        current = current.set_index('ticker')
        prev = prev.set_index('ticker')

        # 지표 계산
        current['장중등락률'] = self.metrics.calculate_intraday_change(current)
        current['거래량증가율'] = self.metrics.calculate_volume_change(current, prev)

        # 필터링 (절대 조건은 financial_data에서 이미 적용됨)
        # 횡보 조건: -5% ~ +5%
        filtered = current[
            (current['장중등락률'] >= -5) &
            (current['장중등락률'] <= 5)
        ].copy()

        # 거래량 급증 조건: 50% 이상
        filtered = filtered[filtered['거래량증가율'] >= 50].copy()

        if len(filtered) == 0:
            logger.warning("횡보주 거래량 필터링 후 종목 없음")
            return []

        # 복합 점수 (거래량증가율 60% + 거래대금 40%)
        filtered = self.scorer.normalize_and_score(
            filtered,
            columns=['거래량증가율', '거래대금'],
            weights=[0.6, 0.4],
            output_col='composite_score'
        )

        # Top N 선정
        top_stocks = filtered.nlargest(top_n, 'composite_score')

        # 결과 변환
        results = []
        for ticker, row in top_stocks.iterrows():
            stock_info = await self.data_service.get_stock_info(ticker)
            results.append({
                'ticker': ticker,
                'name': stock_info['name'],
                'current_price': int(row['종가']),
                'change_rate': float(row['등락률']),
                'volume': int(row['거래량']),
                'trading_value': int(row['거래대금']),
                'market_cap': int(row['시가총액']),
                'intraday_change': float(row['장중등락률']),
                'volume_increase_rate': float(row['거래량증가율']),
                'composite_score': float(row['composite_score'])
            })

        logger.info(f"횡보주 거래량 감지 완료: {len(results)}개 종목")
        return results

    # ============= 통합 실행 =============

    async def run_morning_triggers(
        self,
        date: datetime
    ) -> Dict[TriggerType, List[Trigger]]:
        """
        오전 트리거 전체 실행 (09:10)

        3개 트리거 각각 Top 3 종목 감지 (총 최대 9개)

        Args:
            date: 실행 날짜

        Returns:
            {
                'volume_surge': [Trigger, ...],
                'gap_up': [Trigger, ...],
                'fund_inflow': [Trigger, ...]
            }

        Example:
            >>> results = await service.run_morning_triggers(
            ...     datetime(2025, 11, 6)
            ... )
            >>> print(len(results['volume_surge']))  # 3
        """
        logger.info(f"오전 트리거 실행 시작: {date.strftime('%Y-%m-%d')}")

        # Step 1: 3개 트리거 병렬 실행
        volume_surge_results, gap_up_results, fund_inflow_results = await asyncio.gather(
            self.morning_volume_surge(date, top_n=3),
            self.morning_gap_up(date, top_n=3),
            self.morning_fund_inflow(date, top_n=3)
        )

        # Step 2: 결과를 Trigger 모델로 변환
        results = {
            'volume_surge': [
                Trigger(
                    ticker=item['ticker'],
                    name=item['name'],
                    trigger_type='volume_surge',
                    current_price=item['current_price'],
                    change_rate=item['change_rate'],
                    volume=item['volume'],
                    trading_value=item['trading_value'],
                    composite_score=item['composite_score'],
                    session='morning',
                    detected_at=date
                )
                for item in volume_surge_results
            ],
            'gap_up': [
                Trigger(
                    ticker=item['ticker'],
                    name=item['name'],
                    trigger_type='gap_up',
                    current_price=item['current_price'],
                    change_rate=item['change_rate'],
                    volume=item['volume'],
                    trading_value=item['trading_value'],
                    composite_score=item['composite_score'],
                    session='morning',
                    detected_at=date
                )
                for item in gap_up_results
            ],
            'fund_inflow': [
                Trigger(
                    ticker=item['ticker'],
                    name=item['name'],
                    trigger_type='fund_inflow',
                    current_price=item['current_price'],
                    change_rate=item['change_rate'],
                    volume=item['volume'],
                    trading_value=item['trading_value'],
                    composite_score=item['composite_score'],
                    session='morning',
                    detected_at=date
                )
                for item in fund_inflow_results
            ]
        }

        total_count = sum(len(triggers) for triggers in results.values())
        logger.info(f"오전 트리거 실행 완료: 총 {total_count}개 종목 감지")
        logger.info(f"  - 거래량 급증: {len(results['volume_surge'])}개")
        logger.info(f"  - 갭 상승: {len(results['gap_up'])}개")
        logger.info(f"  - 자금 유입: {len(results['fund_inflow'])}개")

        # Step 3: 데이터베이스에 저장
        self._save_triggers_to_db(results, date, session='morning')

        return results

    async def run_afternoon_triggers(
        self,
        date: datetime
    ) -> Dict[TriggerType, List[Trigger]]:
        """
        오후 트리거 전체 실행 (15:30)

        3개 트리거 각각 Top 3 종목 감지 (총 최대 9개)

        Args:
            date: 실행 날짜

        Returns:
            {
                'intraday_rise': [Trigger, ...],
                'closing_strength': [Trigger, ...],
                'sideways_volume': [Trigger, ...]
            }

        Example:
            >>> results = await service.run_afternoon_triggers(
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"오후 트리거 실행 시작: {date.strftime('%Y-%m-%d')}")

        # Step 1: 3개 트리거 병렬 실행
        intraday_rise_results, closing_strength_results, sideways_volume_results = await asyncio.gather(
            self.afternoon_intraday_rise(date, top_n=3),
            self.afternoon_closing_strength(date, top_n=3),
            self.afternoon_sideways_volume(date, top_n=3)
        )

        # Step 2: 결과를 Trigger 모델로 변환
        results = {
            'intraday_rise': [
                Trigger(
                    ticker=item['ticker'],
                    name=item['name'],
                    trigger_type='intraday_rise',
                    current_price=item['current_price'],
                    change_rate=item['change_rate'],
                    volume=item['volume'],
                    trading_value=item['trading_value'],
                    composite_score=item['composite_score'],
                    session='afternoon',
                    detected_at=date
                )
                for item in intraday_rise_results
            ],
            'closing_strength': [
                Trigger(
                    ticker=item['ticker'],
                    name=item['name'],
                    trigger_type='closing_strength',
                    current_price=item['current_price'],
                    change_rate=item['change_rate'],
                    volume=item['volume'],
                    trading_value=item['trading_value'],
                    composite_score=item['composite_score'],
                    session='afternoon',
                    detected_at=date
                )
                for item in closing_strength_results
            ],
            'sideways_volume': [
                Trigger(
                    ticker=item['ticker'],
                    name=item['name'],
                    trigger_type='sideways_volume',
                    current_price=item['current_price'],
                    change_rate=item['change_rate'],
                    volume=item['volume'],
                    trading_value=item['trading_value'],
                    composite_score=item['composite_score'],
                    session='afternoon',
                    detected_at=date
                )
                for item in sideways_volume_results
            ]
        }

        total_count = sum(len(triggers) for triggers in results.values())
        logger.info(f"오후 트리거 실행 완료: 총 {total_count}개 종목 감지")
        logger.info(f"  - 일중 상승: {len(results['intraday_rise'])}개")
        logger.info(f"  - 마감 강도: {len(results['closing_strength'])}개")
        logger.info(f"  - 횡보 거래량: {len(results['sideways_volume'])}개")

        # Step 3: 데이터베이스에 저장
        self._save_triggers_to_db(results, date, session='afternoon')

        return results

    def _save_triggers_to_db(self, results: Dict[TriggerType, List[Trigger]], date: datetime, session: str):
        """
        트리거 결과를 데이터베이스에 저장

        Args:
            results: 트리거 결과 딕셔너리
            date: 실행 날짜
            session: 세션 (morning/afternoon)
        """
        from app.db.database import get_db
        from app.db.models import TriggerResult

        date_str = date.strftime('%Y-%m-%d')

        with get_db() as db:
            # 해당 날짜의 기존 데이터 삭제 (중복 방지)
            db.query(TriggerResult).filter(
                TriggerResult.date == date_str,
                TriggerResult.session == session
            ).delete()

            # 새 데이터 저장
            saved_count = 0
            for trigger_type, triggers in results.items():
                for trigger in triggers:
                    db_trigger = TriggerResult(
                        ticker=trigger.ticker,
                        name=trigger.name,
                        trigger_type=trigger.trigger_type,
                        session=trigger.session,
                        current_price=trigger.current_price,
                        change_rate=trigger.change_rate,
                        volume=trigger.volume,
                        trading_value=trigger.trading_value,
                        composite_score=trigger.composite_score,
                        date=date_str,
                        detected_at=trigger.detected_at
                    )
                    db.add(db_trigger)
                    saved_count += 1

            logger.info(f"✅ 트리거 결과 DB 저장 완료: {date_str} ({session}), {saved_count}개 종목")


class PreSurgeDetector:
    """
    급등 전조(조짐) 감지기 - 거래량 선행, 가격 후행 원리

    학술 근거:
    - 거래량은 주가에 선행 (Volume precedes price)
    - 세력 매집 시 거래량 먼저 급증, 가격은 아직 크게 안 오름
    - 조짐 감지 후 급등 확률 높음

    감지 조건:
    1. 거래량: 5일 평균 대비 N배 이상 급증
    2. 가격: 아직 크게 안 오름 (±3% 이내)
    → 이 조합 = 매집(Accumulation) 신호
    """

    def __init__(
        self,
        volume_threshold: float = 3.0,
        price_threshold: float = 3.0
    ):
        """
        Args:
            volume_threshold: 5일 평균 대비 거래량 배수 (기본 3.0 = 3배)
            price_threshold: 가격 변동 상한 (기본 ±3%)
        """
        self.volume_threshold = volume_threshold
        self.price_threshold = price_threshold
        self.data_service = DataService()

    def detect_accumulation_signal(
        self,
        ticker: str,
        name: str,
        current_volume: int,
        avg_volume_5d: int,
        change_rate: float,
        current_price: int = 0
    ) -> Dict | None:
        """
        단일 종목 매집(Accumulation) 신호 감지

        조건:
        - 거래량: 5일 평균 대비 N배 이상 급증
        - 가격: 아직 크게 안 오름 (±3% 이내)
        → 세력 매집 가능성 → 곧 상승 전조

        Args:
            ticker: 종목코드
            name: 종목명
            current_volume: 현재 거래량
            avg_volume_5d: 5일 평균 거래량
            change_rate: 등락률 (%)
            current_price: 현재가 (optional)

        Returns:
            감지 시: {"ticker": ..., "volume_ratio": ..., "signal": "accumulation"}
            미감지 시: None
        """
        if avg_volume_5d <= 0:
            return None

        volume_ratio = current_volume / avg_volume_5d

        # 조짐 조건: 거래량 급증 + 가격 미동
        if volume_ratio >= self.volume_threshold and abs(change_rate) <= self.price_threshold:
            return {
                "ticker": ticker,
                "name": name,
                "volume_ratio": round(volume_ratio, 2),
                "change_rate": round(change_rate, 2),
                "current_price": current_price,
                "signal": "accumulation",  # 매집 신호
                "confidence": min(volume_ratio / 5.0, 1.0),  # 신뢰도 (5배일 때 100%)
                "detected_at": datetime.now().isoformat()
            }

        return None

    async def scan_all_stocks(self) -> List[Dict]:
        """
        전체 종목 스캔하여 조짐 감지

        Returns:
            감지된 종목 리스트
        """
        from app.db.database import get_db
        from app.db.models import FinancialData

        logger.info("PreSurgeDetector: 전체 종목 스캔 시작")

        # 1. 필터 통과 종목 조회
        with get_db() as db:
            tickers = [
                row.ticker
                for row in db.query(FinancialData).filter_by(filter_status='pass').all()
            ]

        if not tickers:
            logger.warning("필터 통과 종목 없음")
            return []

        # 2. 실시간 가격 조회
        realtime_prices = await self.data_service.get_realtime_prices_bulk(tickers)

        if not realtime_prices:
            logger.warning("realtime_prices 데이터 없음")
            return []

        # 3. 5일 평균 거래량 조회 (배치)
        avg_volumes = await self._get_avg_volumes_5d_batch(tickers)

        # 4. 각 종목별 조짐 감지
        detected = []
        for ticker in tickers:
            rt = realtime_prices.get(ticker)
            if not rt:
                continue

            current_volume = rt.get('volume', 0)
            change_rate = rt.get('change_rate', 0.0)
            current_price = rt.get('current_price', 0)
            name = rt.get('name', ticker)
            avg_volume = avg_volumes.get(ticker, 0)

            signal = self.detect_accumulation_signal(
                ticker=ticker,
                name=name,
                current_volume=current_volume,
                avg_volume_5d=avg_volume,
                change_rate=change_rate,
                current_price=current_price
            )

            if signal:
                detected.append(signal)
                logger.info(
                    f"🔍 조짐 감지: {name}({ticker}) - "
                    f"거래량 {signal['volume_ratio']:.1f}배, "
                    f"등락률 {signal['change_rate']:+.2f}%"
                )

        logger.info(f"PreSurgeDetector: 총 {len(detected)}개 종목 조짐 감지")
        return detected

    async def _get_avg_volumes_5d_batch(self, tickers: List[str]) -> Dict[str, int]:
        """
        5일 평균 거래량 배치 조회

        Args:
            tickers: 종목 코드 리스트

        Returns:
            {ticker: avg_volume_5d}
        """
        from datetime import timedelta

        result = {}
        today = datetime.now()

        # 최근 5 거래일 데이터 조회
        for i in range(1, 10):  # 최대 10일 전까지 (주말 고려)
            try:
                target_date = today - timedelta(days=i)
                df = await self.data_service.get_market_snapshot(target_date)

                if df.empty:
                    continue

                df = df.set_index('ticker')

                for ticker in tickers:
                    if ticker not in df.index:
                        continue

                    volume = df.loc[ticker].get('거래량', 0)
                    if ticker not in result:
                        result[ticker] = []
                    result[ticker].append(volume)

                # 5일치 수집되면 중단
                if all(len(result.get(t, [])) >= 5 for t in tickers if t in result):
                    break

            except Exception as e:
                logger.warning(f"거래량 조회 실패 ({target_date}): {e}")
                continue

        # 평균 계산
        avg_result = {}
        for ticker, volumes in result.items():
            if volumes:
                avg_result[ticker] = int(sum(volumes) / len(volumes))

        return avg_result

    async def detect_and_notify(self) -> List[Dict]:
        """
        조짐 감지 후 알림 (텔레그램 연동용)

        Returns:
            감지된 종목 리스트
        """
        detected = await self.scan_all_stocks()

        if detected:
            # 신뢰도 순 정렬
            detected.sort(key=lambda x: x['confidence'], reverse=True)

            # DB 저장
            self._save_to_db(detected)

            logger.info(f"🚀 조짐 감지 완료: {len(detected)}개 종목")

        return detected

    def _save_to_db(self, detected: List[Dict]):
        """
        감지 결과 DB 저장

        Args:
            detected: 감지된 종목 리스트
        """
        from app.db.database import get_db
        from app.db.models import TriggerResult

        date_str = datetime.now().strftime('%Y-%m-%d')

        with get_db() as db:
            for signal in detected:
                db_trigger = TriggerResult(
                    ticker=signal['ticker'],
                    name=signal['name'],
                    trigger_type='pre_surge',  # 새 트리거 타입
                    session='realtime',
                    current_price=signal.get('current_price', 0),
                    change_rate=signal['change_rate'],
                    volume=0,  # volume_ratio로 대체
                    trading_value=0,
                    composite_score=signal['confidence'],
                    date=date_str,
                    detected_at=datetime.fromisoformat(signal['detected_at'])
                )
                db.add(db_trigger)

            logger.info(f"✅ 조짐 감지 결과 DB 저장: {len(detected)}개")
