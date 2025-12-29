"""
실제 데이터로 기업 분석 테스트

DataService로 실제 종목 데이터를 불러와서 LLMService.analyze_company()를 테스트합니다.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# backend/ 디렉토리를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.data_service import DataService
from app.services.llm_company_analysis import LLMCompanyAnalysis


async def test_real_company_analysis(ticker: str = "068270"):
    """
    실제 종목 데이터로 기업 분석 테스트

    Args:
        ticker: 종목 코드 (기본값: 068270 셀트리온)
    """
    print("=" * 80)
    print(f"실제 데이터 기반 기업 분석 테스트")
    print("=" * 80)
    print()

    # 1. 서비스 초기화
    print("🔧 서비스 초기화 중...")
    try:
        data_service = DataService()
        llm_service = LLMCompanyAnalysis()
        print("✅ DataService, LLMCompanyAnalysis 초기화 완료\n")
    except Exception as e:
        print(f"❌ 서비스 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. 실제 데이터 수집
    print(f"📊 데이터 수집 중: {ticker}")
    print("-" * 80)

    try:
        # 2.1 기본 정보
        print("  [1/5] 기본 정보 조회 중...")
        stock_info = await data_service.get_stock_info(ticker)
        print(f"  ✅ {stock_info['name']} ({stock_info['market']}) - 시총 {stock_info['market_cap']}억원")

        # 2.2 현재 가격
        print("  [2/5] 현재가 조회 중...")
        today = datetime.now()
        snapshot = await data_service.get_market_snapshot(today)

        if ticker not in snapshot['ticker'].values:
            print(f"  ❌ {ticker}의 시장 데이터를 찾을 수 없습니다 (오늘 휴장일일 수 있음)")
            return

        current_data = snapshot[snapshot['ticker'] == ticker].iloc[0]
        current_price = int(current_data['종가'])
        print(f"  ✅ 현재가: {current_price:,}원")

        # 2.3 재무 데이터
        print("  [3/5] 재무 데이터 조회 중...")
        financial = await data_service.get_financial_data(ticker)
        print(f"  ✅ ROE: {financial['roe']:.1f}%, PER: {financial['per']:.1f}, PBR: {financial['pbr']:.2f}")

        # 2.4 뉴스 데이터
        print("  [4/5] 뉴스 데이터 조회 중...")
        news_list = await data_service.get_news_data(ticker, days=7)
        print(f"  ✅ 뉴스 {len(news_list)}개 수집")

        # 2.5 기술적 지표
        print("  [5/5] 기술적 지표 계산 중...")
        technical = await data_service.get_technical_indicators(ticker, today)
        print(f"  ✅ RSI: {technical['rsi']:.1f}, MACD: {technical['macd_status']}, MA: {technical['ma_position']}")

        print()
        print("-" * 80)
        print("✅ 모든 데이터 수집 완료!\n")

    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. company_data 구성
    company_data = {
        'name': stock_info['name'],
        'current_price': current_price,
        'market_cap': stock_info['market_cap'],
        'financial': financial,
        'news': news_list,
        'technical': technical
    }

    # 4. LLM 분석 실행
    print("=" * 80)
    print(f"🤖 LLM 분석 시작: {stock_info['name']}")
    print("=" * 80)
    print()

    try:
        result = await llm_service.analyze_company(ticker, company_data)

        # Step 1~3 계산 결과 출력
        print("\n" + "=" * 80)
        print("📋 목표가 계산 결과 (Step 1~3)")
        print("=" * 80)
        if 'target_price_calculation' in result:
            calc = result['target_price_calculation']
            print(f"\nStep 1 (기본 밸류): {calc['step1_base_valuation']['base_target']:,}원")
            print(f"  - {calc['step1_base_valuation']['details']}")

            print(f"\nStep 2 (기술적 조정): {calc['step2_technical_adjustment']['adjustment']:+.1%}")
            print(f"  - {calc['step2_technical_adjustment']['details']}")

            print(f"\nStep 3 (뉴스 센티먼트): {calc['step3_news_sentiment']['adjustment']:+.2%}")
            print(f"  - 원본 {calc['step3_news_sentiment'].get('original_count', 0)}개 → 중복 제거 후 {calc['step3_news_sentiment'].get('deduplicated_count', 0)}개")
            print(f"  - 긍정 {calc['step3_news_sentiment']['positive_count']}개 (+{calc['step3_news_sentiment']['positive_count'] * 0.05:.2f}%), 부정 {calc['step3_news_sentiment']['negative_count']}개 ({calc['step3_news_sentiment']['negative_count'] * -0.05:.2f}%), 중립 {calc['step3_news_sentiment']['neutral_count']}개")
            print(f"  - {calc['step3_news_sentiment']['reasoning'][:100]}...")

            print(f"\n예비 목표가: {calc['preliminary_target']:,}원")
            print(f"총 조정: {calc['total_adjustment']:+.1%}")
        print("=" * 80)

        # 실제 LLM에 전달된 프롬프트 출력
        print("\n" + "=" * 80)
        print("📄 LLM에 전달된 프롬프트 전체")
        print("=" * 80)
        if 'metadata' in result and 'prompt' in result['metadata']:
            prompt_text = result['metadata']['prompt']
            # 프롬프트 길이가 너무 길면 일부만 출력 (필요시 전체 출력)
            print(prompt_text)
        print("=" * 80)

        print("=" * 80)
        print("✅ 분석 완료!")
        print("=" * 80)
        print()

        # 결과 출력
        print(f"📌 종목: {stock_info['name']} ({ticker})")
        print(f"💰 현재가: {current_price:,}원")
        print(f"🎯 목표가: {result['target_price']:,}원")

        upside = ((result['target_price'] / current_price) - 1) * 100
        print(f"📈 상승여력: {upside:+.1f}%")

        print(f"💡 투자의견: **{result['opinion']}**")

        if result.get('stop_loss_price'):
            print(f"🛑 손절가: {result['stop_loss_price']:,}원")

        print()
        print("-" * 80)
        print("📝 요약 (3줄)")
        print("-" * 80)
        print(result['summary'])
        print()

        print("-" * 80)
        print("💼 재무 분석")
        print("-" * 80)
        print(result['financial_analysis'])
        print()

        print("-" * 80)
        print("🏭 산업 분석")
        print("-" * 80)
        print(result['industry_analysis'])
        print()

        print("-" * 80)
        print("📰 뉴스 분석")
        print("-" * 80)
        print(result['news_analysis'])
        print()

        print("-" * 80)
        print("📈 기술적 분석")
        print("-" * 80)
        print(result['technical_analysis'])
        print()

        print("-" * 80)
        print(f"⚠️  리스크 요인 ({len(result['risks'])}개)")
        print("-" * 80)
        for i, risk in enumerate(result['risks'], 1):
            print(f"{i}. {risk}")
        print()

        print("-" * 80)
        print("💡 투자 전략")
        print("-" * 80)
        print(result['investment_strategy'])
        print()

        # 비용 리포트
        cost_report = llm_service.cost_tracker.get_daily_report()
        print("=" * 80)
        print("💰 LLM 비용 리포트")
        print("=" * 80)
        print(f"입력 토큰:  {cost_report['input_tokens']:,} tokens")
        print(f"출력 토큰:  {cost_report['output_tokens']:,} tokens")
        print(f"예상 비용:  ${cost_report['total_cost_usd']:.4f} (약 ₩{cost_report['total_cost_krw']:.0f})")
        print()

    except Exception as e:
        print(f"❌ LLM 분석 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='실제 데이터로 기업 분석 테스트')
    parser.add_argument('--ticker', type=str, default='068270',
                        help='종목 코드 (기본값: 068270 셀트리온)')

    args = parser.parse_args()

    asyncio.run(test_real_company_analysis(args.ticker))
