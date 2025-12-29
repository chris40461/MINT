"""
FRED Collector 테스트
"""

import sys
from pathlib import Path

# worker_us를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.fred_collector import FREDCollector


def test_single_indicator():
    """단일 지표 테스트"""
    print("\n[Test 1] Single Indicator (DGS10)")
    print("-" * 80)

    collector = FREDCollector()
    dgs10 = collector.collect_single_indicator('DGS10')

    if dgs10 is not None:
        print(f"✓ DGS10 collected: {len(dgs10)} data points")
        print(f"  Latest: {dgs10.iloc[-1]:.2f} on {dgs10.index[-1]}")
        return True
    else:
        print("✗ DGS10 collection failed")
        return False


def test_all_indicators():
    """전체 지표 수집 테스트"""
    print("\n[Test 2] All Indicators")
    print("-" * 80)

    collector = FREDCollector()
    result = collector.collect()

    if result:
        print("✓ FRED data collected successfully")
        print(f"\nResult:")
        for key, value in result.items():
            print(f"  {key:20s}: {value}")
        return True
    else:
        print("✗ FRED data collection failed")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("  FRED Collector Test")
    print("=" * 80)

    # 테스트 실행
    test1_passed = test_single_indicator()
    test2_passed = test_all_indicators()

    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"  Test 1 (Single Indicator): {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Test 2 (All Indicators):   {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print("=" * 80)
