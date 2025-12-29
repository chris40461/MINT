"""
Nasdaq 주식 데이터 배치 수집
- OpenBB를 사용하여 나스닥 **주식**(ETF 제외) 데이터 수집
- FRED, yfinance, CBOE, Finviz providers 사용 (SEC 제외)
- SQLite DB에 저장
- tqdm으로 진행상황 표시
- sleep(0.2)로 Rate Limit 회피
"""

from openbb import obb
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import time
from tqdm import tqdm
import os
from dotenv import load_dotenv

from database_schema import (
    Stock, FredMacro, PriceDaily, IncomeStatement, BalanceSheet, CashFlow,
    Fundamentals, News, OptionsSummary, create_database
)

# ==================================================================================
# 설정
# ==================================================================================
load_dotenv()

# OpenBB API 키 로드
FRED_KEY = os.getenv("FRED_API_KEY")
if FRED_KEY:
    obb.user.credentials.fred_api_key = FRED_KEY
    print(f"✅ FRED API Key loaded: {FRED_KEY[:4]}****")

# DB 경로
DB_PATH = 'data/nasdaq.db'

# 데이터 수집 기간
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)  # 1년치

# ==================================================================================
# 나스닥 종목 리스트 가져오기 (ETF 제외, 주식만)
# ==================================================================================
def get_nasdaq_tickers(source='manual', limit=None):
    """
    나스닥 종목 리스트 가져오기 (ETF 제외, 주식만)

    Args:
        source: 'manual' (주요 종목 리스트), 'alphavantage' (전체 나스닥), 'nasdaq_ftp' (NASDAQ FTP)
        limit: 제한할 종목 수 (None = 전체)

    Returns:
        list: 티커 리스트 (주식만, ETF 제외)
    """
    if source == 'manual':
        # 주요 나스닥 주식 10개 (테스트용)
        tickers = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META',  # FAANG
            'NVDA', 'TSLA', 'NFLX', 'AMD', 'INTC'      # Big Tech
        ]

    elif source == 'alphavantage':
        # Alpha Vantage CSV 다운로드 (ETF 제외)
        print("Downloading NASDAQ tickers from Alpha Vantage...")
        url = "https://www.alphavantage.co/query?function=LISTING_STATUS&apikey=demo"
        df = pd.read_csv(url)

        # NASDAQ + Stock only (ETF 제외)
        df = df[
            (df['exchange'] == 'NASDAQ') &
            (df['assetType'] == 'Stock')  # ETF, Fund 제외
        ]

        # Delisted 제외
        df = df[df['status'] == 'Active']

        tickers = df['symbol'].tolist()
        print(f"  → Alpha Vantage: {len(tickers)} stocks (ETF excluded)")

    elif source == 'nasdaq_ftp':
        print("Downloading NASDAQ tickers from NASDAQ FTP...")
        
        try:
            ftp_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
            # 파이프(|)로 구분된 파일 읽기
            df = pd.read_csv(ftp_url, sep='|')
            
            # 1. [데이터 정제] 마지막 행 제거 
            # (이 파일은 항상 마지막 줄에 "File Creation Time: ..." 같은 메타데이터가 들어감)
            df = df[:-1]

            # 2. [타입 안정성] Symbol 컬럼을 무조건 문자열(str)로 변환
            # (여기서 NaN이 있다면 'nan' 문자로 변하겠지만 아래 dropna에서 처리됨)
            df = df.dropna(subset=['Symbol']) # Symbol이 빈 곳 삭제
            df['Symbol'] = df['Symbol'].astype(str)

            # 3. [기본 필터] ETF 및 테스트 종목 제외
            # ETF 컬럼이 'N' 이고, Test Issue 컬럼이 'N' 인 것만 남김
            df = df[
                (df['ETF'] == 'N') & 
                (df['Test Issue'] == 'N')
            ]

            # 4. [심화 필터] '회사 이름' 기반 노이즈 제거 (AACBR 같은 종목 방지)
            # 제거할 키워드 목록 (대소문자 무시하고 검색)
            exclusion_keywords = [
                'Warrant', ' Wt',      # 신주인수권 (위험도 높음, 데이터 부실)
                'Right', ' Rt',        # 권리 (AACBR 원인)
                'Unit', ' Ut',         # 유닛 (보통주+워런트 결합)
                'Preferred', ' Pf',    # 우선주 (보통주 데이터 분석 목적이면 제외 권장)
                'Debenture', ' Note'   # 채권형 상품
            ]
            
            # Security Name 컬럼에서 위 키워드가 하나라도 포함되면 제거 (mask 생성)
            # case=False: 대소문자 구분 안 함
            mask = df['Security Name'].str.contains('|'.join(exclusion_keywords), case=False, na=False)
            
            # 제외 키워드가 포함되지 않은(~mask) 행만 선택
            df_clean = df[~mask]

            # 로그 출력 (필터링 결과 확인용)
            removed_count = len(df) - len(df_clean)
            print(f"  → Raw count: {len(df)}, Filtered(W/R/U/Pf): -{removed_count}")

            # 최종 리스트 추출
            tickers = df_clean['Symbol'].tolist()
            print(f"  → NASDAQ FTP: {len(tickers)} clean stocks (ETF excluded)")

        except Exception as e:
            print(f"❌ FTP Download failed: {e}")
            # FTP 실패 시 빈 리스트 혹은 백업 로직
            return []

    # 중복 제거 및 정렬
    tickers = sorted(list(set(tickers)))

    # 제한
    if limit:
        tickers = tickers[:limit]

    print(f"✅ Loaded {len(tickers)} NASDAQ stocks (ETF excluded, source: {source})")
    return tickers


# ==================================================================================
# FRED 거시경제 데이터 수집
# ==================================================================================
def collect_fred_data(session):
    """FRED 거시경제 지표 수집 (종목 무관)"""
    print("\n" + "=" * 80)
    print("  FRED 거시경제 데이터 수집")
    print("=" * 80)

    indicators = {
        'DGS10': 'dgs10',
        'DGS2': 'dgs2',
        'FEDFUNDS': 'fed_funds_rate',
        'CPIAUCSL': 'cpi',
        'UNRATE': 'unemployment_rate'
    }

    fred_data = {}

    for symbol, field in tqdm(indicators.items(), desc="FRED Indicators"):
        try:
            # FRED API requires date string
            start_date_str = (END_DATE - timedelta(days=400)).strftime('%Y-%m-%d')
            print(f"\n  Fetching {symbol} from {start_date_str}...")

            result = obb.economy.fred_series(
                symbol=symbol,
                start_date=start_date_str,
                provider='fred'
            )

            if hasattr(result, 'to_dataframe'):
                df = result.to_dataframe()
                print(f"    → Got {len(df)} rows, columns: {df.columns.tolist()}")

                # FRED data is usually in the last column or 'value' column
                if not df.empty:
                    # Try 'value' column first
                    if 'value' in df.columns:
                        valid_data = df['value'].dropna()
                    else:
                        # Use the last column (usually the data column)
                        valid_data = df.iloc[:, -1].dropna()
                        print(f"    → Using column '{df.columns[-1]}' as data column")

                    if not valid_data.empty:
                        fred_data[field] = valid_data
                        print(f"    → Saved {len(valid_data)} valid data points")
                    else:
                        print(f"    → All values are NaN")
                else:
                    print(f"    → DataFrame is empty")
            else:
                print(f"    → No to_dataframe method")

            time.sleep(0.2)
        except Exception as e:
            print(f"  ⚠️ {symbol} failed: {e}")

    # 데이터 병합 및 저장 (에러가 발생해도 수집된 데이터는 저장)
    print(f"\n  Collected data for {len(fred_data)} indicators: {list(fred_data.keys())}")

    if len(fred_data) >= 2:  # 최소 2개 이상 지표가 있으면 저장
        # 최신 날짜 찾기
        latest_dates = {k: v.index[-1] for k, v in fred_data.items()}
        common_date = max(latest_dates.values())
        print(f"  Latest date: {common_date}")

        # CPI YoY 계산
        cpi_yoy = None
        if 'cpi' in fred_data:
            cpi_series = fred_data['cpi']
            if len(cpi_series) >= 13:
                curr = cpi_series.iloc[-1]
                prev = cpi_series.iloc[-13]
                cpi_yoy = ((curr / prev) - 1) * 100
                print(f"  CPI YoY: {cpi_yoy:.2f}%")

        # Yield Spread 계산
        yield_spread = None
        if 'dgs10' in fred_data and 'dgs2' in fred_data:
            yield_spread = fred_data['dgs10'].iloc[-1] - fred_data['dgs2'].iloc[-1]
            print(f"  Yield Spread: {yield_spread:.2f}")

        # DB 저장 (Timestamp → date 변환)
        common_date_obj = common_date.date() if hasattr(common_date, 'date') else common_date

        fred_macro = FredMacro(
            date=common_date_obj,
            dgs10=fred_data.get('dgs10', pd.Series([None])).iloc[-1],
            dgs2=fred_data.get('dgs2', pd.Series([None])).iloc[-1],
            yield_spread=yield_spread,
            fed_funds_rate=fred_data.get('fed_funds_rate', pd.Series([None])).iloc[-1],
            cpi_yoy=cpi_yoy,
            unemployment_rate=fred_data.get('unemployment_rate', pd.Series([None])).iloc[-1]
        )

        print(f"\n  Saving to DB...")
        print(f"    Date: {common_date_obj}")
        print(f"    DGS10: {fred_macro.dgs10}")
        print(f"    DGS2: {fred_macro.dgs2}")
        print(f"    Yield Spread: {fred_macro.yield_spread}")
        print(f"    Fed Funds: {fred_macro.fed_funds_rate}")
        print(f"    CPI YoY: {fred_macro.cpi_yoy}")
        print(f"    Unemployment: {fred_macro.unemployment_rate}")

        # Upsert
        existing = session.query(FredMacro).filter_by(date=common_date_obj).first()
        if existing:
            print(f"  Deleting existing record for {common_date_obj}")
            session.delete(existing)

        session.add(fred_macro)
        session.commit()
        print(f"✅ FRED data saved for {common_date_obj}")
    else:
        print("  ⚠️ No FRED data collected! Check API key and network.")


# ==================================================================================
# 개별 종목 데이터 수집
# ==================================================================================
def collect_stock_data(ticker, session):
    """개별 종목 데이터 수집"""
    results = {'ticker': ticker, 'success': {}, 'errors': {}}

    # 1. Price Daily (yfinance)
    try:
        price_result = obb.equity.price.historical(
            symbol=ticker,
            start_date=START_DATE.strftime('%Y-%m-%d'),
            end_date=END_DATE.strftime('%Y-%m-%d'),
            provider='yfinance'
        )

        if hasattr(price_result, 'to_dataframe'):
            df = price_result.to_dataframe()
            if not df.empty:
                for date_idx, row in df.iterrows():
                    price_obj = PriceDaily(
                        ticker=ticker,
                        date=date_idx.date() if hasattr(date_idx, 'date') else date_idx,
                        open=row.get('open'),
                        high=row.get('high'),
                        low=row.get('low'),
                        close=row.get('close'),
                        volume=int(row.get('volume')) if row.get('volume') is not None else None,
                        provider='yfinance'
                    )
                    session.merge(price_obj)  # merge = upsert

                results['success']['price'] = len(df)
                session.commit()

        time.sleep(0.2)
    except Exception as e:
        results['errors']['price'] = str(e)[:100]

    # 2. Income Statement (yfinance)
    try:
        income_result = obb.equity.fundamental.income(
            symbol=ticker,
            period='annual',
            limit=5,
            provider='yfinance'
        )

        if hasattr(income_result, 'to_dataframe'):
            df = income_result.to_dataframe()
            if not df.empty:
                for idx, row in df.iterrows():
                    # Extract fiscal_date from period_ending or index
                    fiscal_date = row.get('period_ending')
                    if fiscal_date is None:
                        fiscal_date = idx.date() if hasattr(idx, 'date') else idx

                    income_obj = IncomeStatement(
                        ticker=ticker,
                        period='annual',
                        fiscal_date=fiscal_date,
                        # Core Financials (schema v2)
                        total_revenue=row.get('total_revenue') or row.get('operating_revenue'),
                        cost_of_revenue=row.get('cost_of_revenue'),
                        gross_profit=row.get('gross_profit'),
                        operating_income=row.get('operating_income'),
                        net_income=row.get('net_income'),
                        # Important Metrics
                        ebitda=row.get('ebitda'),
                        operating_expense=row.get('operating_expense'),
                        # Per Share
                        eps_basic=row.get('basic_earnings_per_share'),
                        eps_diluted=row.get('diluted_earnings_per_share'),
                        # R&D and SG&A
                        rd_expense=row.get('research_and_development_expense'),
                        sga_expense=row.get('selling_general_and_admin_expense'),
                        provider='yfinance'
                    )
                    session.merge(income_obj)

                results['success']['income'] = len(df)
                session.commit()

        time.sleep(0.2)
    except Exception as e:
        results['errors']['income'] = str(e)[:100]

    # 3. Balance Sheet (yfinance)
    try:
        balance_result = obb.equity.fundamental.balance(
            symbol=ticker,
            period='annual',
            limit=5,
            provider='yfinance'
        )

        if hasattr(balance_result, 'to_dataframe'):
            df = balance_result.to_dataframe()
            if not df.empty:
                for idx, row in df.iterrows():
                    # Extract fiscal_date
                    fiscal_date = row.get('period_ending')
                    if fiscal_date is None:
                        fiscal_date = idx.date() if hasattr(idx, 'date') else idx

                    balance_obj = BalanceSheet(
                        ticker=ticker,
                        period='annual',
                        fiscal_date=fiscal_date,
                        # Core Financials (schema v2)
                        total_assets=row.get('total_assets'),
                        total_current_assets=row.get('total_current_assets'),
                        cash_and_cash_equivalents=row.get('cash_and_cash_equivalents'),
                        # Liabilities
                        total_liabilities=(
                            row.get('total_liabilities_net_minority_interest') or
                            row.get('total_liabilities')
                        ),
                        current_liabilities=row.get('current_liabilities'),
                        total_debt=row.get('total_debt'),
                        # Equity
                        total_equity=(
                            row.get('common_stock_equity') or
                            row.get('total_equity_non_controlling_interests') or
                            row.get('total_equity')
                        ),
                        retained_earnings=row.get('retained_earnings'),
                        provider='yfinance'
                    )
                    session.merge(balance_obj)

                results['success']['balance'] = len(df)
                session.commit()

        time.sleep(0.2)
    except Exception as e:
        results['errors']['balance'] = str(e)[:100]

    # 4. Cash Flow (yfinance)
    try:
        cash_result = obb.equity.fundamental.cash(
            symbol=ticker,
            period='annual',
            limit=5,
            provider='yfinance'
        )

        if hasattr(cash_result, 'to_dataframe'):
            df = cash_result.to_dataframe()
            if not df.empty:
                for idx, row in df.iterrows():
                    # Extract fiscal_date
                    fiscal_date = row.get('period_ending')
                    if fiscal_date is None:
                        fiscal_date = idx.date() if hasattr(idx, 'date') else idx

                    # Core Cash Flows (schema v2)
                    ocf = row.get('operating_cash_flow')
                    capex = row.get('capital_expenditure')

                    # Free Cash Flow: try to get from data, or calculate
                    fcf = row.get('free_cash_flow')
                    if fcf is None and ocf is not None and capex is not None:
                        fcf = ocf + capex  # capex is negative, so add it

                    cash_obj = CashFlow(
                        ticker=ticker,
                        period='annual',
                        fiscal_date=fiscal_date,
                        # Core Cash Flows
                        operating_cash_flow=ocf,
                        investing_cash_flow=row.get('investing_cash_flow'),
                        financing_cash_flow=row.get('financing_cash_flow'),
                        # Important Items (schema v2)
                        capital_expenditure=capex,
                        cash_dividends_paid=(
                            row.get('cash_dividends_paid') or
                            row.get('common_stock_dividend_paid')
                        ),
                        free_cash_flow=fcf,
                        provider='yfinance'
                    )
                    session.merge(cash_obj)

                results['success']['cash_flow'] = len(df)
                session.commit()

        time.sleep(0.2)
    except Exception as e:
        results['errors']['cash_flow'] = str(e)[:100]

    # 5. Fundamentals (Finviz) - ALL 21 columns from schema v2
    try:
        finviz_result = obb.equity.fundamental.metrics(
            symbol=ticker,
            provider='finviz'
        )

        if hasattr(finviz_result, 'to_dataframe'):
            df = finviz_result.to_dataframe()
            if not df.empty:
                row = df.iloc[0]

                # Map all 21 columns exactly as they appear in Finviz output
                fund_obj = Fundamentals(
                    ticker=ticker,
                    snapshot_date=END_DATE.date(),
                    # Valuation Ratios
                    market_cap=row.get('market_cap'),
                    pe_ratio=row.get('pe_ratio'),
                    foward_pe=row.get('foward_pe'),  # IMPORTANT: typo exists in Finviz!
                    price_to_sales=row.get('price_to_sales'),
                    price_to_book=row.get('price_to_book'),
                    eps=row.get('eps'),
                    book_value_per_share=row.get('book_value_per_share'),
                    # Profitability
                    return_on_equity=row.get('return_on_equity'),
                    return_on_assets=row.get('return_on_assets'),
                    profit_margin=row.get('profit_margin'),
                    operating_margin=row.get('operating_margin'),
                    gross_margin=row.get('gross_margin'),
                    # Financial Health
                    debt_to_equity=row.get('debt_to_equity'),
                    long_term_debt_to_equity=row.get('long_term_debt_to_equity'),
                    current_ratio=row.get('current_ratio'),
                    quick_ratio=row.get('quick_ratio'),
                    # Other
                    payout_ratio=row.get('payout_ratio'),
                    provider='finviz'
                )
                session.merge(fund_obj)
                session.commit()

                results['success']['fundamentals'] = 1

        time.sleep(0.2)
    except Exception as e:
        results['errors']['fundamentals'] = str(e)[:100]

    # 6. News (yfinance)
    try:
        news_result = obb.news.company(
            symbol=ticker,
            limit=20,
            provider='yfinance'
        )

        if hasattr(news_result, 'to_dataframe'):
            df = news_result.to_dataframe()
            if not df.empty:
                for idx, row in df.iterrows():
                    # 날짜는 index에 있음 (test_columns 확인: Name: 2025-11-18 18:11:14+00:00)
                    published_date = idx
                    if hasattr(idx, 'date'):
                        published_date = idx  # Already datetime

                    news_obj = News(
                        ticker=ticker,
                        published_date=published_date,
                        title=row.get('title'),
                        url=row.get('url'),
                        source=row.get('source'),
                        provider='yfinance'
                    )
                    session.add(news_obj)

                results['success']['news'] = len(df)
                session.commit()

        time.sleep(0.2)
    except Exception as e:
        results['errors']['news'] = str(e)[:100]

    return results


# ==================================================================================
# Stock 마스터 테이블 업데이트
# ==================================================================================
def update_stock_master(ticker, session):
    """
    Stock 마스터 테이블 업데이트

    yfinance profile API 사용:
    - name: company name (e.g., 'Apple Inc.')
    - sector: sector (e.g., 'Technology')
    - industry_category: industry (e.g., 'Consumer Electronics')
    - market_cap: market capitalization
    """
    # Retry logic for Yahoo Finance 401 errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # yfinance에서 company profile 가져오기
            profile_result = obb.equity.profile(
                symbol=ticker,
                provider='yfinance'
            )

            if hasattr(profile_result, 'to_dataframe'):
                df = profile_result.to_dataframe()
                if not df.empty:
                    row = df.iloc[0]

                    stock_obj = Stock(
                        ticker=ticker,
                        name=row.get('name'),  # yfinance profile에 있음
                        sector=row.get('sector'),  # yfinance profile에 있음
                        industry=row.get('industry_category'),  # yfinance에서는 'industry_category'
                        market_cap=row.get('market_cap'),
                        exchange='NASDAQ',
                        last_updated=datetime.now()
                    )
                    session.merge(stock_obj)
                    session.commit()
                    time.sleep(0.2)
                    return True

            time.sleep(0.2)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                continue
            print(f"  ⚠️ Stock master update failed for {ticker}: {e}")
            return False

    return False


# ==================================================================================
# CBOE Options 데이터 수집
# ==================================================================================
def collect_options_data(ticker, session):
    """
    CBOE 옵션 요약 통계 수집 (options_summary만 저장)
    Note: 개별 옵션 계약(options)은 사용자 요청 시 실시간 조회
    """
    try:
        options_result = obb.derivatives.options.chains(
            symbol=ticker,
            provider='cboe'
        )

        if hasattr(options_result, 'to_dataframe'):
            df = options_result.to_dataframe()
            if not df.empty:
                snapshot_date = END_DATE.date()

                # 요약 통계 계산
                calls = df[df['option_type'] == 'call']
                puts = df[df['option_type'] == 'put']

                total_call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
                total_put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0
                total_call_oi = calls['open_interest'].sum() if 'open_interest' in calls.columns else 0
                total_put_oi = puts['open_interest'].sum() if 'open_interest' in puts.columns else 0

                # Put/Call Ratios
                pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else None
                pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else None

                # IV Averages
                avg_iv_call = calls['implied_volatility'].mean() if 'implied_volatility' in calls.columns else None
                avg_iv_put = puts['implied_volatility'].mean() if 'implied_volatility' in puts.columns else None
                avg_iv = df['implied_volatility'].mean() if 'implied_volatility' in df.columns else None

                summary_obj = OptionsSummary(
                    ticker=ticker,
                    snapshot_date=snapshot_date,
                    put_call_ratio_volume=pcr_volume,
                    put_call_ratio_oi=pcr_oi,
                    total_call_volume=int(total_call_volume),
                    total_put_volume=int(total_put_volume),
                    total_call_oi=int(total_call_oi),
                    total_put_oi=int(total_put_oi),
                    avg_iv_call=avg_iv_call,
                    avg_iv_put=avg_iv_put,
                    avg_iv=avg_iv,
                    provider='cboe'
                )
                session.merge(summary_obj)
                session.commit()

                return len(df)

        time.sleep(0.2)
    except Exception as e:
        # 작은 종목들은 옵션이 없는 게 정상 (조용히 실패 처리)
        return 0


# ==================================================================================
# 메인 실행
# ==================================================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          Nasdaq Stock Data Batch Collection (Stocks Only, No ETF)           ║
║                DB: {DB_PATH:50s}   ║
║                Period: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # 1. DB 생성/연결
    if not os.path.exists(DB_PATH):
        print("Creating database...")
        create_database(DB_PATH)
    else:
        print(f"Using existing database: {DB_PATH}")

    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. FRED 거시경제 데이터 수집 (1회만, 글로벌 데이터)
    print("\n[Step 2/4] Collecting FRED macroeconomic data...")
    collect_fred_data(session)
    print("✅ FRED data saved to DB")

    # 3. 나스닥 종목 리스트 (ETF 제외, 주식만)
    print("\n[Step 3/4] Loading NASDAQ ticker list...")
    #tickers = get_nasdaq_tickers(source='manual', limit=10)  # 테스트용
    tickers = get_nasdaq_tickers(source='nasdaq_ftp', limit=None)  # 전체 수집
    #tickers = get_nasdaq_tickers(source='alphavantage', limit=None)  # Alpha Vantage 사용

    # 4. 개별 종목 데이터 수집
    print(f"\n[Step 4/4] Collecting {len(tickers)} stocks...")
    print("=" * 80)
    print("Note: Options collection 실패는 정상 (작은 종목은 CBOE 옵션 없음)")
    print("=" * 80)

    success_count = 0
    error_count = 0
    options_count = 0
    start_time = time.time()

    for idx, ticker in enumerate(tqdm(tickers, desc="Collecting stocks"), 1):
        try:
            # 4.1 Stock 마스터 테이블 업데이트
            update_stock_master(ticker, session)

            # 4.2 일반 재무/가격 데이터 수집
            results = collect_stock_data(ticker, session)

            # 4.3 Options 데이터 수집 (CBOE) - 실패 시 조용히 처리
            options_cnt = collect_options_data(ticker, session)
            if options_cnt > 0:
                options_count += 1
                results['success']['options'] = options_cnt

            if results['success']:
                success_count += 1
            if results['errors']:
                error_count += 1

            # 100개마다 중간 통계 출력
            if idx % 100 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining = (len(tickers) - idx) * avg_time
                tqdm.write(
                    f"\n📊 중간 통계 ({idx}/{len(tickers)}): "
                    f"성공 {success_count}, 오류 {error_count}, 옵션 {options_count} | "
                    f"남은 시간: {remaining/60:.1f}분\n"
                )

        except Exception as e:
            error_count += 1
            tqdm.write(f"  ❌ {ticker} failed: {str(e)[:80]}")

        time.sleep(0.2)  # Rate limit 회피

    # 5. 요약
    session.close()

    print("\n" + "=" * 80)
    print("  수집 완료")
    print("=" * 80)
    print(f"  총 종목: {len(tickers)}")
    print(f"  성공: {success_count}")
    print(f"  오류: {error_count}")
    print(f"  옵션 수집: {options_count} 종목")
    print(f"  DB 경로: {DB_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
