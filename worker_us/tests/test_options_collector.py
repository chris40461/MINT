"""
Options Collector 테스트
"""

import sys
from pathlib import Path

# worker_us를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.options_collector import OptionsCollector


def test_single_ticker():
    """단일 종목 옵션 테스트"""
    print("\n[Test 1] Single Ticker Options (AAPL)")
    print("-" * 80)

    collector = OptionsCollector()
    record = collector.collect_ticker('AAPL')

    if record:
        print(f"✓ AAPL options summary collected")
        print(f"\nOptions summary:")
        for key, value in record.items():
            print(f"  {key:25s}: {value}")
        return True
    else:
        print("✗ AAPL options collection failed")
        return False


def test_latest():
    """최신 옵션 요약 수집 테스트"""
    print("\n[Test 2] Latest Options Summary (MSFT)")
    print("-" * 80)

    collector = OptionsCollector()
    record = collector.collect_latest('MSFT')

    if record:
        print(f"✓ MSFT latest options summary collected")
        print(f"\nKey metrics:")
        print(f"  Put/Call Ratio (Vol) : {record.get('put_call_ratio_volume')}")
        print(f"  Put/Call Ratio (OI)  : {record.get('put_call_ratio_oi')}")
        print(f"  Total Call Volume    : {record.get('total_call_volume')}")
        print(f"  Total Put Volume     : {record.get('total_put_volume')}")
        print(f"  Avg IV (Call)        : {record.get('avg_iv_call')}")
        print(f"  Avg IV (Put)         : {record.get('avg_iv_put')}")
        return True
    else:
        print("✗ MSFT latest options collection failed")
        return False


def test_multiple_tickers():
    """여러 종목 테스트"""
    print("\n[Test 3] Multiple Tickers (AAPL, MSFT, GOOGL)")
    print("-" * 80)

    collector = OptionsCollector()
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    results = collector.collect_latest_batch(tickers)

    if results:
        print(f"✓ Collected options for {len(results)}/{len(tickers)} tickers")
        for ticker, record in results.items():
            print(f"\n  {ticker}:")
            print(f"    PCR (Vol)  : {record.get('put_call_ratio_volume')}")
            print(f"    PCR (OI)   : {record.get('put_call_ratio_oi')}")
            print(f"    Avg IV     : {record.get('avg_iv')}")
        return True
    else:
        print("✗ Multiple tickers options collection failed")
        return False


def test_small_cap():
    """작은 종목 테스트 (옵션 없을 수 있음)"""
    print("\n[Test 4] Small Cap Stock (May have no options)")
    print("-" * 80)

    collector = OptionsCollector()
    # 작은 종목 예시 (옵션이 없을 수 있음)
    record = collector.collect_ticker('APADR')  # 존재하지 않는 종목

    if record:
        print(f"✓ Collected options summary")
        return True
    else:
        print("✓ No options data (expected for small/non-existent stocks)")
        return True  # 옵션 없는 건 정상


if __name__ == "__main__":
    print("=" * 80)
    print("  Options Collector Test")
    print("=" * 80)
    print("Note: Some stocks may not have CBOE options (this is normal)")
    print("=" * 80)

    # 테스트 실행
    test1_passed = test_single_ticker()
    test2_passed = test_latest()
    test3_passed = test_multiple_tickers()
    test4_passed = test_small_cap()

    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"  Test 1 (Single Ticker):    {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Test 2 (Latest):           {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"  Test 3 (Multiple Tickers): {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print(f"  Test 4 (Small Cap):        {'✓ PASSED' if test4_passed else '✗ FAILED'}")
    print("=" * 80)
