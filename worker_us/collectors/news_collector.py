"""
News Collector
yfinance를 통한 종목별 뉴스 데이터 수집
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
)
from utils.logger import get_logger
from utils.retry import retry_with_backoff
import time

logger = get_logger(__name__)


class NewsCollector:
    """
    종목별 뉴스 데이터 수집기

    yfinance provider를 통해 최근 뉴스 수집:
    - 제목, 내용, 출처, 발행일시, URL
    """

    def __init__(self):
        """초기화"""
        self.provider = 'yfinance'
        logger.info("NewsCollector initialized (provider: yfinance)")

    @retry_with_backoff(max_retries=5, base_delay=2)
    def _fetch_news(
        self,
        ticker: str,
        limit: int = 50
    ) -> Optional[pd.DataFrame]:
        """
        단일 종목의 뉴스 데이터 수집

        Args:
            ticker: 종목 코드
            limit: 최대 뉴스 개수 (기본값: 50)

        Returns:
            pd.DataFrame: 뉴스 데이터
                         columns: ['title', 'url', 'source']
                         index: datetime (published_date)
                         실패 시 None
        """
        try:
            logger.debug(f"{ticker}: Fetching news (limit: {limit})")

            result = obb.news.company(
                symbol=ticker,
                limit=limit,
                provider=self.provider
            )

            if not hasattr(result, 'to_dataframe'):
                logger.warning(f"{ticker}: No to_dataframe method")
                return None

            df = result.to_dataframe()

            if df.empty:
                logger.warning(f"{ticker}: No news found")
                return None

            logger.info(f"{ticker}: Collected {len(df)} news articles")
            return df

        except Exception as e:
            logger.error(f"{ticker} news collection failed: {str(e)}")
            raise

    def collect_ticker(
        self,
        ticker: str,
        limit: int = 50,
        days: Optional[int] = None
    ) -> Optional[List[Dict]]:
        """
        단일 종목의 뉴스 데이터 수집 (DB 저장 형식으로 변환)

        Args:
            ticker: 종목 코드
            limit: 최대 뉴스 개수
            days: 최근 N일 이내 뉴스만 필터링 (None이면 전체)

        Returns:
            List[Dict]: [
                {
                    'ticker': str,
                    'published_date': datetime,
                    'title': str,
                    'url': str,
                    'source': str,
                    'provider': str
                },
                ...
            ]
            실패 시 None

        Note:
            - yfinance에서는 text 컬럼이 제공되지 않음 (title, url, source만 제공)
        """
        try:
            df = self._fetch_news(ticker, limit)

            if df is None:
                return None

            # 날짜 필터링 (날짜는 index에 있음)
            if days is not None:
                cutoff_date = datetime.now() - timedelta(days=days)
                # Make cutoff_date timezone-aware if index is timezone-aware
                if df.index.tzinfo is not None:
                    from datetime import timezone
                    cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
                df = df[df.index >= cutoff_date]
                logger.debug(f"{ticker}: Filtered to last {days} days, {len(df)} articles remaining")

            if df.empty:
                logger.warning(f"{ticker}: No news after date filtering")
                return None

            # DataFrame → List[Dict] 변환
            records = []
            for idx, row in df.iterrows():
                # 날짜는 index에 있음 (initial_setup.py:517-520 참고)
                published_date = idx
                if hasattr(idx, 'to_pydatetime'):
                    published_date = idx  # Already datetime

                record = {
                    'ticker': ticker,
                    'published_date': published_date,
                    'title': row.get('title'),
                    'url': row.get('url'),
                    'source': row.get('source'),  # source 컬럼 사용 (text 없음)
                    'provider': self.provider
                }
                records.append(record)

            logger.info(f"{ticker}: Converted {len(records)} news records")
            return records

        except Exception as e:
            logger.error(f"{ticker} news collection failed: {str(e)}")
            return None

    def collect_latest(
        self,
        ticker: str,
        days: int = 7,
        limit: int = 50
    ) -> Optional[List[Dict]]:
        """
        최근 N일 이내 뉴스만 수집

        Args:
            ticker: 종목 코드
            days: 최근 N일 (기본값: 7일)
            limit: 최대 뉴스 개수

        Returns:
            List[Dict]: 최근 N일 이내 뉴스 데이터
                        실패 시 None

        Note:
            - Daily update에서 사용
            - 최근 7일 이내 뉴스만 수집하여 중복 방지
        """
        logger.info(f"{ticker}: Collecting news from last {days} days")

        return self.collect_ticker(
            ticker=ticker,
            limit=limit,
            days=days
        )

    def collect_multiple(
        self,
        tickers: List[str],
        limit: int = 50,
        days: Optional[int] = None,
        rate_limit: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        여러 종목의 뉴스 데이터 수집

        Args:
            tickers: 종목 코드 리스트
            limit: 종목당 최대 뉴스 개수
            days: 최근 N일 이내 필터링 (None이면 전체)
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: [records]}
        """
        logger.info(f"Collecting news for {len(tickers)} tickers")

        results = {}

        for idx, ticker in enumerate(tickers, 1):
            try:
                records = self.collect_ticker(ticker, limit, days)

                if records:
                    results[ticker] = records

                # Rate limiting
                if rate_limit and idx < len(tickers):
                    time.sleep(RATE_LIMIT_SLEEP)

            except Exception as e:
                logger.error(f"{ticker} news collection failed: {str(e)}")
                continue

        logger.info(f"Collected news for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_latest_batch(
        self,
        tickers: List[str],
        days: int = 7,
        limit: int = 50,
        rate_limit: bool = True
    ) -> Dict[str, List[Dict]]:
        """
        여러 종목의 최근 뉴스 배치 수집

        Args:
            tickers: 종목 코드 리스트
            days: 최근 N일
            limit: 종목당 최대 뉴스 개수
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: [recent_news]}

        Note:
            - Daily update에서 사용
            - 각 종목별로 최근 N일 뉴스만 수집
        """
        logger.info(f"Collecting latest news for {len(tickers)} tickers (last {days} days)")

        return self.collect_multiple(
            tickers=tickers,
            limit=limit,
            days=days,
            rate_limit=rate_limit
        )
