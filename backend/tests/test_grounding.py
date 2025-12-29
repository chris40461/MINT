"""
Google Grounding 기능 테스트

LLMReport 서비스의 Google Search Grounding 기능을 테스트합니다.
"""

import asyncio
import sys
import os
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.llm_report import LLMReport


async def test_grounding():
    """
    Google Grounding 기능 통합 테스트

    검증 사항:
    - API 호출 성공
    - 텍스트 생성 확인
    - 토큰 사용량 추적
    - 에러 핸들링
    """
    print("=" * 80)
    print("Google Grounding 기능 테스트")
    print("=" * 80)
    print()

    # 서비스 초기화
    print("🔧 LLMReport 서비스 초기화 중...")
    service = LLMReport()
    print("✅ LLMReport 초기화 완료")
    print()

    # 테스트 프롬프트 (시장 분석용)
    test_prompt = """
오늘(2025년 11월 13일) 글로벌 경제와 금융시장에 영향을 미칠 주요 뉴스와 이벤트를 요약하세요.

특히 다음 항목에 주목하세요:
1. 미국 연준(Fed)의 통화정책 관련 소식
2. 주요 기술주(테슬라, 애플, 엔비디아 등) 동향
3. 국제 유가 및 원자재 가격
4. 한국 경제에 직접적인 영향을 미칠 이슈

각 항목을 간략히 요약하고, 한국 주식시장에 미칠 영향을 분석하세요.
"""

    print("📡 Google Grounding을 사용한 검색 시작...")
    print("-" * 80)
    print("프롬프트:")
    print(test_prompt)
    print("-" * 80)
    print()

    try:
        # Grounding 호출
        result = await service._generate_with_grounding(test_prompt)

        # 결과 출력
        print("✅ Grounding 호출 성공!")
        print()
        print("=" * 80)
        print("📄 생성된 텍스트")
        print("=" * 80)
        print(result['text'])
        print()

        # 메타데이터 출력
        print("=" * 80)
        print("🔍 Grounding 메타데이터")
        print("=" * 80)
        if result.get('search_queries'):
            print(f"검색 쿼리 ({len(result['search_queries'])}개):")
            for i, query in enumerate(result['search_queries'], 1):
                print(f"  {i}. {query}")
            print()

        if result.get('sources'):
            print(f"참고 출처 ({len(result['sources'])}개):")
            for i, source in enumerate(result['sources'], 1):
                print(f"  {i}. {source}")
            print()

        if not result.get('search_queries') and not result.get('sources'):
            print("⚠️  메타데이터 추출 미구현 (TODO)")
            print("   - 새 SDK에서 Grounding 메타데이터 추출 방법 확인 필요")
            print()

        # 비용 정보
        print("=" * 80)
        print("💰 LLM 비용 리포트")
        print("=" * 80)
        cost_report = service.cost_tracker.get_daily_report()
        print(f"입력 토큰:  {cost_report['input_tokens']:,} tokens")
        print(f"출력 토큰:  {cost_report['output_tokens']:,} tokens")
        print(f"예상 비용:  ${cost_report['total_cost_usd']:.4f} (약 ₩{int(cost_report['total_cost_krw'])})")
        print()

        # Grounding 추가 비용 안내
        print("📌 Google Grounding 추가 비용: $0.035/request (검색 횟수와 무관)")
        print(f"   총 예상 비용: ${cost_report['total_cost_usd'] + 0.035:.4f}")
        print()

        print("=" * 80)
        print("✅ 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Grounding 호출 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_basic_generation():
    """
    기본 텍스트 생성 테스트 (Grounding 없음)

    비교를 위해 Grounding 없이 동일한 프롬프트 실행
    """
    print()
    print("=" * 80)
    print("기본 텍스트 생성 테스트 (Grounding 없음, 비교용)")
    print("=" * 80)
    print()

    service = LLMReport()

    test_prompt = "2025년 11월 13일 글로벌 금융시장 동향을 간략히 요약하세요."

    try:
        result = await service.generate(test_prompt)

        print("✅ 기본 생성 성공!")
        print()
        print("📄 생성된 텍스트:")
        print(result)
        print()

        # 비용 정보
        cost_report = service.cost_tracker.get_daily_report()
        print("💰 비용:")
        print(f"   ${cost_report['total_cost_usd']:.4f} (Grounding 비용 없음)")
        print()

        return True

    except Exception as e:
        print(f"❌ 기본 생성 실패: {e}")
        return False


async def main():
    """메인 테스트 실행"""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "LLMReport Grounding 테스트 스위트" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Test 1: Grounding 기능
    success1 = await test_grounding()

    # Test 2: 기본 생성 (비교용)
    success2 = await test_basic_generation()

    # 최종 결과
    print()
    print("=" * 80)
    print("🏁 테스트 결과")
    print("=" * 80)
    print(f"Grounding 테스트: {'✅ 통과' if success1 else '❌ 실패'}")
    print(f"기본 생성 테스트: {'✅ 통과' if success2 else '❌ 실패'}")
    print()

    if success1 and success2:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️  일부 테스트 실패")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
