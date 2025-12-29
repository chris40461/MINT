"""
Price Data Collector
yfinance를 통한 일별 OHLCV 가격 데이터 수집
"""

import sys
from pathlib import Path

# 직접 실행 시 부모 디렉토리를 Python path에 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from openbb import obb

from config.settings import (
    RATE_LIMIT_SLEEP,
    START_DATE,
    END_DATE
)
from utils.logger import get_logger
from utils.retry import retry_with_backoff
import time

logger = get_logger(__name__)


class PriceCollector:
    """
    OHLCV 가격 데이터 수집기

    yfinance provider를 통해 일별 가격 데이터 수집:
    - Open, High, Low, Close, Volume
    """

    def __init__(self):
        """초기화"""
        self.provider = 'yfinance'
        logger.info("PriceCollector initialized (provider: yfinance)")

    @retry_with_backoff(max_retries=5, base_delay=2)
    def _fetch_price_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        단일 종목의 가격 데이터 수집

        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일

        Returns:
            pd.DataFrame: OHLCV 데이터 (index: date)
                         columns: ['open', 'high', 'low', 'close', 'volume']
                         실패 시 None
        """
        try:
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')

            logger.debug(f"{ticker}: Fetching price data {start_str} ~ {end_str}")

            result = obb.equity.price.historical(
                symbol=ticker,
                start_date=start_str,
                end_date=end_str,
                provider=self.provider
            )

            if not hasattr(result, 'to_dataframe'):
                logger.warning(f"{ticker}: No to_dataframe method")
                return None

            df = result.to_dataframe()

            if df.empty:
                logger.warning(f"{ticker}: Empty DataFrame")
                return None

            logger.info(f"{ticker}: Collected {len(df)} price records")
            return df

        except Exception as e:
            logger.error(f"{ticker} price collection failed: {str(e)}")
            raise

    def collect_ticker(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[List[Dict]]:
        """
        단일 종목의 가격 데이터 수집 (DB 저장 형식으로 변환)

        Args:
            ticker: 종목 코드
            start_date: 시작일 (기본값: 1년 전)
            end_date: 종료일 (기본값: 오늘)

        Returns:
            List[Dict]: [
                {
                    'ticker': str,
                    'date': date,
                    'open': float,
                    'high': float,
                    'low': float,
                    'close': float,
                    'volume': int,
                    'provider': str
                },
                ...
            ]
            실패 시 None
        """
        if start_date is None:
            start_date = START_DATE
        if end_date is None:
            end_date = END_DATE

        try:
            df = self._fetch_price_data(ticker, start_date, end_date)

            if df is None:
                return None

            # DataFrame → List[Dict] 변환
            records = []
            for date_idx, row in df.iterrows():
                # Timestamp → date 변환
                trade_date = date_idx.date() if hasattr(date_idx, 'date') else date_idx

                record = {
                    'ticker': ticker,
                    'date': trade_date,
                    'open': row.get('open'),
                    'high': row.get('high'),
                    'low': row.get('low'),
                    'close': row.get('close'),
                    'volume': int(row.get('volume')) if row.get('volume') is not None else None,
                    'provider': self.provider
                }
                records.append(record)

            logger.info(f"{ticker}: Converted {len(records)} price records")
            return records

        except Exception as e:
            logger.error(f"{ticker} price collection failed: {str(e)}")
            return None

    def collect_latest(self, ticker: str) -> Optional[List[Dict]]:
        """
        가장 최근 거래일 가격 데이터 수집

        Args:
            ticker: 종목 코드

        Returns:
            List[Dict]: 최근 거래일 가격 데이터 (1개 record)
                        실패 시 None

        Note:
            - Daily update에서 사용
            - 주말/공휴일을 고려하여 최근 7일 데이터를 가져온 후
              마지막 거래일 데이터 반환 (records[-1])
        """
        # 최근 7일 데이터 조회 (주말/공휴일 고려)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        logger.info(f"{ticker}: Collecting latest trading day price")

        try:
            records = self.collect_ticker(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )

            if not records:
                logger.warning(f"{ticker}: No recent price data found")
                return None

            # 가장 최근 거래일 데이터 반환 (마지막 record)
            latest_record = records[-1]
            logger.info(f"{ticker}: Latest trading day - {latest_record['date']}")

            return [latest_record]

        except Exception as e:
            logger.error(f"{ticker} latest price collection failed: {str(e)}")
            return None

    def collect_multiple(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        rate_limit: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        여러 종목의 가격 데이터 수집

        Args:
            tickers: 종목 코드 리스트
            start_date: 시작일
            end_date: 종료일
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: [records]}
        """
        logger.info(f"Collecting price data for {len(tickers)} tickers")

        results = {}

        for idx, ticker in enumerate(tickers, 1):
            try:
                records = self.collect_ticker(ticker, start_date, end_date)

                if records:
                    results[ticker] = records

                # Rate limiting
                if rate_limit and idx < len(tickers):
                    time.sleep(RATE_LIMIT_SLEEP)

            except Exception as e:
                logger.error(f"{ticker} collection failed: {str(e)}")
                continue

        logger.info(f"Collected price data for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_latest_batch(
        self,
        tickers: List[str],
        rate_limit: bool = True
    ) -> Dict[str, Dict]:
        """
        여러 종목의 최근 거래일 가격 데이터 배치 수집

        Args:
            tickers: 종목 코드 리스트
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: latest_record}

        Note:
            - 각 종목별로 최근 7일 데이터를 가져와 마지막 거래일 반환
            - 주말/공휴일 자동 처리
        """
        logger.info(f"Collecting latest price for {len(tickers)} tickers")

        results = {}

        for idx, ticker in enumerate(tickers, 1):
            try:
                records = self.collect_latest(ticker)

                if records:
                    # collect_latest는 1개 record를 리스트로 반환
                    results[ticker] = records[0]

                # Rate limiting
                if rate_limit and idx < len(tickers):
                    time.sleep(RATE_LIMIT_SLEEP)

            except Exception as e:
                logger.error(f"{ticker} latest price collection failed: {str(e)}")
                continue

        logger.info(f"Collected latest price for {len(results)}/{len(tickers)} tickers")
        return results
