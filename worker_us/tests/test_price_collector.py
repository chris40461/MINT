"""
Price Collector 테스트
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# worker_us를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.price_collector import PriceCollector


def test_single_ticker():
    """단일 종목 가격 데이터 테스트"""
    print("\n[Test 1] Single Ticker Price Data (AAPL, Last 5 Days)")
    print("-" * 80)

    collector = PriceCollector()

    # 최근 5일 데이터
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)

    records = collector.collect_ticker('AAPL', start_date, end_date)

    if records:
        print(f"✓ AAPL collected: {len(records)} records")
        print(f"\nLatest record:")
        latest = records[-1]
        for key, value in latest.items():
            print(f"  {key:10s}: {value}")
        return True
    else:
        print("✗ AAPL collection failed")
        return False


def test_yesterday():
    """어제 데이터만 수집 테스트"""
    print("\n[Test 2] Yesterday's Price (AAPL)")
    print("-" * 80)

    collector = PriceCollector()
    records = collector.collect_latest('AAPL')

    if records:
        print(f"✓ Yesterday's AAPL collected: {len(records)} record(s)")
        if records:
            record = records[0]
            print(f"\nYesterday's data:")
            for key, value in record.items():
                print(f"  {key:10s}: {value}")
        return True
    else:
        print("✗ Yesterday's data collection failed")
        return False


def test_multiple_tickers():
    """여러 종목 테스트"""
    print("\n[Test 3] Multiple Tickers (AAPL, MSFT, GOOGL - Last 3 Days)")
    print("-" * 80)

    collector = PriceCollector()

    end_date = datetime.now()
    start_date = end_date - timedelta(days=3)

    tickers = ['AAPL', 'MSFT', 'GOOGL']
    results = collector.collect_multiple(tickers, start_date, end_date)

    if results:
        print(f"✓ Collected {len(results)}/{len(tickers)} tickers")
        for ticker, records in results.items():
            print(f"  {ticker}: {len(records)} records")
        return True
    else:
        print("✗ Multiple tickers collection failed")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("  Price Collector Test")
    print("=" * 80)

    # 테스트 실행
    test1_passed = test_single_ticker()
    test2_passed = test_yesterday()
    test3_passed = test_multiple_tickers()

    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"  Test 1 (Single Ticker):    {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Test 2 (Yesterday):        {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"  Test 3 (Multiple Tickers): {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print("=" * 80)
