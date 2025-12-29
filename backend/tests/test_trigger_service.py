"""
TriggerService 테스트 스크립트
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.trigger_service import TriggerService
from app.services.data_service import DataService


async def test_trigger_service():
    data_service = DataService()
    trigger_service = TriggerService(data_service)

    print("=== TriggerService 테스트 시작 ===\n")

    # 테스트 날짜 (최근 거래일)
    test_date = datetime.now()

    # ============= 개별 트리거 테스트 =============

    print("1. 오전 트리거 1: 거래량 급증...")
    try:
        results = await trigger_service.morning_volume_surge(test_date, top_n=3)
        print(f"✅ 감지 완료: {len(results)}개 종목")
        if results:
            print(f"\n상위 종목:")
            for i, stock in enumerate(results, 1):
                print(f"  [{i}] {stock['name']} ({stock['ticker']})")
                print(f"      현재가: {stock['current_price']:,}원 ({stock['change_rate']:+.2f}%)")
                print(f"      거래량 증가율: {stock['volume_increase_rate']:.1f}%")
                print(f"      복합점수: {stock['composite_score']:.3f}")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    print("2. 오전 트리거 2: 갭 상승 모멘텀...")
    try:
        results = await trigger_service.morning_gap_up(test_date, top_n=3)
        print(f"✅ 감지 완료: {len(results)}개 종목")
        if results:
            print(f"\n상위 종목:")
            for i, stock in enumerate(results, 1):
                print(f"  [{i}] {stock['name']} ({stock['ticker']})")
                print(f"      현재가: {stock['current_price']:,}원 ({stock['change_rate']:+.2f}%)")
                print(f"      갭상승률: {stock['gap_ratio']:.2f}%")
                print(f"      장중등락률: {stock['intraday_change']:.2f}%")
    except Exception as e:
        print(f"❌ 실패: {e}")

    print("\n" + "="*70 + "\n")

    print("3. 오전 트리거 3: 시총 대비 자금유입...")
    try:
        results = await trigger_service.morning_fund_inflow(test_date, top_n=3)
        print(f"✅ 감지 완료: {len(results)}개 종목")
        if results:
            print(f"\n상위 종목:")
            for i, stock in enumerate(results, 1):
                print(f"  [{i}] {stock['name']} ({stock['ticker']})")
                print(f"      자금유입비율: {stock['fund_inflow_ratio']:.3f}%")
    except Exception as e:
        print(f"❌ 실패: {e}")

    print("\n" + "="*70 + "\n")

    print("4. 오후 트리거 1: 일중 상승률...")
    try:
        results = await trigger_service.afternoon_intraday_rise(test_date, top_n=3)
        print(f"✅ 감지 완료: {len(results)}개 종목")
        if results:
            print(f"\n상위 종목:")
            for i, stock in enumerate(results, 1):
                print(f"  [{i}] {stock['name']} ({stock['ticker']})")
                print(f"      장중등락률: {stock['intraday_change']:.2f}%")
    except Exception as e:
        print(f"❌ 실패: {e}")

    print("\n" + "="*70 + "\n")

    print("5. 오후 트리거 2: 마감 강도...")
    try:
        results = await trigger_service.afternoon_closing_strength(test_date, top_n=3)
        print(f"✅ 감지 완료: {len(results)}개 종목")
        if results:
            print(f"\n상위 종목:")
            for i, stock in enumerate(results, 1):
                print(f"  [{i}] {stock['name']} ({stock['ticker']})")
                print(f"      마감강도: {stock['closing_strength']:.3f}")
                print(f"      거래량증가율: {stock['volume_increase_rate']:.1f}%")
    except Exception as e:
        print(f"❌ 실패: {e}")

    print("\n" + "="*70 + "\n")

    print("6. 오후 트리거 3: 횡보주 거래량...")
    try:
        results = await trigger_service.afternoon_sideways_volume(test_date, top_n=3)
        print(f"✅ 감지 완료: {len(results)}개 종목")
        if results:
            print(f"\n상위 종목:")
            for i, stock in enumerate(results, 1):
                print(f"  [{i}] {stock['name']} ({stock['ticker']})")
                print(f"      장중등락률: {stock['intraday_change']:.2f}%")
                print(f"      거래량증가율: {stock['volume_increase_rate']:.1f}%")
        else:
            print("  ⚠️ 횡보 조건에 맞는 종목 없음")
    except Exception as e:
        print(f"❌ 실패: {e}")

    print("\n" + "="*70 + "\n")

    # ============= 통합 실행 테스트 =============

    print("7. 오전 트리거 통합 실행 (run_morning_triggers)...")
    try:
        results = await trigger_service.run_morning_triggers(test_date)

        print(f"✅ 통합 실행 완료")
        print(f"\n트리거별 종목 수:")
        print(f"  - 거래량 급증: {len(results['volume_surge'])}개")
        print(f"  - 갭 상승: {len(results['gap_up'])}개")
        print(f"  - 자금 유입: {len(results['fund_inflow'])}개")

        total = len(results['volume_surge']) + len(results['gap_up']) + len(results['fund_inflow'])
        print(f"\n총 {total}개 종목 감지")

        # 검증
        assert isinstance(results, dict), "결과는 dict 타입이어야 함"
        assert 'volume_surge' in results, "volume_surge 키 필요"
        assert 'gap_up' in results, "gap_up 키 필요"
        assert 'fund_inflow' in results, "fund_inflow 키 필요"

        # Trigger 모델 검증
        if results['volume_surge']:
            first_trigger = results['volume_surge'][0]
            assert hasattr(first_trigger, 'ticker'), "Trigger 모델에 ticker 필드 필요"
            assert hasattr(first_trigger, 'name'), "Trigger 모델에 name 필드 필요"
            assert hasattr(first_trigger, 'trigger_type'), "Trigger 모델에 trigger_type 필드 필요"
            assert first_trigger.trigger_type == 'volume_surge', "trigger_type이 올바르지 않음"
            assert first_trigger.session == 'morning', "session이 morning이어야 함"
            print("\n  ✓ Trigger 모델 검증 통과")

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    print("8. 오후 트리거 통합 실행 (run_afternoon_triggers)...")
    try:
        results = await trigger_service.run_afternoon_triggers(test_date)

        print(f"✅ 통합 실행 완료")
        print(f"\n트리거별 종목 수:")
        print(f"  - 일중 상승: {len(results['intraday_rise'])}개")
        print(f"  - 마감 강도: {len(results['closing_strength'])}개")
        print(f"  - 횡보 거래량: {len(results['sideways_volume'])}개")

        total = len(results['intraday_rise']) + len(results['closing_strength']) + len(results['sideways_volume'])
        print(f"\n총 {total}개 종목 감지")

        # 검증
        assert isinstance(results, dict), "결과는 dict 타입이어야 함"
        assert 'intraday_rise' in results, "intraday_rise 키 필요"
        assert 'closing_strength' in results, "closing_strength 키 필요"
        assert 'sideways_volume' in results, "sideways_volume 키 필요"

        # Trigger 모델 검증
        if results['intraday_rise']:
            first_trigger = results['intraday_rise'][0]
            assert first_trigger.trigger_type == 'intraday_rise', "trigger_type이 올바르지 않음"
            assert first_trigger.session == 'afternoon', "session이 afternoon이어야 함"
            print("\n  ✓ Trigger 모델 검증 통과")

    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("=== 테스트 완료 (8개 함수) ===")


if __name__ == "__main__":
    asyncio.run(test_trigger_service())
