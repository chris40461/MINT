"""
통합 테스트: Collector + Loader (병렬 처리)
전체 ETL 파이프라인 (Extract → Transform → Load) 테스트
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from concurrent.futures import ThreadPoolExecutor, as_completed

from collectors.fred_collector import FREDCollector
from collectors.price_collector import PriceCollector
from collectors.news_collector import NewsCollector
from collectors.fundamentals_collector import FundamentalsCollector
from collectors.options_collector import OptionsCollector

from loaders.fred_loader import FredLoader
from loaders.price_loader import PriceLoader
from loaders.news_loader import NewsLoader
from loaders.fundamentals_loader import FundamentalsLoader
from loaders.options_loader import OptionsLoader

from models.connection import get_db_session


def test_fred_pipeline():
    """FRED ETL 파이프라인 테스트"""
    print("\n" + "=" * 80)
    print("[Test 1] FRED Pipeline (Collector → Loader → DB)")
    print("=" * 80)

    # Extract
    collector = FREDCollector()
    data = collector.collect()

    if not data:
        print("✗ FRED collection failed")
        return False

    print(f"✓ FRED data collected: {data['date']}")

    # Load
    loader = FredLoader()
    with get_db_session() as session:
        success = loader.load(data, session)

    if success:
        print(f"✓ FRED data loaded to DB")
        return True
    else:
        print("✗ FRED load failed")
        return False


def test_single_ticker_parallel():
    """단일 종목 모든 데이터 병렬 수집 및 적재"""
    print("\n" + "=" * 80)
    print("[Test 2] Single Ticker All Data Pipeline (Parallel)")
    print("=" * 80)

    ticker = 'AAPL'

    # 병렬 수집
    def collect_price():
        collector = PriceCollector()
        return ('price', collector.collect_latest(ticker))

    def collect_news():
        collector = NewsCollector()
        return ('news', collector.collect_latest(ticker, days=7, limit=10))

    def collect_fundamentals():
        collector = FundamentalsCollector()
        return ('fundamentals', collector.collect_latest(ticker))

    def collect_options():
        collector = OptionsCollector()
        return ('options', collector.collect_latest(ticker))

    # 병렬 실행
    print(f"\nCollecting all data for {ticker} (parallel)...")
    results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(collect_price),
            executor.submit(collect_news),
            executor.submit(collect_fundamentals),
            executor.submit(collect_options)
        ]

        for future in as_completed(futures):
            data_type, data = future.result()
            results[data_type] = data
            if data:
                count = len(data) if isinstance(data, list) else 1
                print(f"  ✓ {ticker} {data_type}: {count} records")
            else:
                print(f"  ⚠ {ticker} {data_type}: no data (may be normal for options)")

    # 병렬 적재
    def load_price():
        if results.get('price'):
            loader = PriceLoader()
            with get_db_session() as session:
                count = loader.load_batch(results['price'], session)
            return ('price', count)
        return ('price', 0)

    def load_news():
        if results.get('news'):
            loader = NewsLoader()
            with get_db_session() as session:
                count = loader.load_batch(results['news'], session)
            return ('news', count)
        return ('news', 0)

    def load_fundamentals():
        if results.get('fundamentals'):
            loader = FundamentalsLoader()
            with get_db_session() as session:
                success = loader.load_single(results['fundamentals'], session)
            return ('fundamentals', 1 if success else 0)
        return ('fundamentals', 0)

    def load_options():
        if results.get('options'):
            loader = OptionsLoader()
            with get_db_session() as session:
                success = loader.load_single(results['options'], session)
            return ('options', 1 if success else 0)
        return ('options', 0)

    # 병렬 적재
    print(f"\nLoading all data to DB (parallel)...")
    load_results = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(load_price),
            executor.submit(load_news),
            executor.submit(load_fundamentals),
            executor.submit(load_options)
        ]

        for future in as_completed(futures):
            data_type, count = future.result()
            load_results[data_type] = count
            print(f"  ✓ {ticker} {data_type} loaded: {count} records")

    total_loaded = sum(load_results.values())
    print(f"\n✓ Total loaded: {total_loaded} records")
    return True


def test_multiple_tickers_parallel():
    """여러 종목 병렬 ETL 파이프라인"""
    print("\n" + "=" * 80)
    print("[Test 3] Multiple Tickers Parallel Pipeline")
    print("=" * 80)

    tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA']

    # ========================================
    # 1. 가격 데이터 병렬 수집
    # ========================================
    print(f"\n[1] Collecting prices for {len(tickers)} tickers (parallel)...")

    def collect_ticker_price(ticker):
        collector = PriceCollector()
        records = collector.collect_latest(ticker)
        return (ticker, records)

    price_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(collect_ticker_price, t) for t in tickers]

        for future in as_completed(futures):
            ticker, records = future.result()
            if records:
                price_data[ticker] = records
                print(f"  ✓ {ticker}: {len(records)} price records")

    # 가격 데이터 적재
    print(f"\n[2] Loading prices to DB...")
    price_loader = PriceLoader()
    with get_db_session() as session:
        price_results = price_loader.load_multiple_tickers(price_data, session)
    print(f"  ✓ Price loaded: {sum(price_results.values())} total records")

    # ========================================
    # 2. 뉴스 데이터 병렬 수집
    # ========================================
    print(f"\n[3] Collecting news for {len(tickers)} tickers (parallel)...")

    def collect_ticker_news(ticker):
        collector = NewsCollector()
        records = collector.collect_latest(ticker, days=7, limit=5)
        return (ticker, records)

    news_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(collect_ticker_news, t) for t in tickers]

        for future in as_completed(futures):
            ticker, records = future.result()
            if records:
                news_data[ticker] = records
                print(f"  ✓ {ticker}: {len(records)} news articles")

    # 뉴스 데이터 적재
    print(f"\n[4] Loading news to DB...")
    news_loader = NewsLoader()
    with get_db_session() as session:
        news_results = news_loader.load_multiple_tickers(news_data, session)
    print(f"  ✓ News loaded: {sum(news_results.values())} total records")

    # ========================================
    # 3. 펀더멘탈 데이터 병렬 수집
    # ========================================
    print(f"\n[5] Collecting fundamentals for {len(tickers)} tickers (parallel)...")

    def collect_ticker_fundamentals(ticker):
        collector = FundamentalsCollector()
        record = collector.collect_latest(ticker)
        return (ticker, record)

    fund_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(collect_ticker_fundamentals, t) for t in tickers]

        for future in as_completed(futures):
            ticker, record = future.result()
            if record:
                fund_data[ticker] = record
                print(f"  ✓ {ticker}: fundamentals collected")

    # 펀더멘탈 데이터 적재
    print(f"\n[6] Loading fundamentals to DB...")
    fund_loader = FundamentalsLoader()
    with get_db_session() as session:
        fund_results = fund_loader.load_multiple_tickers(fund_data, session)
    success_count = sum(1 for v in fund_results.values() if v)
    print(f"  ✓ Fundamentals loaded: {success_count}/{len(tickers)} tickers")

    # ========================================
    # 4. 옵션 데이터 병렬 수집
    # ========================================
    print(f"\n[7] Collecting options for {len(tickers)} tickers (parallel)...")

    def collect_ticker_options(ticker):
        collector = OptionsCollector()
        record = collector.collect_latest(ticker)
        return (ticker, record)

    options_data = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(collect_ticker_options, t) for t in tickers]

        for future in as_completed(futures):
            ticker, record = future.result()
            if record:
                options_data[ticker] = record
                print(f"  ✓ {ticker}: options summary collected")

    # 옵션 데이터 적재
    print(f"\n[8] Loading options to DB...")
    options_loader = OptionsLoader()
    with get_db_session() as session:
        options_results = options_loader.load_multiple_tickers(options_data, session)
    success_count = sum(1 for v in options_results.values() if v)
    print(f"  ✓ Options loaded: {success_count}/{len(tickers)} tickers")

    print(f"\n✓ All data collected and loaded for {len(tickers)} tickers (parallel)")
    return True


if __name__ == "__main__":
    print("=" * 80)
    print("  Integration Test: Collector + Loader (Parallel Processing)")
    print("=" * 80)
    print("\nNote: DB path should be set in config/settings.py")
    print("=" * 80)

    # 테스트 실행
    test1_passed = test_fred_pipeline()
    test2_passed = test_single_ticker_parallel()
    test3_passed = test_multiple_tickers_parallel()

    # 요약
    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"  Test 1 (FRED):                      {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Test 2 (Single Ticker Parallel):    {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"  Test 3 (Multiple Tickers Parallel): {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print("=" * 80)

    all_passed = all([test1_passed, test2_passed, test3_passed])
    if all_passed:
        print("\n🎉 All integration tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check logs above.")
