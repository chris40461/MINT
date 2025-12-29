"""
Retry Failed Stocks - NASDAQ FTP 리스트 vs DB 비교하여 누락된 종목 재수집
- NASDAQ FTP에서 받은 원래 ticker 리스트 로드
- DB의 stocks 테이블과 비교
- DB에 없는 종목들만 재시도 (강화된 retry 로직)
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
    Stock, PriceDaily, IncomeStatement, BalanceSheet, CashFlow,
    Fundamentals, News, OptionsSummary
)

# ==================================================================================
# 설정
# ==================================================================================
load_dotenv()

DB_PATH = 'data/nasdaq.db'
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)

# OpenBB API 키 로드
FRED_API_KEY = os.getenv('FRED_API_KEY')
if FRED_API_KEY:
    obb.user.credentials.fred_api_key = FRED_API_KEY


# ==================================================================================
# NASDAQ FTP에서 ticker 리스트 로드 (batch_collect_nasdaq.py와 동일)
# ==================================================================================
def get_nasdaq_tickers_from_ftp():
    """
    NASDAQ FTP에서 ticker 리스트 로드
    (batch_collect_nasdaq.py의 로직과 동일)
    """
    print("\n[Step 1] Loading NASDAQ tickers from FTP...")

    try:
        ftp_url = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"
        df = pd.read_csv(ftp_url, sep='|')

        # 1. 마지막 행 제거 (메타데이터)
        df = df[:-1]

        # 2. Symbol 컬럼 문자열 변환
        df = df.dropna(subset=['Symbol'])
        df['Symbol'] = df['Symbol'].astype(str)

        # 3. ETF 및 테스트 종목 제외
        df = df[
            (df['ETF'] == 'N') &
            (df['Test Issue'] == 'N')
        ]

        # 4. Warrant, Right, Unit, Preferred, Debenture 제외
        exclusion_keywords = [
            'Warrant', ' Wt',
            'Right', ' Rt',
            'Unit', ' Ut',
            'Preferred', ' Pf',
            'Debenture', ' Note'
        ]

        mask = df['Security Name'].str.contains('|'.join(exclusion_keywords), case=False, na=False)
        df_clean = df[~mask]

        removed_count = len(df) - len(df_clean)
        print(f"  → Raw count: {len(df)}, Filtered(W/R/U/Pf): -{removed_count}")

        tickers = sorted(df_clean['Symbol'].tolist())
        print(f"  ✅ NASDAQ FTP: {len(tickers)} clean stocks (ETF excluded)")

        return tickers

    except Exception as e:
        print(f"  ❌ FTP Download failed: {e}")
        return []


# ==================================================================================
# DB에 있는 ticker 리스트 로드
# ==================================================================================
def get_db_tickers(session):
    """DB의 stocks 테이블에서 ticker 리스트 로드"""
    print("\n[Step 2] Loading tickers from DB...")

    db_tickers = [row[0] for row in session.query(Stock.ticker).all()]
    print(f"  ✅ DB stocks table: {len(db_tickers)} tickers")

    return db_tickers


# ==================================================================================
# 누락된 ticker 찾기
# ==================================================================================
def find_missing_tickers(ftp_tickers, db_tickers):
    """FTP 리스트와 DB 비교하여 누락된 ticker 찾기"""
    print("\n[Step 3] Comparing FTP list vs DB...")

    ftp_set = set(ftp_tickers)
    db_set = set(db_tickers)

    missing = sorted(list(ftp_set - db_set))

    print(f"  FTP 원본: {len(ftp_set)} 종목")
    print(f"  DB 저장: {len(db_set)} 종목")
    print(f"  ✅ 누락: {len(missing)} 종목")

    if len(missing) <= 20:
        print(f"  누락 종목: {', '.join(missing)}")

    return missing


# ==================================================================================
# 재시도 로직 (batch_collect_nasdaq.py와 동일하지만 강화)
# ==================================================================================
def collect_stock_data(ticker, session):
    """개별 종목 데이터 수집 (재시도 로직 강화)"""
    results = {'ticker': ticker, 'success': {}, 'errors': {}}

    # 재시도 설정 (5회, exponential backoff)
    max_retries = 5
    import random

    # 1. Price Daily
    for attempt in range(max_retries):
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
                        session.merge(price_obj)
                    results['success']['price'] = len(df)
                    session.commit()
                    break
            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 2)
                time.sleep(wait)
                continue
            results['errors']['price'] = str(e)[:100]

    # 2. Income Statement
    for attempt in range(max_retries):
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
                        fiscal_date = row.get('period_ending')
                        if fiscal_date is None:
                            fiscal_date = idx.date() if hasattr(idx, 'date') else idx

                        income_obj = IncomeStatement(
                            ticker=ticker,
                            period='annual',
                            fiscal_date=fiscal_date,
                            total_revenue=row.get('total_revenue') or row.get('operating_revenue'),
                            cost_of_revenue=row.get('cost_of_revenue'),
                            gross_profit=row.get('gross_profit'),
                            operating_income=row.get('operating_income'),
                            net_income=row.get('net_income'),
                            ebitda=row.get('ebitda'),
                            operating_expense=row.get('operating_expense'),
                            eps_basic=row.get('basic_earnings_per_share'),
                            eps_diluted=row.get('diluted_earnings_per_share'),
                            rd_expense=row.get('research_and_development_expense'),
                            sga_expense=row.get('selling_general_and_admin_expense'),
                            provider='yfinance'
                        )
                        session.merge(income_obj)
                    results['success']['income'] = len(df)
                    session.commit()
                    break
            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 2)
                time.sleep(wait)
                continue
            results['errors']['income'] = str(e)[:100]

    # 3. Balance Sheet
    for attempt in range(max_retries):
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
                        fiscal_date = row.get('period_ending')
                        if fiscal_date is None:
                            fiscal_date = idx.date() if hasattr(idx, 'date') else idx

                        balance_obj = BalanceSheet(
                            ticker=ticker,
                            period='annual',
                            fiscal_date=fiscal_date,
                            total_assets=row.get('total_assets'),
                            total_current_assets=row.get('total_current_assets'),
                            cash_and_cash_equivalents=row.get('cash_and_cash_equivalents'),
                            total_liabilities=(
                                row.get('total_liabilities_net_minority_interest') or
                                row.get('total_liabilities')
                            ),
                            current_liabilities=row.get('current_liabilities'),
                            total_debt=row.get('total_debt'),
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
                    break
            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 2)
                time.sleep(wait)
                continue
            results['errors']['balance'] = str(e)[:100]

    # 4. Cash Flow
    for attempt in range(max_retries):
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
                        fiscal_date = row.get('period_ending')
                        if fiscal_date is None:
                            fiscal_date = idx.date() if hasattr(idx, 'date') else idx

                        ocf = row.get('operating_cash_flow')
                        capex = row.get('capital_expenditure')
                        fcf = row.get('free_cash_flow')
                        if fcf is None and ocf is not None and capex is not None:
                            fcf = ocf + capex

                        cash_obj = CashFlow(
                            ticker=ticker,
                            period='annual',
                            fiscal_date=fiscal_date,
                            operating_cash_flow=ocf,
                            investing_cash_flow=row.get('investing_cash_flow'),
                            financing_cash_flow=row.get('financing_cash_flow'),
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
                    break
            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 2)
                time.sleep(wait)
                continue
            results['errors']['cash_flow'] = str(e)[:100]

    # 5. Fundamentals (Finviz)
    for attempt in range(max_retries):
        try:
            finviz_result = obb.equity.fundamental.metrics(
                symbol=ticker,
                provider='finviz'
            )

            if hasattr(finviz_result, 'to_dataframe'):
                df = finviz_result.to_dataframe()
                if not df.empty:
                    row = df.iloc[0]

                    fund_obj = Fundamentals(
                        ticker=ticker,
                        snapshot_date=END_DATE.date(),
                        market_cap=row.get('market_cap'),
                        pe_ratio=row.get('pe_ratio'),
                        foward_pe=row.get('foward_pe'),
                        price_to_sales=row.get('price_to_sales'),
                        price_to_book=row.get('price_to_book'),
                        eps=row.get('eps'),
                        book_value_per_share=row.get('book_value_per_share'),
                        return_on_equity=row.get('return_on_equity'),
                        return_on_assets=row.get('return_on_assets'),
                        profit_margin=row.get('profit_margin'),
                        operating_margin=row.get('operating_margin'),
                        gross_margin=row.get('gross_margin'),
                        debt_to_equity=row.get('debt_to_equity'),
                        long_term_debt_to_equity=row.get('long_term_debt_to_equity'),
                        current_ratio=row.get('current_ratio'),
                        quick_ratio=row.get('quick_ratio'),
                        payout_ratio=row.get('payout_ratio'),
                        provider='finviz'
                    )
                    session.merge(fund_obj)
                    session.commit()
                    results['success']['fundamentals'] = 1
                    break
            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 2)
                time.sleep(wait)
                continue
            results['errors']['fundamentals'] = str(e)[:100]

    # 6. News (yfinance)
    for attempt in range(max_retries):
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
                        published_date = idx
                        if hasattr(idx, 'date'):
                            published_date = idx

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
                    break
            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 2)
                time.sleep(wait)
                continue
            results['errors']['news'] = str(e)[:100]

    return results


def update_stock_master(ticker, session):
    """Stock 마스터 테이블 업데이트 (강화된 재시도)"""
    max_retries = 5
    import random

    for attempt in range(max_retries):
        try:
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
                        name=row.get('name'),
                        sector=row.get('sector'),
                        industry=row.get('industry_category'),
                        market_cap=row.get('market_cap'),
                        exchange='NASDAQ',
                        last_updated=datetime.now()
                    )
                    session.merge(stock_obj)
                    session.commit()
                    time.sleep(0.3)
                    return True

            time.sleep(0.3)
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 3)
                time.sleep(wait)
                continue
            print(f"  ⚠️ Stock master failed for {ticker}: {str(e)[:60]}")
            return False

    return False


def collect_options_data(ticker, session):
    """
    CBOE 옵션 요약 통계 수집 (조용히 실패 처리)
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

                pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else None
                pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else None

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

        time.sleep(0.3)
    except Exception as e:
        # 작은 종목들은 옵션이 없는 게 정상
        return 0


# ==================================================================================
# 메인 실행
# ==================================================================================
def main():
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         Retry Failed Stocks - FTP List vs DB Comparison (재수집)            ║
║                DB: {DB_PATH:50s}   ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

    # 1. DB 연결
    engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 2. FTP에서 원본 ticker 리스트 로드
    ftp_tickers = get_nasdaq_tickers_from_ftp()
    if not ftp_tickers:
        print("❌ FTP 티커 로드 실패")
        return

    # 3. DB에서 ticker 리스트 로드
    db_tickers = get_db_tickers(session)

    # 4. 누락된 ticker 찾기
    missing_tickers = find_missing_tickers(ftp_tickers, db_tickers)

    if not missing_tickers:
        print("\n✅ 모든 종목이 DB에 저장되어 있습니다!")
        session.close()
        return

    # 5. 재수집 시작
    print(f"\n[Step 4] 재수집 시작: {len(missing_tickers)} 종목")
    print("=" * 80)

    success_count = 0
    error_count = 0
    options_count = 0
    start_time = time.time()

    for idx, ticker in enumerate(tqdm(missing_tickers, desc="Retrying"), 1):
        try:
            # Stock 마스터 업데이트
            update_stock_master(ticker, session)

            # 재무/가격 데이터 수집
            results = collect_stock_data(ticker, session)

            # Options 데이터 수집
            options_cnt = collect_options_data(ticker, session)
            if options_cnt > 0:
                options_count += 1
                results['success']['options'] = options_cnt

            if results['success']:
                success_count += 1
            if results['errors']:
                error_count += 1

            # 20개마다 중간 통계
            if idx % 20 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                remaining = (len(missing_tickers) - idx) * avg_time
                tqdm.write(
                    f"\n📊 중간 통계 ({idx}/{len(missing_tickers)}): "
                    f"성공 {success_count}, 오류 {error_count}, 옵션 {options_count} | "
                    f"남은 시간: {remaining/60:.1f}분\n"
                )

        except Exception as e:
            error_count += 1
            tqdm.write(f"  ❌ {ticker} failed: {str(e)[:80]}")

        time.sleep(0.3)

    # 6. 최종 요약
    session.close()

    print("\n" + "=" * 80)
    print("  재수집 완료")
    print("=" * 80)
    print(f"  재시도 종목: {len(missing_tickers)}")
    print(f"  성공: {success_count}")
    print(f"  오류: {error_count}")
    print(f"  옵션 수집: {options_count} 종목")
    print(f"  DB 경로: {DB_PATH}")
    print("=" * 80)

    # 7. 재검증
    print("\n[재검증] FTP vs DB 재비교...")
    session = Session()
    db_tickers_after = get_db_tickers(session)
    missing_after = find_missing_tickers(ftp_tickers, db_tickers_after)
    session.close()

    print(f"\n  재수집 전 누락: {len(missing_tickers)} 종목")
    print(f"  재수집 후 누락: {len(missing_after)} 종목")
    print(f"  ✅ 복구: {len(missing_tickers) - len(missing_after)} 종목")

    if len(missing_after) > 0 and len(missing_after) <= 20:
        print(f"  아직 누락: {', '.join(missing_after)}")


if __name__ == "__main__":
    main()
