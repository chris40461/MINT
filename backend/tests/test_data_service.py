"""
DataService 테스트 스크립트
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.data_service import DataService


async def test_data_service():
    service = DataService()

    print("=== DataService 테스트 시작 ===\n")

    # 1. 시장 스냅샷 테스트
    print("1. 시장 스냅샷 테스트 (오늘)...")
    try:
        df = await service.get_market_snapshot(datetime.now())
        print(f"✅ 조회 성공: {len(df)}개 종목")
        print(f"\n컬럼: {df.columns.tolist()}")
        print(f"\n상위 3개 종목:")
        print(df.head(3))
        print(f"\n데이터 타입:")
        print(df.dtypes)
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 2. 종목 정보 테스트 (삼성전자)
    print("2. 종목 정보 테스트 (삼성전자 005930)...")
    try:
        info = await service.get_stock_info("005930")
        print(f"✅ 조회 성공")
        for key, value in info.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 3. 가격 히스토리 테스트
    print("3. 가격 히스토리 테스트 (삼성전자, 최근 10일)...")
    try:
        start = datetime.now() - timedelta(days=10)
        history = await service.get_price_history("005930", start)
        print(f"✅ 조회 성공: {len(history)}일치 데이터")
        print(f"\n컬럼: {history.columns.tolist()}")
        print(f"\n최근 5일 데이터:")
        print(history.tail(5))
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 4. 전 거래일 찾기 테스트
    print("4. 전 거래일 찾기 테스트...")
    try:
        prev_day = await service.get_previous_trading_day(datetime.now())
        print(f"✅ 조회 성공: {prev_day.strftime('%Y-%m-%d')}")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 5. 기술적 지표 테스트 (새로 구현)
    print("5. 기술적 지표 테스트 (삼성전자)...")
    try:
        indicators = await service.get_technical_indicators("005930", datetime.now())
        print(f"✅ 조회 성공")
        for key, value in indicators.items():
            print(f"  {key}: {value}")

        # 검증
        assert 0 <= indicators['rsi'] <= 100, "RSI는 0-100 범위여야 함"
        assert indicators['macd_status'] in ['golden_cross', 'dead_cross', 'neutral'], "MACD 상태 오류"
        assert indicators['ma_position'] in ['상회', '하회', '중립'], "MA 위치 오류"
        print("  ✓ 모든 검증 통과")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 6. 시장 지수 테스트 (KOSPI + KOSDAQ + 수급 + 시장폭)
    print("6. 시장 지수 테스트 (KOSPI + KOSDAQ + 수급 + 시장폭)...")
    try:
        index = await service.get_market_index(datetime.now())
        print(f"✅ 조회 성공")

        print("\n  ■ KOSPI")
        print(f"    종가: {index['kospi_close']:,.2f}")
        print(f"    등락률: {index['kospi_change']:+.2f}%")
        print(f"    포인트: {index['kospi_point_change']:+.2f}p")

        print("\n  ■ KOSDAQ")
        print(f"    종가: {index['kosdaq_close']:,.2f}")
        print(f"    등락률: {index['kosdaq_change']:+.2f}%")
        print(f"    포인트: {index['kosdaq_point_change']:+.2f}p")

        print(f"\n  ■ 거래대금: {index['trading_value'] // 100000000:,}억원")

        print("\n  ■ 수급 (KOSPI)")
        print(f"    외국인: {index['foreign_net_kospi'] // 100000000:+,}억원")
        print(f"    기관: {index['institution_net_kospi'] // 100000000:+,}억원")
        print(f"    개인: {index['individual_net_kospi'] // 100000000:+,}억원")

        print("\n  ■ 수급 (KOSDAQ)")
        print(f"    외국인: {index['foreign_net_kosdaq'] // 100000000:+,}억원")
        print(f"    기관: {index['institution_net_kosdaq'] // 100000000:+,}억원")
        print(f"    개인: {index['individual_net_kosdaq'] // 100000000:+,}억원")

        print("\n  ■ 시장 폭")
        print(f"    상승: {index['advance_count']:,}개")
        print(f"    하락: {index['decline_count']:,}개")
        print(f"    보합: {index['unchanged_count']:,}개")

        # 검증
        assert isinstance(index['kospi_close'], float), "KOSPI 종가는 float여야 함"
        assert isinstance(index['kosdaq_close'], float), "KOSDAQ 종가는 float여야 함"
        assert isinstance(index['trading_value'], int), "거래대금은 int여야 함"
        assert isinstance(index['advance_count'], int), "상승종목수는 int여야 함"
        print("\n  ✓ 모든 검증 통과")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 7. 뉴스 데이터 테스트 (새로 구현)
    print("7. 뉴스 데이터 테스트 (삼성전자, 최근 7일)...")
    try:
        news = await service.get_news_data("005930", days=7)
        print(f"✅ 조회 성공: {len(news)}개 뉴스")

        if news:
            print(f"\n최신 뉴스 3개:")
            for i, item in enumerate(news[:3], 1):
                print(f"\n  [{i}] {item['title']}")
                print(f"      출처: {item['source']}")
                print(f"      날짜: {item['published_at'].strftime('%Y-%m-%d %H:%M')}")

            # 검증
            assert all('title' in item for item in news), "모든 뉴스에 제목 필요"
            assert all('published_at' in item for item in news), "모든 뉴스에 날짜 필요"
            print("\n  ✓ 모든 검증 통과")
        else:
            print("  ⚠️ 뉴스 없음 (휴일 또는 크롤링 제한)")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70 + "\n")

    # 8. 재무 데이터 테스트 (DART API 연동)
    print("8. 재무 데이터 테스트 (삼성전자)...")
    try:
        financial = await service.get_financial_data("005930")

        # 실제 값이 있는지 확인
        has_real_data = any(v != 0.0 for v in financial.values())

        if has_real_data:
            print(f"✅ 조회 성공 (DART API)")
        else:
            print(f"✅ 조회 성공 (기본값)")

        for key, value in financial.items():
            print(f"  {key}: {value}")

        # 검증
        assert 'roe' in financial, "ROE 필드 필요"
        assert 'per' in financial, "PER 필드 필요"
        assert 'pbr' in financial, "PBR 필드 필요"
        print("  ✓ 모든 검증 통과")

        if not has_real_data:
            print("  ⚠️ DART API 키 미설정으로 기본값 반환")
    except Exception as e:
        print(f"❌ 실패: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*70)
    print("=== 테스트 완료 (8개 함수) ===")


if __name__ == "__main__":
    asyncio.run(test_data_service())
