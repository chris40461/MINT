"""
News Loader
뉴스 데이터를 DB에 적재
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.schemas import News
from utils.logger import get_logger

logger = get_logger(__name__)


class NewsLoader:
    """
    뉴스 데이터 DB 적재기

    Note:
        - News는 id (autoincrement) Primary Key
        - URL 중복 체크하여 중복 뉴스 방지
        - 동일 ticker + URL이면 중복으로 간주
    """

    def __init__(self):
        """초기화"""
        logger.info("NewsLoader initialized")

    def _is_duplicate(
        self,
        ticker: str,
        url: str,
        session: Session
    ) -> bool:
        """
        중복 뉴스 체크

        Args:
            ticker: 종목 코드
            url: 뉴스 URL
            session: DB 세션

        Returns:
            bool: 중복이면 True
        """
        existing = session.query(News).filter(
            and_(
                News.ticker == ticker,
                News.url == url
            )
        ).first()

        return existing is not None

    def load_single(
        self,
        record: Dict,
        session: Session,
        skip_duplicate: bool = True
    ) -> bool:
        """
        단일 뉴스 데이터 적재

        Args:
            record: {
                'ticker': str,
                'published_date': datetime,
                'title': str,
                'url': str,
                'source': str,
                'provider': str
            }
            session: DB 세션
            skip_duplicate: 중복 뉴스 스킵 여부

        Returns:
            bool: 성공 시 True (중복 스킵 시 False)
        """
        try:
            # 중복 체크
            if skip_duplicate and self._is_duplicate(record['ticker'], record['url'], session):
                logger.debug(f"{record['ticker']}: Duplicate news skipped - {record['url']}")
                return False

            news_obj = News(
                ticker=record['ticker'],
                published_date=record['published_date'],
                title=record.get('title'),
                url=record.get('url'),
                source=record.get('source'),
                provider=record.get('provider', 'yfinance')
            )

            session.add(news_obj)
            session.commit()

            logger.debug(f"{record['ticker']}: News loaded - {record['title'][:50]}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"{record['ticker']}: News load failed - {str(e)}")
            return False

    def load_batch(
        self,
        records: List[Dict],
        session: Session,
        skip_duplicate: bool = True
    ) -> int:
        """
        여러 뉴스 데이터 배치 적재

        Args:
            records: 뉴스 데이터 리스트
            session: DB 세션
            skip_duplicate: 중복 뉴스 스킵 여부

        Returns:
            int: 성공적으로 적재된 레코드 수
        """
        if not records:
            logger.warning("No records to load")
            return 0

        success_count = 0

        for record in records:
            # 중복 체크
            if skip_duplicate and self._is_duplicate(record['ticker'], record['url'], session):
                continue

            try:
                news_obj = News(
                    ticker=record['ticker'],
                    published_date=record['published_date'],
                    title=record.get('title'),
                    url=record.get('url'),
                    source=record.get('source'),
                    provider=record.get('provider', 'yfinance')
                )

                session.add(news_obj)
                success_count += 1

            except Exception as e:
                logger.error(f"{record['ticker']}: News load failed - {str(e)}")
                continue

        try:
            session.commit()
            logger.info(f"News batch loaded: {success_count}/{len(records)} records (duplicates skipped)")
        except Exception as e:
            session.rollback()
            logger.error(f"News batch commit failed: {str(e)}")
            return 0

        return success_count

    def load_ticker_batch(
        self,
        ticker: str,
        records: List[Dict],
        session: Session,
        skip_duplicate: bool = True
    ) -> int:
        """
        단일 종목의 여러 뉴스 데이터 배치 적재

        Args:
            ticker: 종목 코드
            records: 뉴스 데이터 리스트
            session: DB 세션
            skip_duplicate: 중복 뉴스 스킵 여부

        Returns:
            int: 성공적으로 적재된 레코드 수
        """
        # ticker 필드가 없으면 추가
        for record in records:
            if 'ticker' not in record:
                record['ticker'] = ticker

        return self.load_batch(records, session, skip_duplicate)

    def load_multiple_tickers(
        self,
        data: Dict[str, List[Dict]],
        session: Session,
        skip_duplicate: bool = True
    ) -> Dict[str, int]:
        """
        여러 종목의 뉴스 데이터 배치 적재

        Args:
            data: {ticker: [news_records]}
            session: DB 세션
            skip_duplicate: 중복 뉴스 스킵 여부

        Returns:
            dict: {ticker: loaded_count}
        """
        results = {}

        for ticker, records in data.items():
            count = self.load_ticker_batch(ticker, records, session, skip_duplicate)
            results[ticker] = count

        logger.info(f"Multiple tickers news loaded: {len(results)} tickers, {sum(results.values())} total records")
        return results
