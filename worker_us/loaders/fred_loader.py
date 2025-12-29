"""
FRED Loader
FRED 거시경제 지표 데이터를 DB에 적재
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from models.schemas import FredMacro
from utils.logger import get_logger

logger = get_logger(__name__)


class FredLoader:
    """
    FRED 거시경제 지표 DB 적재기

    Note:
        - FredMacro는 date가 Primary Key
        - session.merge()로 upsert (중복 시 업데이트)
    """

    def __init__(self):
        """초기화"""
        logger.info("FredLoader initialized")

    def load_single(
        self,
        record: Dict,
        session: Session
    ) -> bool:
        """
        단일 FRED 데이터 적재

        Args:
            record: {
                'date': date,
                'dgs10': float,
                'dgs2': float,
                'yield_spread': float,
                'fed_funds_rate': float,
                'cpi_yoy': float,
                'unemployment_rate': float
            }
            session: DB 세션

        Returns:
            bool: 성공 시 True
        """
        try:
            # FredMacro 객체 생성
            fred_obj = FredMacro(
                date=record['date'],
                dgs10=record.get('dgs10'),
                dgs2=record.get('dgs2'),
                yield_spread=record.get('yield_spread'),
                fed_funds_rate=record.get('fed_funds_rate'),
                cpi_yoy=record.get('cpi_yoy'),
                unemployment_rate=record.get('unemployment_rate')
            )

            # Upsert (merge)
            session.merge(fred_obj)
            session.commit()

            logger.info(f"FRED data loaded: {record['date']}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"FRED data load failed: {str(e)}")
            return False

    def load(
        self,
        record: Dict,
        session: Session
    ) -> bool:
        """
        FRED 데이터 적재 (단일 레코드만 존재)

        Args:
            record: FRED 데이터 딕셔너리
            session: DB 세션

        Returns:
            bool: 성공 시 True

        Note:
            - FRED는 항상 단일 레코드 (최신 거시경제 지표)
            - 배치 개념 없음
        """
        return self.load_single(record, session)
