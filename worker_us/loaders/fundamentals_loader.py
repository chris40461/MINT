"""
Fundamentals Loader
펀더멘탈 지표 데이터를 DB에 적재
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict
from sqlalchemy.orm import Session

from models.schemas import Fundamentals
from utils.logger import get_logger

logger = get_logger(__name__)


class FundamentalsLoader:
    """
    펀더멘탈 지표 DB 적재기

    Note:
        - Fundamentals는 (ticker, snapshot_date) 복합 Primary Key
        - session.merge()로 upsert (중복 시 업데이트)
    """

    def __init__(self):
        """초기화"""
        logger.info("FundamentalsLoader initialized")

    def load_single(
        self,
        record: Dict,
        session: Session
    ) -> bool:
        """
        단일 펀더멘탈 데이터 적재

        Args:
            record: {
                'ticker': str,
                'snapshot_date': date,
                # Valuation Ratios
                'market_cap': float,
                'pe_ratio': float,
                'foward_pe': float,
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
            session: DB 세션

        Returns:
            bool: 성공 시 True
        """
        try:
            fund_obj = Fundamentals(
                ticker=record['ticker'],
                snapshot_date=record['snapshot_date'],
                # Valuation Ratios
                market_cap=record.get('market_cap'),
                pe_ratio=record.get('pe_ratio'),
                foward_pe=record.get('foward_pe'),
                price_to_sales=record.get('price_to_sales'),
                price_to_book=record.get('price_to_book'),
                eps=record.get('eps'),
                book_value_per_share=record.get('book_value_per_share'),
                # Profitability
                return_on_equity=record.get('return_on_equity'),
                return_on_assets=record.get('return_on_assets'),
                profit_margin=record.get('profit_margin'),
                operating_margin=record.get('operating_margin'),
                gross_margin=record.get('gross_margin'),
                # Financial Health
                debt_to_equity=record.get('debt_to_equity'),
                long_term_debt_to_equity=record.get('long_term_debt_to_equity'),
                current_ratio=record.get('current_ratio'),
                quick_ratio=record.get('quick_ratio'),
                # Other
                payout_ratio=record.get('payout_ratio'),
                provider=record.get('provider', 'finviz')
            )

            session.merge(fund_obj)
            session.commit()

            logger.debug(f"{record['ticker']} {record['snapshot_date']}: Fundamentals loaded")
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
        여러 펀더멘탈 데이터 배치 적재

        Args:
            records: 펀더멘탈 데이터 리스트
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
                fund_obj = Fundamentals(
                    ticker=record['ticker'],
                    snapshot_date=record['snapshot_date'],
                    # Valuation Ratios
                    market_cap=record.get('market_cap'),
                    pe_ratio=record.get('pe_ratio'),
                    foward_pe=record.get('foward_pe'),
                    price_to_sales=record.get('price_to_sales'),
                    price_to_book=record.get('price_to_book'),
                    eps=record.get('eps'),
                    book_value_per_share=record.get('book_value_per_share'),
                    # Profitability
                    return_on_equity=record.get('return_on_equity'),
                    return_on_assets=record.get('return_on_assets'),
                    profit_margin=record.get('profit_margin'),
                    operating_margin=record.get('operating_margin'),
                    gross_margin=record.get('gross_margin'),
                    # Financial Health
                    debt_to_equity=record.get('debt_to_equity'),
                    long_term_debt_to_equity=record.get('long_term_debt_to_equity'),
                    current_ratio=record.get('current_ratio'),
                    quick_ratio=record.get('quick_ratio'),
                    # Other
                    payout_ratio=record.get('payout_ratio'),
                    provider=record.get('provider', 'finviz')
                )

                session.merge(fund_obj)
                success_count += 1

            session.commit()
            logger.info(f"Fundamentals batch loaded: {success_count} records")

        except Exception as e:
            session.rollback()
            logger.error(f"Fundamentals batch load failed: {str(e)}")
            return 0

        return success_count

    def load_multiple_tickers(
        self,
        data: Dict[str, Dict],
        session: Session
    ) -> Dict[str, bool]:
        """
        여러 종목의 펀더멘탈 데이터 배치 적재

        Args:
            data: {ticker: fundamentals_record}
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
        logger.info(f"Multiple tickers fundamentals loaded: {success_count}/{len(results)} tickers")
        return results
