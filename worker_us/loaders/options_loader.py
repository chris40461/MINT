"""
Options Loader
옵션 요약 통계 데이터를 DB에 적재
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict
from sqlalchemy.orm import Session

from models.schemas import OptionsSummary
from utils.logger import get_logger

logger = get_logger(__name__)


class OptionsLoader:
    """
    옵션 요약 통계 DB 적재기

    Note:
        - OptionsSummary는 (ticker, snapshot_date) 복합 Primary Key
        - session.merge()로 upsert (중복 시 업데이트)
    """

    def __init__(self):
        """초기화"""
        logger.info("OptionsLoader initialized")

    def load_single(
        self,
        record: Dict,
        session: Session
    ) -> bool:
        """
        단일 옵션 요약 데이터 적재

        Args:
            record: {
                'ticker': str,
                'snapshot_date': date,
                'put_call_ratio_volume': float,
                'put_call_ratio_oi': float,
                'total_call_volume': int,
                'total_put_volume': int,
                'total_call_oi': int,
                'total_put_oi': int,
                'avg_iv_call': float,
                'avg_iv_put': float,
                'avg_iv': float,
                'provider': str
            }
            session: DB 세션

        Returns:
            bool: 성공 시 True
        """
        try:
            options_obj = OptionsSummary(
                ticker=record['ticker'],
                snapshot_date=record['snapshot_date'],
                put_call_ratio_volume=record.get('put_call_ratio_volume'),
                put_call_ratio_oi=record.get('put_call_ratio_oi'),
                total_call_volume=record.get('total_call_volume'),
                total_put_volume=record.get('total_put_volume'),
                total_call_oi=record.get('total_call_oi'),
                total_put_oi=record.get('total_put_oi'),
                avg_iv_call=record.get('avg_iv_call'),
                avg_iv_put=record.get('avg_iv_put'),
                avg_iv=record.get('avg_iv'),
                provider=record.get('provider', 'cboe')
            )

            session.merge(options_obj)
            session.commit()

            logger.debug(f"{record['ticker']} {record['snapshot_date']}: Options summary loaded")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"{record['ticker']} {record['snapshot_date']}: Load failed - {str(e)}")
            return False

    def load_batch(
        self,
        records: List[Dict],
        session: Session
    ) -> int:
        """
        여러 옵션 요약 데이터 배치 적재

        Args:
            records: 옵션 요약 데이터 리스트
            session: DB 세션

        Returns:
            int: 성공적으로 적재된 레코드 수
        """
        if not records:
            logger.warning("No records to load")
            return 0

        success_count = 0

        try:
            for record in records:
                options_obj = OptionsSummary(
                    ticker=record['ticker'],
                    snapshot_date=record['snapshot_date'],
                    put_call_ratio_volume=record.get('put_call_ratio_volume'),
                    put_call_ratio_oi=record.get('put_call_ratio_oi'),
                    total_call_volume=record.get('total_call_volume'),
                    total_put_volume=record.get('total_put_volume'),
                    total_call_oi=record.get('total_call_oi'),
                    total_put_oi=record.get('total_put_oi'),
                    avg_iv_call=record.get('avg_iv_call'),
                    avg_iv_put=record.get('avg_iv_put'),
                    avg_iv=record.get('avg_iv'),
                    provider=record.get('provider', 'cboe')
                )

                session.merge(options_obj)
                success_count += 1

            session.commit()
            logger.info(f"Options summary batch loaded: {success_count} records")

        except Exception as e:
            session.rollback()
            logger.error(f"Options summary batch load failed: {str(e)}")
            return 0

        return success_count

    def load_multiple_tickers(
        self,
        data: Dict[str, Dict],
        session: Session
    ) -> Dict[str, bool]:
        """
        여러 종목의 옵션 요약 데이터 배치 적재

        Args:
            data: {ticker: options_summary_record}
            session: DB 세션

        Returns:
            dict: {ticker: success}
        """
        results = {}

        for ticker, record in data.items():
            # ticker 필드가 없으면 추가
            if 'ticker' not in record:
                record['ticker'] = ticker

            success = self.load_single(record, session)
            results[ticker] = success

        success_count = sum(1 for v in results.values() if v)
        logger.info(f"Multiple tickers options summary loaded: {success_count}/{len(results)} tickers")
        return results
