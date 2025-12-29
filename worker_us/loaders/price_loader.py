"""
Price Loader
일별 OHLCV 가격 데이터를 DB에 적재
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict
from sqlalchemy.orm import Session

from models.schemas import PriceDaily
from utils.logger import get_logger

logger = get_logger(__name__)


class PriceLoader:
    """
    일별 가격 데이터 DB 적재기

    Note:
        - PriceDaily는 (ticker, date) 복합 Primary Key
        - 배치 삽입 최적화 (bulk merge)
    """

    def __init__(self):
        """초기화"""
        logger.info("PriceLoader initialized")

    def load_single(
        self,
        record: Dict,
        session: Session
    ) -> bool:
        """
        단일 가격 데이터 적재

        Args:
            record: {
                'ticker': str,
                'date': date,
                'open': float,
                'high': float,
                'low': float,
                'close': float,
                'volume': int,
                'provider': str
            }
            session: DB 세션

        Returns:
            bool: 성공 시 True
        """
        try:
            price_obj = PriceDaily(
                ticker=record['ticker'],
                date=record['date'],
                open=record.get('open'),
                high=record.get('high'),
                low=record.get('low'),
                close=record.get('close'),
                volume=record.get('volume'),
                provider=record.get('provider', 'yfinance')
            )

            session.merge(price_obj)
            session.commit()

            logger.debug(f"{record['ticker']} {record['date']}: Price data loaded")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"{record['ticker']} {record['date']}: Load failed - {str(e)}")
            return False

    def load_batch(
        self,
        records: List[Dict],
        session: Session
    ) -> int:
        """
        여러 가격 데이터 배치 적재

        Args:
            records: 가격 데이터 리스트
            session: DB 세션

        Returns:
            int: 성공적으로 적재된 레코드 수
        """
        if not records:
            logger.warning("No records to load")
            return 0

        success_count = 0
        failed_count = 0

        try:
            for record in records:
                price_obj = PriceDaily(
                    ticker=record['ticker'],
                    date=record['date'],
                    open=record.get('open'),
                    high=record.get('high'),
                    low=record.get('low'),
                    close=record.get('close'),
                    volume=record.get('volume'),
                    provider=record.get('provider', 'yfinance')
                )
                session.merge(price_obj)
                success_count += 1

            session.commit()
            logger.info(f"Price batch loaded: {success_count} records")

        except Exception as e:
            session.rollback()
            logger.error(f"Price batch load failed: {str(e)}")
            failed_count = len(records) - success_count

        return success_count

    def load_ticker_batch(
        self,
        ticker: str,
        records: List[Dict],
        session: Session
    ) -> int:
        """
        단일 종목의 여러 날짜 데이터 배치 적재

        Args:
            ticker: 종목 코드
            records: 가격 데이터 리스트 (ticker 필드 포함 안 되어 있을 수 있음)
            session: DB 세션

        Returns:
            int: 성공적으로 적재된 레코드 수
        """
        # ticker 필드가 없으면 추가
        for record in records:
            if 'ticker' not in record:
                record['ticker'] = ticker

        return self.load_batch(records, session)

    def load_multiple_tickers(
        self,
        data: Dict[str, List[Dict]],
        session: Session
    ) -> Dict[str, int]:
        """
        여러 종목의 가격 데이터 배치 적재

        Args:
            data: {ticker: [price_records]}
            session: DB 세션

        Returns:
            dict: {ticker: loaded_count}
        """
        results = {}

        for ticker, records in data.items():
            count = self.load_ticker_batch(ticker, records, session)
            results[ticker] = count

        logger.info(f"Multiple tickers loaded: {len(results)} tickers, {sum(results.values())} total records")
        return results
