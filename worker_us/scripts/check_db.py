"""
DB 데이터 확인 스크립트
"""

from sqlalchemy import create_engine, text
import pandas as pd

DB_PATH = 'data/nasdaq.db'

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)

print("=" * 80)
print("  DATABASE STATISTICS")
print("=" * 80)

with engine.connect() as conn:
    # 1. 각 테이블 row count (9 tables, options 제외)
    tables = [
        'stocks', 'fred_macro', 'price_daily', 'income_statement',
        'balance_sheet', 'cash_flow', 'fundamentals', 'news',
        'options_summary'
    ]

    print("\n[Table Row Counts]")
    for table in tables:
        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        count = result.scalar()
        print(f"  {table:20s}: {count:,} rows")

    # 2. FRED 최신 데이터
    print("\n[FRED Latest Data]")
    fred_df = pd.read_sql("SELECT * FROM fred_macro ORDER BY date DESC LIMIT 1", conn)
    if not fred_df.empty:
        print(fred_df.T)

    # 3. Price Daily 샘플 (AAPL 최근 5일)
    print("\n[Price Daily Sample - AAPL Last 5 Days]")
    price_df = pd.read_sql(
        "SELECT * FROM price_daily WHERE ticker='AAPL' ORDER BY date DESC LIMIT 5",
        conn
    )
    if not price_df.empty:
        print(price_df)

    # 4. Fundamentals 샘플
    print("\n[Fundamentals Sample - Top 5 by PE Ratio]")
    fund_df = pd.read_sql(
        """
        SELECT ticker, snapshot_date, pe_ratio, price_to_book,
               return_on_equity, debt_to_equity, profit_margin
        FROM fundamentals
        WHERE pe_ratio IS NOT NULL
        ORDER BY pe_ratio
        LIMIT 5
        """,
        conn
    )
    if not fund_df.empty:
        print(fund_df)

    # 5. News 통계
    print("\n[News Statistics]")
    news_stats = pd.read_sql(
        """
        SELECT ticker, COUNT(*) as news_count
        FROM news
        GROUP BY ticker
        ORDER BY news_count DESC
        LIMIT 10
        """,
        conn
    )
    if not news_stats.empty:
        print(news_stats)

print("\n" + "=" * 80)
