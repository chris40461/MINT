"""
Afternoon Report 생성 테스트

장 마감 리포트 생성 테스트:
- 확장된 시장 데이터 수집 (KOSPI + KOSDAQ + 개인수급 + 시장폭)
- DB에서 오후 트리거 결과 조회
- Google Search Grounding으로 급등주 재료 분석
- LLM 기반 시장 요약 + 업종 분석 + 수급 해석 + 내일 전략 생성
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.llm_report import LLMReport
from app.services.data_service import DataService
from app.db.database import init_db, get_db
from app.db.models import TriggerResult


def get_trigger_results(date: datetime, session: str = 'afternoon') -> list:
    """
    DB에서 트리거 결과 조회

    Args:
        date: 조회 날짜
        session: 'morning' or 'afternoon'

    Returns:
        급등주 목록 [{ticker, name, change_rate, volume, trigger_type, ...}]
    """
    date_str = date.strftime('%Y-%m-%d')

    with get_db() as db:
        results = db.query(TriggerResult).filter(
            TriggerResult.date == date_str,
            TriggerResult.session == session
        ).order_by(TriggerResult.composite_score.desc()).all()

        surge_stocks = []
        for r in results:
            surge_stocks.append({
                'ticker': r.ticker,
                'name': r.name,
                'change_rate': r.change_rate or 0.0,
                'volume': r.volume or 0,
                'trigger_type': r.trigger_type,
                'composite_score': r.composite_score or 0.0
            })

        return surge_stocks


async def test_market_index():
    """시장 지수 조회 테스트"""
    print("=" * 80)
    print("Step 1: 시장 지수 조회 테스트")
    print("=" * 80)
    print()

    data_service = DataService()
    test_date = datetime.now()

    print(f"테스트 날짜: {test_date.strftime('%Y-%m-%d')}")
    print("시장 데이터 조회 중...")
    print()

    market_data = await data_service.get_market_index(test_date)

    print("■ KOSPI")
    print(f"  종가: {market_data['kospi_close']:,.2f}")
    print(f"  등락률: {market_data['kospi_change']:+.2f}%")
    print(f"  포인트: {market_data['kospi_point_change']:+.2f}p")
    print()

    print("■ KOSDAQ")
    print(f"  종가: {market_data['kosdaq_close']:,.2f}")
    print(f"  등락률: {market_data['kosdaq_change']:+.2f}%")
    print(f"  포인트: {market_data['kosdaq_point_change']:+.2f}p")
    print()

    print("■ 거래대금")
    print(f"  전체: {market_data['trading_value'] // 100000000:,}억원")
    print()

    print("■ 수급 (KOSPI)")
    print(f"  외국인: {market_data['foreign_net_kospi'] // 100000000:+,}억원")
    print(f"  기관: {market_data['institution_net_kospi'] // 100000000:+,}억원")
    print(f"  개인: {market_data['individual_net_kospi'] // 100000000:+,}억원")
    print()

    print("■ 수급 (KOSDAQ)")
    print(f"  외국인: {market_data['foreign_net_kosdaq'] // 100000000:+,}억원")
    print(f"  기관: {market_data['institution_net_kosdaq'] // 100000000:+,}억원")
    print(f"  개인: {market_data['individual_net_kosdaq'] // 100000000:+,}억원")
    print()

    print("■ 시장 폭 (Market Breadth)")
    print(f"  상승: {market_data['advance_count']:,}개")
    print(f"  하락: {market_data['decline_count']:,}개")
    print(f"  보합: {market_data['unchanged_count']:,}개")
    print()

    return market_data


async def test_afternoon_report():
    """Afternoon Report 생성 테스트"""
    print("=" * 80)
    print("Afternoon Report 생성 테스트 시작")
    print("=" * 80)
    print()

    # DB 초기화
    init_db()

    # 테스트 날짜 (현재 날짜 또는 특정 날짜)
    test_date = datetime.now()
    print(f"테스트 날짜: {test_date.strftime('%Y-%m-%d')}")
    print()

    # Step 1: 확장된 시장 데이터 수집
    market_data = await test_market_index()

    # Step 2: DB에서 오후 트리거 결과 조회
    print("=" * 80)
    print("Step 2: 오후 트리거 결과 조회")
    print("=" * 80)
    print()

    surge_stocks = get_trigger_results(test_date, session='afternoon')

    if not surge_stocks:
        print("⚠️  오후 트리거 결과가 없습니다. 더미 데이터를 사용합니다.")
        # 더미 데이터 (테스트용)
        surge_stocks = [
            {'ticker': '005930', 'name': '삼성전자', 'change_rate': 3.5, 'volume': 15000000, 'trigger_type': 'intraday_rise'},
            {'ticker': '000660', 'name': 'SK하이닉스', 'change_rate': 4.2, 'volume': 8000000, 'trigger_type': 'volume_surge'},
            {'ticker': '035420', 'name': 'NAVER', 'change_rate': 2.8, 'volume': 2000000, 'trigger_type': 'closing_strength'},
            {'ticker': '051910', 'name': 'LG화학', 'change_rate': 5.1, 'volume': 1500000, 'trigger_type': 'intraday_rise'},
            {'ticker': '006400', 'name': '삼성SDI', 'change_rate': 3.9, 'volume': 1200000, 'trigger_type': 'volume_surge'},
        ]
        print()
        for i, stock in enumerate(surge_stocks[:10], 1):
            print(f"{i}. {stock['name']} ({stock['ticker']}) - {stock['change_rate']:+.2f}%")
    else:
        print(f"✅ {len(surge_stocks)}개 급등주 조회 완료")
        print()
        for i, stock in enumerate(surge_stocks[:10], 1):
            print(f"{i}. {stock['name']} ({stock['ticker']}) - {stock['change_rate']:+.2f}%, "
                  f"트리거: {stock['trigger_type']}")
    print()

    # Step 3: LLM Report 생성
    print("=" * 80)
    print("Step 3: Afternoon Report 생성 중...")
    print("=" * 80)
    print()
    print("⏳ LLM 호출 중 (Google Search Grounding 포함)")
    print("   약 1-2분 소요...")
    print()

    report_service = LLMReport()

    try:
        report = await report_service.generate_afternoon_report(
            test_date,
            market_data,
            surge_stocks
        )

        # 결과 출력
        print("=" * 80)
        print("Afternoon Report 생성 완료!")
        print("=" * 80)
        print()

        # 1. 시장 요약
        print("[1] 시장 요약")
        print("-" * 80)
        print(report.get('market_summary_text', 'N/A'))
        print()

        # 2. 시장 폭 분석
        market_breadth = report.get('market_breadth', {})
        if market_breadth:
            print("[2] 시장 폭 분석")
            print("-" * 80)
            print(f"분위기: {market_breadth.get('sentiment', 'N/A')}")
            print(f"해석: {market_breadth.get('interpretation', 'N/A')}")
            print()

        # 3. 업종별 분석
        sector_analysis = report.get('sector_analysis', {})
        if sector_analysis:
            print("[3] 업종별 분석")
            print("-" * 80)

            bullish = sector_analysis.get('bullish', [])
            if bullish:
                print("강세 업종:")
                for sector in bullish:
                    print(f"  • {sector.get('sector')}: {sector.get('change')} - {sector.get('reason')}")

            bearish = sector_analysis.get('bearish', [])
            if bearish:
                print("\n약세 업종:")
                for sector in bearish:
                    print(f"  • {sector.get('sector')}: {sector.get('change')} - {sector.get('reason')}")
            print()

        # 4. 수급 해석
        supply_demand = report.get('supply_demand_analysis', '')
        if supply_demand:
            print("[4] 수급 해석")
            print("-" * 80)
            print(supply_demand)
            print()

        # 5. 오늘의 테마
        themes = report.get('today_themes', [])
        if themes:
            print("[5] 오늘의 테마")
            print("-" * 80)
            for theme in themes:
                print(f"• {theme.get('theme')}: {theme.get('drivers')}")
                leading = theme.get('leading_stocks', [])
                if leading:
                    print(f"  대장주: {', '.join(leading)}")
            print()

        # 6. 급등주 분석
        surge_analysis = report.get('surge_analysis', [])
        if surge_analysis:
            print("[6] 급등주 분석")
            print("=" * 80)
            for stock in surge_analysis:
                print(f"\n• {stock.get('name')} ({stock.get('ticker')})")
                print(f"  카테고리: {stock.get('category')}")
                print(f"  급등 사유: {stock.get('reason')}")
                print(f"  전망: {stock.get('outlook')}")
            print()

        # 7. 내일 전략
        print("[7] 내일 투자 전략")
        print("-" * 80)
        print(report.get('tomorrow_strategy', 'N/A'))
        print()

        # 8. 체크 포인트
        check_points = report.get('check_points', [])
        if check_points:
            print("[8] 내일 확인 사항")
            print("-" * 80)
            for i, point in enumerate(check_points, 1):
                print(f"{i}. {point}")
            print()

        # 9. 메타데이터
        metadata = report.get('metadata', {})
        print("[9] 메타데이터")
        print("-" * 80)
        print(f"생성 시각: {report.get('generated_at', 'N/A')}")
        print(f"Grounding Sources: {len(metadata.get('grounding_sources', []))}개")
        print()

        # JSON 저장
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_file = data_dir / "afternoon_report_test.json"

        # datetime 객체 직렬화를 위한 처리
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=json_serializer)

        print(f"✅ Afternoon Report 저장: {output_file}")
        print()

        # 검증 결과 요약
        print("=" * 80)
        print("검증 결과 요약")
        print("=" * 80)

        validation_results = []

        # 필수 필드 체크
        required_fields = [
            'market_summary_text',
            'market_breadth',
            'sector_analysis',
            'supply_demand_analysis',
            'today_themes',
            'surge_analysis',
            'tomorrow_strategy',
            'check_points'
        ]

        for field in required_fields:
            value = report.get(field)
            if value:
                validation_results.append((field, "✅ OK"))
            else:
                validation_results.append((field, "❌ 누락"))

        for field, status in validation_results:
            print(f"  {field}: {status}")
        print()

        print("=" * 80)
        print("테스트 완료!")
        print("=" * 80)

        return report

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """메인 실행"""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "Afternoon Report Test" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        await test_afternoon_report()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단")
    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
