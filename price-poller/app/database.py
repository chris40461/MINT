"""
Database operations for Price Poller Service

SQLAlchemy를 사용하여 realtime_prices 테이블에 데이터를 씁니다.
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Index, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    }
)

# Enable WAL mode for better concurrency using event listener
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class RealtimePrice(Base):
    """실시간 주가 테이블"""
    __tablename__ = 'realtime_prices'

    ticker = Column(String(10), primary_key=True, index=True)
    current_price = Column(Integer, nullable=False)
    change_rate = Column(Float, nullable=False)
    change_amount = Column(Integer, nullable=False)
    volume = Column(Integer, nullable=False)
    open_price = Column(Integer, nullable=True)
    high_price = Column(Integer, nullable=True)
    low_price = Column(Integer, nullable=True)
    trading_value = Column(Integer, default=0)
    market_status = Column(String(20), default='open')
    data_source = Column(String(20), default='kis')
    updated_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_ticker_updated', 'ticker', 'updated_at'),
    )


class FinancialData(Base):
    """재무 데이터 테이블 (읽기 전용)"""
    __tablename__ = 'financial_data'

    ticker = Column(String(10), primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    filter_status = Column(String(20), default='unknown')


class DatabaseWriter:
    """Database write operations"""

    def __init__(self):
        self.session: Optional[Session] = None

    def connect(self):
        """Open database session"""
        self.session = SessionLocal()
        logger.info("✅ Database connection opened")

    def close(self):
        """Close database session"""
        if self.session:
            self.session.close()
            logger.info("Database connection closed")

    def get_filtered_tickers(self) -> List[str]:
        """
        필터 통과 종목 조회 (filter_status='pass')

        Returns:
            티커 리스트 (예: ['005930', '000660', ...])
        """
        if not self.session:
            raise RuntimeError("Database not connected")

        try:
            results = self.session.query(FinancialData.ticker).filter(
                FinancialData.filter_status == 'pass'
            ).all()

            tickers = [r.ticker for r in results]
            logger.info(f"📊 필터 통과 종목 {len(tickers)}개 조회")
            return tickers

        except Exception as e:
            logger.error(f"❌ 필터 종목 조회 실패: {e}")
            return []

    def update_realtime_price(self, ticker: str, price_data: Dict[str, Any]) -> bool:
        """
        실시간 가격 업데이트 (UPDATE or INSERT)

        Args:
            ticker: 종목 코드
            price_data: {
                'current_price': int,
                'change_rate': float,
                'change_amount': int,
                'volume': int,
                'open_price': int,
                'high_price': int,
                'low_price': int,
                'trading_value': int,
                'market_status': str,
                'updated_at': datetime
            }

        Returns:
            성공 여부
        """
        if not self.session:
            raise RuntimeError("Database not connected")

        try:
            # Check if record exists
            existing = self.session.query(RealtimePrice).filter_by(ticker=ticker).first()

            if existing:
                # Update existing record
                for key, value in price_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                # Insert new record
                new_price = RealtimePrice(
                    ticker=ticker,
                    data_source='kis',
                    **price_data
                )
                self.session.add(new_price)

            self.session.commit()
            return True

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ {ticker} 가격 업데이트 실패: {e}")
            return False

    def batch_update_realtime_prices(
        self,
        batch_data: Dict[str, Dict[str, Any]],
        session: str = '정규시간'
    ) -> int:
        """
        배치 가격 업데이트 (시간대별 필드 매핑)

        Args:
            batch_data: {ticker: price_data, ...}
            session: 현재 거래 시간대 (동시호가 시 예상 체결가 사용)

        Returns:
            성공한 종목 수
        """
        success_count = 0
        is_call_auction = session in ['장_시작_동시호가', '장_마감_동시호가']

        for ticker, price_data in batch_data.items():
            # 동시호가 시간대: 예상 체결가로 대체
            if is_call_auction:
                price_data = self._apply_call_auction_mapping(price_data)

            # DB 저장 전 동시호가 필드 제거 (테이블에 없는 컬럼)
            clean_data = {k: v for k, v in price_data.items()
                         if k not in ['prev_close_price', 'expected_diff',
                                     'expected_change_rate', 'expected_volume']}

            if self.update_realtime_price(ticker, clean_data):
                success_count += 1

        return success_count

    def _apply_call_auction_mapping(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        동시호가 시간대 데이터 매핑

        예상 체결가가 있으면 현재가/등락률/거래량을 대체
        """
        expected_diff = price_data.get('expected_diff', 0)
        prev_close = price_data.get('prev_close_price', 0)

        # 예상 체결가가 존재하고 전일 종가도 있으면 대체
        if expected_diff != 0 and prev_close > 0:
            # 예상 체결가 = 전일 종가 + 예상 대비
            expected_price = prev_close + expected_diff
            price_data['current_price'] = expected_price
            price_data['change_amount'] = expected_diff

            # 예상 등락률로 대체
            expected_rate = price_data.get('expected_change_rate', 0)
            if expected_rate != 0:
                price_data['change_rate'] = expected_rate

            # 예상 거래량으로 대체
            expected_vol = price_data.get('expected_volume', 0)
            if expected_vol > 0:
                price_data['volume'] = expected_vol

        return price_data


def split_into_batches(tickers: List[str], batch_size: int = 30) -> List[List[str]]:
    """
    종목 리스트를 배치로 분할

    Args:
        tickers: 종목 코드 리스트
        batch_size: 배치 크기 (기본 30개)

    Returns:
        배치 리스트
    """
    return [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
