"""
News Collector 테스트
"""

import sys
from pathlib import Path

# worker_us를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.news_collector import NewsCollector


def test_single_ticker():
    """단일 종목 뉴스 테스트"""
    print("\n[Test 1] Single Ticker News (AAPL, Last 50 Articles)")
    print("-" * 80)

    collector = NewsCollector()
    records = collector.collect_ticker('AAPL', limit=50)

    if records:
        print(f"✓ AAPL collected: {len(records)} news articles")
        print(f"\nLatest article:")
        latest = records[0]
        for key, value in latest.items():
            print(f"  {key:15s}: {value}")
        return True
    else:
        print("✗ AAPL news collection failed")
        return False


def test_recent_news():
    """최근 7일 뉴스만 수집 테스트"""
    print("\n[Test 2] Recent News (AAPL, Last 7 Days)")
    print("-" * 80)

    collector = NewsCollector()
    records = collector.collect_latest('AAPL', days=7)

    if records:
        print(f"✓ AAPL recent news collected: {len(records)} articles")
        print(f"\nFirst 3 articles:")
        for i, article in enumerate(records[:3], 1):
            print(f"\n  [{i}] {article['title']}")
            print(f"      Date: {article['published_date']}")
            print(f"      URL: {article['url']}")
        return True
    else:
        print("✗ Recent news collection failed")
        return False


def test_multiple_tickers():
    """여러 종목 테스트"""
    print("\n[Test 3] Multiple Tickers (AAPL, MSFT, GOOGL - Last 7 Days)")
    print("-" * 80)

    collector = NewsCollector()
    tickers = ['AAPL', 'MSFT', 'GOOGL']
    results = collector.collect_latest_batch(tickers, days=7, limit=20)

    if results:
        print(f"✓ Collected news for {len(results)}/{len(tickers)} tickers")
        for ticker, records in results.items():
            print(f"  {ticker}: {len(records)} articles")
        return True
    else:
        print("✗ Multiple tickers news collection failed")
        return False


if __name__ == "__main__":
    print("=" * 80)
    print("  News Collector Test")
    print("=" * 80)

    # 테스트 실행
    test1_passed = test_single_ticker()
    test2_passed = test_recent_news()
    test3_passed = test_multiple_tickers()

    print("\n" + "=" * 80)
    print("  Test Summary")
    print("=" * 80)
    print(f"  Test 1 (Single Ticker):    {'✓ PASSED' if test1_passed else '✗ FAILED'}")
    print(f"  Test 2 (Recent News):      {'✓ PASSED' if test2_passed else '✗ FAILED'}")
    print(f"  Test 3 (Multiple Tickers): {'✓ PASSED' if test3_passed else '✗ FAILED'}")
    print("=" * 80)
