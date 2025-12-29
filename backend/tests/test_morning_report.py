"""
Morning Report 생성 테스트

장 시작 리포트 생성 테스트:
- Top 10 종목 선정 (M:40%, V:30%, T:20%, S:10%)
- realtime_prices 조회 (시간외 거래 데이터)
- ATR 계산 (동적 목표가/손절가)
- Google Search Grounding으로 해외 시장 정보 수집
- LLM 기반 시장 전망 + 섹터 분석 + 투자 전략 생성

Usage:
    cd backend && python tests/test_morning_report.py
    cd backend && python tests/test_morning_report.py --date 2025-12-03
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.llm_report import LLMReport
from app.db.database import init_db


def get_confidence_label(confidence: float) -> str:
    """Confidence 값을 라벨로 변환"""
    if confidence >= 0.8:
        return f"🟢 HIGH ({confidence:.0%})"
    elif confidence >= 0.6:
        return f"🟡 MEDIUM ({confidence:.0%})"
    else:
        return f"🔴 LOW ({confidence:.0%})"


async def test_morning_report(test_date: datetime):
    """Morning Report 생성 테스트"""
    print("=" * 80)
    print("Morning Report 생성 테스트 시작")
    print("=" * 80)
    print()

    # DB 초기화
    init_db()

    # LLMReport 서비스 생성
    report_service = LLMReport()

    print(f"테스트 날짜: {test_date.strftime('%Y-%m-%d')}")
    print()

    try:
        # ========== Phase 1: Top 10 종목 선정 ==========
        print("=" * 80)
        print("[Phase 1] Top 10 종목 선정...")
        print("=" * 80)
        top_10_stocks = await report_service.select_top_stocks_for_morning(test_date, top_n=10)
        print(f"선정된 종목 수: {len(top_10_stocks)}")
        for i, stock in enumerate(top_10_stocks, 1):
            print(f"  {i}. {stock['name']} ({stock['ticker']}) - 점수: {stock['final_score']:.2f}")
        print()

        # ========== Phase 2: 시장 데이터 수집 ==========
        print("=" * 80)
        print("[Phase 2] 시장 데이터 수집...")
        print("=" * 80)
        market_data = await report_service._collect_market_data(test_date)
        print(f"KOSPI 종가: {market_data.get('kospi_close')}")
        print(f"KOSPI 등락률: {market_data.get('kospi_change')}%")
        print()

        # ========== Phase 2.5: realtime_prices 조회 ==========
        print("=" * 80)
        print("[Phase 2.5] realtime_prices 조회...")
        print("=" * 80)
        tickers = [stock['ticker'] for stock in top_10_stocks]
        realtime_prices = await report_service.data_service.get_realtime_prices_bulk(tickers, staleness_threshold=86400)
        for ticker, rt in realtime_prices.items():
            if rt:
                print(f"  {ticker}: {rt.get('current_price'):,}원 ({rt.get('change_rate'):+.2f}%)")
        print()

        # ========== Phase 2.6: ATR 계산 ==========
        print("=" * 80)
        print("[Phase 2.6] ATR 계산...")
        print("=" * 80)
        atr_data = await report_service.data_service.get_atr_batch(tickers, test_date, period=14)
        for ticker, atr in atr_data.items():
            if atr:
                print(f"  {ticker}: ATR {atr:,.0f}원")
        print()

        # Top 10에 realtime_prices + ATR 병합
        for stock in top_10_stocks:
            ticker = stock['ticker']
            if ticker in realtime_prices and realtime_prices[ticker]:
                stock['realtime_price'] = realtime_prices[ticker]
            else:
                stock['realtime_price'] = None
            stock['atr'] = atr_data.get(ticker)
            if stock['atr'] and stock.get('realtime_price'):
                current_price = stock['realtime_price'].get('current_price', 0)
                if current_price > 0:
                    stock['atr_percent'] = round(stock['atr'] / current_price * 100, 2)

        # ========== Phase 3: 프롬프트 생성 ==========
        print("=" * 80)
        print("[Phase 3] 프롬프트 생성")
        print("=" * 80)
        prompt = report_service._build_morning_report_prompt(test_date, market_data, top_10_stocks)
        print()
        print(">>> 프롬프트 전문 <<<")
        print("-" * 80)
        print(prompt)
        print("-" * 80)
        print(f"프롬프트 길이: {len(prompt):,} 문자")
        print()

        # ========== Phase 4: LLM 호출 ==========
        print("=" * 80)
        print("[Phase 4] LLM 호출 (Google Search Grounding)...")
        print("=" * 80)
        print("⏳ 약 1-2분 소요...")
        print()

        report = await report_service.generate_morning_report(test_date)

        # ========== 전체 출력 (JSON) ==========
        print()
        print("=" * 80)
        print(">>> LLM 응답 전문 (JSON) <<<")
        print("=" * 80)
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        print()
        print("=" * 80)

        # 결과 출력
        print("=" * 80)
        print("Morning Report 생성 완료!")
        print("=" * 80)
        print()

        # 1. 시장 전망
        print("[1] 시장 전망")
        print("-" * 80)
        print(report.get('market_forecast', 'N/A'))
        print()

        # 2. KOSPI 예상 범위
        kospi_range = report.get('kospi_range', {})
        print(f"[2] KOSPI 예상 범위: {kospi_range.get('low', 0):.2f} ~ {kospi_range.get('high', 0):.2f}")
        if 'reasoning' in kospi_range:
            print(f"   근거: {kospi_range.get('reasoning')}")
        print()

        # 3. 주요 리스크
        market_risks = report.get('market_risks', [])
        if market_risks:
            print("[3] 주요 리스크 요인")
            print("-" * 80)
            for i, risk in enumerate(market_risks, 1):
                print(f"{i}. {risk}")
            print()

        # 4. Top 10 주목 종목 (상세 진입 전략)
        print("[4] 주목 종목 Top 10 (상세 진입 전략)")
        print("=" * 80)
        top_stocks = report.get('top_stocks', [])
        for stock_info in top_stocks[:10]:
            print(f"\n{'─' * 78}")
            print(f"#{stock_info.get('rank')} {stock_info.get('name')} ({stock_info.get('ticker')})")
            print(f"{'─' * 78}")
            print(f"   현재가: {stock_info.get('current_price', 0):,}원")
            print(f"   주목 이유: {stock_info.get('reason', 'N/A')}")

            # 진입 전략 상세 출력
            entry = stock_info.get('entry_strategy', {})
            if isinstance(entry, dict):
                print("\n   📈 진입 전략:")

                # Chain-of-Thought Analysis (새로 추가)
                if entry.get('analysis'):
                    print(f"      📊 분석: {entry.get('analysis')}")

                # Confidence (새로 추가)
                if entry.get('confidence') is not None:
                    print(f"      🎯 신뢰도: {get_confidence_label(entry.get('confidence'))}")

                print()
                print(f"      진입가: {entry.get('entry_price', 0):,}원")
                print(f"      진입 타이밍: {entry.get('entry_timing', 'N/A')}")

                entry_price = entry.get('entry_price', 1)
                target1 = entry.get('target_price_1', 0)
                target2 = entry.get('target_price_2', 0)
                stop_loss = entry.get('stop_loss', 0)

                if entry_price > 0:
                    gain1 = ((target1 / entry_price - 1) * 100) if target1 else 0
                    gain2 = ((target2 / entry_price - 1) * 100) if target2 else 0
                    loss = ((stop_loss / entry_price - 1) * 100) if stop_loss else 0

                    print(f"      1차 목표가: {target1:,}원 ({gain1:+.1f}%)")
                    print(f"      2차 목표가: {target2:,}원 ({gain2:+.1f}%)")
                    print(f"      손절가: {stop_loss:,}원 ({loss:+.1f}%)")

                print(f"      손익비: {entry.get('risk_reward_ratio', 'N/A')}")
                print(f"      보유기간: {entry.get('holding_period', 'N/A')}")
                print(f"      기술적 근거: {entry.get('technical_basis', 'N/A')}")
                print(f"      거래량 전략: {entry.get('volume_strategy', 'N/A')}")
                print(f"      청산 조건: {entry.get('exit_condition', 'N/A')}")
            else:
                print(f"   진입 전략: {entry}")

        # 5. 섹터 분석
        print()
        print("[5] 섹터 분석")
        print("-" * 80)
        sector_analysis = report.get('sector_analysis', {})

        bullish = sector_analysis.get('bullish', [])
        if bullish:
            print("📈 강세 예상:")
            for sector_info in bullish:
                if isinstance(sector_info, dict):
                    print(f"   • {sector_info.get('sector')}: {sector_info.get('reason')}")
                else:
                    print(f"   • {sector_info}")

        bearish = sector_analysis.get('bearish', [])
        if bearish:
            print("\n📉 약세 예상:")
            for sector_info in bearish:
                if isinstance(sector_info, dict):
                    print(f"   • {sector_info.get('sector')}: {sector_info.get('reason')}")
                else:
                    print(f"   • {sector_info}")
        print()

        # 6. 투자 전략
        print("[6] 투자 전략")
        print("-" * 80)
        print(report.get('investment_strategy', 'N/A'))
        print()

        # 7. 시간대별 전략
        daily_schedule = report.get('daily_schedule', {})
        if daily_schedule:
            print("[7] 시간대별 전략")
            print("-" * 80)
            for time_slot, strategy in daily_schedule.items():
                time_formatted = time_slot.replace('_', ':')
                print(f"⏰ {time_formatted}: {strategy}")
            print()

        # 8. 메타데이터
        metadata = report.get('metadata', {})
        print("[8] 메타데이터")
        print("-" * 80)
        print(f"생성 시각: {metadata.get('generated_at', 'N/A')}")
        market_data = metadata.get('market_data', {})
        print(f"전일 KOSPI: {market_data.get('kospi_close', 'N/A')} ({market_data.get('kospi_change', 'N/A')}%)")
        print(f"Grounding Sources: {len(metadata.get('grounding_sources', []))}개")
        print()

        # JSON 저장
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_file = data_dir / f"morning_report_{test_date.strftime('%Y%m%d')}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        print(f"✅ Morning Report 저장: {output_file}")
        print()

        print("=" * 80)
        print("테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Morning Report 생성 테스트')
    parser.add_argument('--date', type=str, help='테스트 날짜 (YYYY-MM-DD)', default=None)
    args = parser.parse_args()

    if args.date:
        test_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        test_date = datetime.now()

    asyncio.run(test_morning_report(test_date))
