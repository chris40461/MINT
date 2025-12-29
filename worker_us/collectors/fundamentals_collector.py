"""
Fundamentals Collector
Finviz를 통한 종목별 펀더멘탈 지표 수집
"""

import sys
from pathlib import Path

# 직접 실행 시 부모 디렉토리를 Python path에 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from openbb import obb

from config.settings import (
    RATE_LIMIT_SLEEP,
    END_DATE
)
from utils.logger import get_logger
from utils.retry import retry_with_backoff
import time

logger = get_logger(__name__)


class FundamentalsCollector:
    """
    Finviz 펀더멘탈 지표 수집기

    수집 지표 (18개):
    - Valuation: market_cap, pe_ratio, foward_pe, price_to_sales, price_to_book, eps, bvps
    - Profitability: roe, roa, profit_margin, operating_margin, gross_margin
    - Financial Health: debt_to_equity, long_term_debt_to_equity, current_ratio, quick_ratio
    - Other: payout_ratio
    """

    def __init__(self):
        """초기화"""
        self.provider = 'finviz'
        logger.info("FundamentalsCollector initialized (provider: finviz)")

    @retry_with_backoff(max_retries=5, base_delay=2)
    def _fetch_fundamentals(
        self,
        ticker: str
    ) -> Optional[pd.DataFrame]:
        """
        단일 종목의 펀더멘탈 지표 수집

        Args:
            ticker: 종목 코드

        Returns:
            pd.DataFrame: 펀더멘탈 지표 (1 row)
                         실패 시 None
        """
        try:
            logger.debug(f"{ticker}: Fetching fundamentals from Finviz")

            # initial_setup.py:459-461 참고
            result = obb.equity.fundamental.metrics(
                symbol=ticker,
                provider=self.provider
            )

            if not hasattr(result, 'to_dataframe'):
                logger.warning(f"{ticker}: No to_dataframe method")
                return None

            df = result.to_dataframe()

            if df.empty:
                logger.warning(f"{ticker}: Empty DataFrame")
                return None

            logger.info(f"{ticker}: Collected fundamentals")
            return df

        except Exception as e:
            logger.error(f"{ticker} fundamentals collection failed: {str(e)}")
            raise

    def collect_ticker(
        self,
        ticker: str,
        snapshot_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        단일 종목의 펀더멘탈 지표 수집 (DB 저장 형식으로 변환)

        Args:
            ticker: 종목 코드
            snapshot_date: 스냅샷 날짜 (기본값: 오늘)

        Returns:
            dict: {
                'ticker': str,
                'snapshot_date': date,
                # Valuation Ratios
                'market_cap': float,
                'pe_ratio': float,
                'foward_pe': float,  # IMPORTANT: Finviz typo!
                'price_to_sales': float,
                'price_to_book': float,
                'eps': float,
                'book_value_per_share': float,
                # Profitability
                'return_on_equity': float,
                'return_on_assets': float,
                'profit_margin': float,
                'operating_margin': float,
                'gross_margin': float,
                # Financial Health
                'debt_to_equity': float,
                'long_term_debt_to_equity': float,
                'current_ratio': float,
                'quick_ratio': float,
                # Other
                'payout_ratio': float,
                'provider': str
            }
            실패 시 None

        Note:
            - initial_setup.py:457-503 패턴 따름
            - df.iloc[0]로 첫 번째 행 가져오기 (단일 종목이므로 1 row)
            - row.get()으로 각 필드 추출
        """
        if snapshot_date is None:
            snapshot_date = END_DATE

        try:
            df = self._fetch_fundamentals(ticker)

            if df is None:
                return None

            # initial_setup.py:467 참고: df.iloc[0] 사용
            row = df.iloc[0]

            # initial_setup.py:469-495 참고: Map all 18 columns
            record = {
                'ticker': ticker,
                'snapshot_date': snapshot_date.date() if hasattr(snapshot_date, 'date') else snapshot_date,
                # Valuation Ratios
                'market_cap': row.get('market_cap'),
                'pe_ratio': row.get('pe_ratio'),
                'foward_pe': row.get('foward_pe'),  # IMPORTANT: typo exists in Finviz!
                'price_to_sales': row.get('price_to_sales'),
                'price_to_book': row.get('price_to_book'),
                'eps': row.get('eps'),
                'book_value_per_share': row.get('book_value_per_share'),
                # Profitability
                'return_on_equity': row.get('return_on_equity'),
                'return_on_assets': row.get('return_on_assets'),
                'profit_margin': row.get('profit_margin'),
                'operating_margin': row.get('operating_margin'),
                'gross_margin': row.get('gross_margin'),
                # Financial Health
                'debt_to_equity': row.get('debt_to_equity'),
                'long_term_debt_to_equity': row.get('long_term_debt_to_equity'),
                'current_ratio': row.get('current_ratio'),
                'quick_ratio': row.get('quick_ratio'),
                # Other
                'payout_ratio': row.get('payout_ratio'),
                'provider': self.provider
            }

            logger.info(f"{ticker}: Converted fundamentals record")
            return record

        except Exception as e:
            logger.error(f"{ticker} fundamentals collection failed: {str(e)}")
            return None

    def collect_latest(
        self,
        ticker: str
    ) -> Optional[Dict]:
        """
        최신 펀더멘탈 지표 수집 (오늘 날짜로)

        Args:
            ticker: 종목 코드

        Returns:
            dict: 펀더멘탈 지표
                  실패 시 None

        Note:
            - Daily update에서 사용
            - snapshot_date는 오늘 날짜로 자동 설정
        """
        logger.info(f"{ticker}: Collecting latest fundamentals")

        return self.collect_ticker(ticker)

    def collect_multiple(
        self,
        tickers: List[str],
        snapshot_date: Optional[datetime] = None,
        rate_limit: bool = True
    ) -> Dict[str, Dict]:
        """
        여러 종목의 펀더멘탈 지표 수집

        Args:
            tickers: 종목 코드 리스트
            snapshot_date: 스냅샷 날짜
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: record}
        """
        logger.info(f"Collecting fundamentals for {len(tickers)} tickers")

        results = {}

        for idx, ticker in enumerate(tickers, 1):
            try:
                record = self.collect_ticker(ticker, snapshot_date)

                if record:
                    results[ticker] = record

                # Rate limiting
                if rate_limit and idx < len(tickers):
                    time.sleep(RATE_LIMIT_SLEEP)

            except Exception as e:
                logger.error(f"{ticker} fundamentals collection failed: {str(e)}")
                continue

        logger.info(f"Collected fundamentals for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_latest_batch(
        self,
        tickers: List[str],
        rate_limit: bool = True
    ) -> Dict[str, Dict]:
        """
        여러 종목의 최신 펀더멘탈 배치 수집

        Args:
            tickers: 종목 코드 리스트
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: latest_record}

        Note:
            - Daily update에서 사용
            - 각 종목별로 최신 펀더멘탈 수집
        """
        logger.info(f"Collecting latest fundamentals for {len(tickers)} tickers")

        return self.collect_multiple(
            tickers=tickers,
            snapshot_date=None,  # 오늘 날짜 사용
            rate_limit=rate_limit
        )
