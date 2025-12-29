"""
Fundamentals Collector 테스트
"""

import sys
from pathlib import Path

# worker_us를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.fundamentals_collector import FundamentalsCollector


def test_single_ticker():
    """단일 종목 펀더멘탈 테스트"""
    print("\n[Test 1] Single Ticker Fundamentals (AAPL)")
    print("-" * 80)

    collector = FundamentalsCollector()
    record = collector.collect_ticker('AAPL')

    if record:
        print(f"✓ AAPL fundamentals collected")
        print(f"\nFundamental metrics:")
        for key, value in record.items():
            print(f"  {key:30s}: {value}")
        return True
    else:
        print("✗ AAPL fundamentals collection failed")
        return False


def test_latest():
    """최신 펀더멘탈 수집 테스트"""
    print("\n[Test 2] Latest Fundamentals (MSFT)")
    print("-" * 80)

    collector = FundamentalsCollector()
    record = collector.collect_latest('MSFT')

    if record:
        print(f"✓ MSFT latest fundamentals collected")
        print(f"\nKey metrics:")
        print(f"  Market Cap       : {record.get('market_cap')}")
        print(f"  PE Ratio         : {record.get('pe_ratio')}")
        print(f"  Price/Sales      : {record.get('price_to_sales')}")
        print(f"  Price/Book       : {record.get('price_to_book')}")
        print(f"  ROE              : {record.get('return_on_equity')}")
        print(f"  Debt/Equity      : {record.get('debt_to_equity')}")
        return True
    else:
        print("✗ MSFT latest fundamentals collection failed")
        return False


def test_multiple_tickers():
    """여러 종목 테스트"""
    print("\n[Test 3] Multiple Tickers (AAPL, MSFT, GOOGL)")
    print("-" * 80)

    collector = FundamentalsCollector()
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    results = collector.collect_latest_batch(tickers)

    if results:
        print(f"✓ Collected fundamentals for {len(results)}/{len(tickers)} tickers")
        for ticker, record in results.items():
            print(f"\n  {ticker}:")
            print(f"    PE Ratio    : {record.get('pe_ratio')}")
            print(f"    ROE         : {record.get('return_on_equity')}")
            print(f"    Debt/Equity : {record.get('debt_to_equity')}")
        return True
    else:
        print("✗ Multiple tickers fundamentals collection failed")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("  Fundamentals Collector Test")
    print("=" * 80)

    # 테스트 실행
    test1_passed = test_single_ticker()
    test2_passed = test_latest()
    test3_passed = test_multiple_tickers()

    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"  Test 1 (Single Ticker):    {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Test 2 (Latest):           {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"  Test 3 (Multiple Tickers): {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print("=" * 80)
