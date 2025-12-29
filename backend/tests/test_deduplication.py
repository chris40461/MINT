"""
중복 제거 함수 검증 테스트 - 다양한 임계값 비교
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.utils.llm_utils import deduplicate_news


def test_multiple_thresholds():
    """여러 임계값으로 중복 제거 테스트"""

    # 테스트 데이터: 실제 수집된 중복 뉴스들 (나눔키오스크 10주년)
    test_news = [
        {'title': '삼성 임직원들의 응원 덕에 한발 뗄 자신감 갖게 됐어요', 'published_at': datetime.now()},
        {'title': '"삼성 직원들이 십시일반 모았다"…삼성, 나눔키오스크 10주년 맞아', 'published_at': datetime.now()},
        {'title': '삼성, 나눔키오스크 10주년 기념 나눔의 날 행사 개최', 'published_at': datetime.now()},
        {'title': '삼성 \'일상의 기부\' 나눔키오스크 10년…누적 기부금 112억원', 'published_at': datetime.now()},
        {'title': '삼성 임직원, 사원증 찍어서 10년간 112억원 기부', 'published_at': datetime.now()},
        {'title': '삼성, \'나눔키오스크 10주년\' 기념 \'2025 나눔의 날\' 행사 개최', 'published_at': datetime.now()},
        {'title': '한번의 터치, 10년긴 112억 모아…"삼성식 기부 문화 더 확대할"', 'published_at': datetime.now()},
        {'title': '삼성, 나눔키오스크 10주년…누적 기부금 112억원', 'published_at': datetime.now()},
        {'title': '삼성 나눔키오스크 10년...112억원 기부로 아동 3770명 지원', 'published_at': datetime.now()},
        {'title': '삼성 임직원, 2주만에 3억 모금…3600명 헌혈 참여', 'published_at': datetime.now()},
        {'title': '"삑! 사원증 태깅으로 누적 112억 기부"…삼성, 나눔키오스크 10주년', 'published_at': datetime.now()},
        {'title': '장애인 위해 쿠키 굽는 삼성전자 부회장…\'일상\'이 된 삼성의 기부', 'published_at': datetime.now()},
        # 다른 주제 뉴스 (비교용)
        {'title': '삼성전자, HBM4 프리미엄 효과 2026년 영업이익 두 배 뛴다', 'published_at': datetime.now()},
        {'title': '삼성전자 사업지원실 M&A팀 신설 추가 빅딜 기대감', 'published_at': datetime.now()},
    ]

    print("=" * 80)
    print("중복 제거 임계값 테스트 (STS 코사인 유사도)")
    print("=" * 80)
    print()

    print(f"원본 뉴스 개수: {len(test_news)}")
    print()

    print("원본 뉴스 제목:")
    for i, news in enumerate(test_news, 1):
        print(f"  {i}. {news['title']}")
    print()

    # 다양한 임계값 테스트
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

    print("=" * 80)
    print("임계값별 중복 제거 결과")
    print("=" * 80)
    print()

    results = {}

    for threshold in thresholds:
        deduplicated = deduplicate_news(test_news, threshold=threshold)
        removed_count = len(test_news) - len(deduplicated)
        results[threshold] = {
            'count': len(deduplicated),
            'removed': removed_count,
            'news': deduplicated
        }

        print(f"임계값 {threshold:.0%} (코사인 유사도):")
        print(f"  - 제거 전: {len(test_news)}개 → 제거 후: {len(deduplicated)}개")
        print(f"  - 제거된 뉴스: {removed_count}개")
        print(f"  - 제거율: {removed_count / len(test_news) * 100:.1f}%")
        print()

    print("=" * 80)
    print("임계값별 결과 요약")
    print("=" * 80)
    print()

    print("임계값 | 남은 뉴스 | 제거된 뉴스 | 제거율")
    print("-" * 80)
    for threshold in thresholds:
        result = results[threshold]
        print(f"  {threshold:.0%}  |    {result['count']}개    |     {result['removed']}개     | {result['removed'] / len(test_news) * 100:5.1f}%")
    print()

    # 권장 임계값 분석
    print("=" * 80)
    print("임계값 추천 분석")
    print("=" * 80)
    print()

    # 0.50 (50%) 결과 상세
    print(f"📌 임계값 50% 결과 (적극적 중복 제거):")
    print(f"   제거 후: {results[0.50]['count']}개")
    for i, news in enumerate(results[0.50]['news'], 1):
        print(f"   {i}. {news['title']}")
    print()

    # 0.65 (65%) 결과 상세
    print(f"📌 임계값 65% 결과 (균형):")
    print(f"   제거 후: {results[0.65]['count']}개")
    for i, news in enumerate(results[0.65]['news'], 1):
        print(f"   {i}. {news['title']}")
    print()

    # 0.70 (70%) 결과 상세 (현재)
    print(f"📌 임계값 70% 결과 (현재 설정):")
    print(f"   제거 후: {results[0.70]['count']}개")
    for i, news in enumerate(results[0.70]['news'], 1):
        print(f"   {i}. {news['title']}")
    print()

    print("=" * 80)
    print("권장 사항")
    print("=" * 80)
    print()
    print("1. 임계값 60% (0.60):")
    print("   ✅ 장점: 비슷한 뉴스를 적극적으로 제거하여 다양성 확보")
    print("   ⚠️  단점: 약간 다른 내용의 뉴스도 제거될 가능성")
    print()
    print("2. 임계값 65% (0.65):")
    print("   ✅ 장점: 균형잡힌 중복 제거")
    print("   ✅ 추천: 대부분의 경우에 적합")
    print()
    print("3. 임계값 70% (0.70) - 현재:")
    print("   ⚠️  단점: 명백히 중복인 뉴스도 일부 남아있음")
    print()

    # 최종 권장
    print("=" * 80)
    print("💡 최종 권장: 임계값 65% (0.65)")
    print("=" * 80)
    print("이유:")
    print("- 중복 뉴스는 효과적으로 제거하면서")
    print("- 다른 관점의 뉴스는 유지")
    print("- 실제 데이터 (252개)에서도 적절한 제거율 기대")
    print()


if __name__ == "__main__":
    test_multiple_thresholds()
