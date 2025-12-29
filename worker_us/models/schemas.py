"""
Nasdaq Database Schema (v3 - 9 Tables)
SQLite database for US stock data collection

Based on actual OpenBB data structure (tested with AAPL)
- Only columns that actually exist in OpenBB responses
- Removed excessive nullable columns to reduce NULL values

v3 Changes (2024-11-20):
- Removed 'options' table (사용자 요청 시 CBOE API 실시간 조회로 대체)
- Kept 'options_summary' table (매일 업데이트, PCR/IV 요약 통계)
- Total: 9 tables
"""

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Date, DateTime, Text,
    Index, ForeignKey, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

Base = declarative_base()

# ==================================================================================
# 1. 종목 기본 정보 (Master Table)
# ==================================================================================
class Stock(Base):
    __tablename__ = 'stocks'

    ticker = Column(String(10), primary_key=True)
    name = Column(String(200))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)  # Finviz에서 가져옴
    exchange = Column(String(20), default='NASDAQ')
    last_updated = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index('idx_sector', 'sector'),
        Index('idx_market_cap', 'market_cap'),
    )


# ==================================================================================
# 2. FRED 거시경제 지표 (Global, 종목 무관)
# ==================================================================================
class FredMacro(Base):
    __tablename__ = 'fred_macro'

    date = Column(Date, primary_key=True)
    dgs10 = Column(Float)  # 10년물 국채 금리
    dgs2 = Column(Float)   # 2년물 국채 금리
    yield_spread = Column(Float)  # 장단기 금리차 (10Y - 2Y)
    fed_funds_rate = Column(Float)  # 연방기금금리
    cpi_yoy = Column(Float)  # CPI 전년 대비 증가율 (%)
    unemployment_rate = Column(Float)  # 실업률 (%)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_fred_date', 'date'),
    )


# ==================================================================================
# 3. 일별 OHLCV (yfinance)
# ==================================================================================
class PriceDaily(Base):
    __tablename__ = 'price_daily'

    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'), primary_key=True)
    date = Column(Date, primary_key=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Integer)
    provider = Column(String(20), default='yfinance')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('ticker', 'date', name='uq_price_ticker_date'),
        Index('idx_price_ticker', 'ticker'),
        Index('idx_price_date', 'date'),
    )


# ==================================================================================
# 4. Income Statement (손익계산서) - yfinance 실제 컬럼 기준
# ==================================================================================
class IncomeStatement(Base):
    __tablename__ = 'income_statement'

    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'), primary_key=True)
    period = Column(String(10), primary_key=True)  # 'annual' or 'quarterly'
    fiscal_date = Column(Date, primary_key=True)  # period_ending

    # Core Financials (항상 존재)
    total_revenue = Column(Float)  # or operating_revenue
    cost_of_revenue = Column(Float)
    gross_profit = Column(Float)
    operating_income = Column(Float)
    net_income = Column(Float)

    # Important Metrics
    ebitda = Column(Float)
    operating_expense = Column(Float)  # operating_expense

    # Per Share
    eps_basic = Column(Float)  # basic_earnings_per_share
    eps_diluted = Column(Float)  # diluted_earnings_per_share

    # R&D and SG&A
    rd_expense = Column(Float)  # research_and_development_expense
    sga_expense = Column(Float)  # selling_general_and_admin_expense

    provider = Column(String(20), default='yfinance')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('ticker', 'period', 'fiscal_date', name='uq_income'),
        Index('idx_income_ticker', 'ticker'),
    )


# ==================================================================================
# 5. Balance Sheet (재무상태표) - yfinance 실제 컬럼 기준
# ==================================================================================
class BalanceSheet(Base):
    __tablename__ = 'balance_sheet'

    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'), primary_key=True)
    period = Column(String(10), primary_key=True)
    fiscal_date = Column(Date, primary_key=True)

    # Core Financials
    total_assets = Column(Float)
    total_current_assets = Column(Float)  # total_current_assets
    cash_and_cash_equivalents = Column(Float)  # cash_and_cash_equivalents

    total_liabilities = Column(Float)  # total_liabilities_net_minority_interest
    current_liabilities = Column(Float)  # current_liabilities
    total_debt = Column(Float)  # total_debt

    total_equity = Column(Float)  # common_stock_equity or total_equity_non_controlling_interests
    retained_earnings = Column(Float)

    provider = Column(String(20), default='yfinance')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('ticker', 'period', 'fiscal_date', name='uq_balance'),
        Index('idx_balance_ticker', 'ticker'),
    )


# ==================================================================================
# 6. Cash Flow Statement (현금흐름표) - yfinance 실제 컬럼 기준
# ==================================================================================
class CashFlow(Base):
    __tablename__ = 'cash_flow'

    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'), primary_key=True)
    period = Column(String(10), primary_key=True)
    fiscal_date = Column(Date, primary_key=True)

    # Core Cash Flows
    operating_cash_flow = Column(Float)
    investing_cash_flow = Column(Float)
    financing_cash_flow = Column(Float)

    # Important Items
    capital_expenditure = Column(Float)  # capital_expenditure (음수)
    cash_dividends_paid = Column(Float)  # cash_dividends_paid or common_stock_dividend_paid
    free_cash_flow = Column(Float)  # free_cash_flow (OCF - CapEx)

    provider = Column(String(20), default='yfinance')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('ticker', 'period', 'fiscal_date', name='uq_cashflow'),
        Index('idx_cashflow_ticker', 'ticker'),
    )


# ==================================================================================
# 7. 펀더멘탈 지표 (Finviz) - 실제 컬럼 기준
# ==================================================================================
class Fundamentals(Base):
    __tablename__ = 'fundamentals'

    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'), primary_key=True)
    snapshot_date = Column(Date, primary_key=True)

    # Valuation Ratios
    market_cap = Column(Float)
    pe_ratio = Column(Float)
    foward_pe = Column(Float)  # 실제 컬럼명 (typo in Finviz)
    price_to_sales = Column(Float)
    price_to_book = Column(Float)
    eps = Column(Float)
    book_value_per_share = Column(Float)

    # Profitability
    return_on_equity = Column(Float)
    return_on_assets = Column(Float)
    profit_margin = Column(Float)
    operating_margin = Column(Float)
    gross_margin = Column(Float)

    # Financial Health
    debt_to_equity = Column(Float)
    long_term_debt_to_equity = Column(Float)
    current_ratio = Column(Float)
    quick_ratio = Column(Float)

    # Other
    payout_ratio = Column(Float)

    provider = Column(String(20), default='finviz')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('ticker', 'snapshot_date', name='uq_fund'),
        Index('idx_fund_ticker', 'ticker'),
    )


# ==================================================================================
# 8. 뉴스 (yfinance)
# ==================================================================================
class News(Base):
    __tablename__ = 'news'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'))
    published_date = Column(DateTime)  # index in yfinance
    title = Column(Text)
    url = Column(Text)
    source = Column(String(100))

    # 추후 LLM 센티먼트 분석 추가
    sentiment_score = Column(Float, nullable=True)

    provider = Column(String(20), default='yfinance')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_news_ticker', 'ticker'),
        Index('idx_news_date', 'published_date'),
    )


# ==================================================================================
# 9. 옵션 요약 통계 (일별) - CBOE
# Note: 옵션 원본 데이터(options)는 사용자 요청 시 실시간 API 조회로 대체
# ==================================================================================
class OptionsSummary(Base):
    __tablename__ = 'options_summary'

    ticker = Column(String(10), ForeignKey('stocks.ticker', ondelete='CASCADE'), primary_key=True)
    snapshot_date = Column(Date, primary_key=True)

    # Put/Call Ratios
    put_call_ratio_volume = Column(Float)
    put_call_ratio_oi = Column(Float)

    # Totals
    total_call_volume = Column(Integer)
    total_put_volume = Column(Integer)
    total_call_oi = Column(Integer)
    total_put_oi = Column(Integer)

    # IV Averages
    avg_iv_call = Column(Float)
    avg_iv_put = Column(Float)
    avg_iv = Column(Float)

    provider = Column(String(20), default='cboe')
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint('ticker', 'snapshot_date', name='uq_opsum'),
        Index('idx_opsum_ticker', 'ticker'),
    )


# ==================================================================================
# Database Management Functions
# ==================================================================================
def create_database(db_path='data/nasdaq.db'):
    """데이터베이스 생성 및 초기화"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    engine = create_engine(f'sqlite:///{db_path}', echo=False)

    # 외래키 제약조건 활성화
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Drop all tables (fresh start)
    Base.metadata.drop_all(engine)

    # Create all tables
    Base.metadata.create_all(engine)

    print(f"✅ Database created: {db_path}")
    print(f"   Tables: {', '.join(Base.metadata.tables.keys())}")

    return engine


def get_session(db_path='data/nasdaq.db'):
    """데이터베이스 세션 반환"""
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Session = sessionmaker(bind=engine)
    return Session()


def get_table_info(db_path='data/nasdaq.db'):
    """테이블 정보 출력"""
    from sqlalchemy import inspect

    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    inspector = inspect(engine)

    print("\n" + "=" * 80)
    print("DATABASE SCHEMA INFO (v2 - Aligned with OpenBB)")
    print("=" * 80)

    for table_name in inspector.get_table_names():
        print(f"\n[{table_name}]")
        columns = inspector.get_columns(table_name)
        print(f"  Columns ({len(columns)}):")
        for col in columns:
            null_str = "" if col['nullable'] else " NOT NULL"
            pk_str = " (PK)" if col.get('primary_key') else ""
            print(f"    - {col['name']:30s}: {str(col['type']):15s}{null_str}{pk_str}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # 데이터베이스 생성
    engine = create_database('data/nasdaq.db')
    print("\n📊 Database schema v2 created successfully!")

    # 테이블 상세 정보 출력
    get_table_info('data/nasdaq.db')
