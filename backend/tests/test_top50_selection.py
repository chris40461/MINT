"""
Top 50 선정 테스트 (Momentum, Volume, Technical)

단기 예측 방법론 (학술 근거 기반):
- Momentum (40%): D-1(40%), D-5(35%), D-20(25%) 수익률
- Volume (30%): 거래량 증가율 + 거래대금 (offset + log + percentile)
- Technical (20%): RSI/MACD/MA 기술적 조정
- Sentiment (10%): Top 50 선정 후 뉴스 분석 (별도)
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.services.llm_report import LLMReport
from app.db.database import init_db
import pandas as pd


async def test_top50_selection():
    """Top 50 선정 테스트"""
    print("=" * 80)
    print("Top 50 선정 테스트 시작")
    print("=" * 80)
    print()

    # DB 초기화
    init_db()

    # LLMReport 서비스 생성
    report_service = LLMReport()

    # 테스트 날짜 (최근 거래일)
    test_date = datetime(2025, 11, 14)  # 2025-11-14 (목)
    print(f"테스트 날짜: {test_date.strftime('%Y-%m-%d')}")
    print()

    # Phase 1: Top 50 선정 (센티먼트 분석 제외)
    print("=" * 80)
    print("Phase 1: 3개 점수 계산 및 Top 50 선정")
    print("=" * 80)
    print()

    try:
        # select_top_stocks_for_morning 호출하되, 센티먼트 분석 전까지만 테스트
        # 임시로 _calculate_all_scores까지만 호출
        from app.db.database import get_db
        from app.db.models import FinancialData

        # 1.1: 시장 스냅샷 + DB 데이터 조회
        print("[Step 1.1] 시장 스냅샷 + DB 데이터 조회")
        df_market = await report_service.data_service.get_market_snapshot(test_date)
        print(f"  - 시장 스냅샷: {len(df_market)}개 종목")

        with get_db() as db:
            all_stocks = db.query(FinancialData).all()
            df_financial = pd.DataFrame([stock.to_dict() for stock in all_stocks])
        print(f"  - DB 조회: {len(df_financial)}개 종목")

        df = df_market.merge(df_financial, on='ticker', how='inner')
        print(f"  - Merge: {len(df)}개 종목")

        # 유효성 검증
        df = df[
            (df['per'] > 0) &
            (df['pbr'] > 0) &
            (df['market_cap'] > 0) &
            (df['종가'] > 0)
        ].copy()
        print(f"  - 유효성 검증 후: {len(df)}개 종목")
        print()

        # 1.2-1.4: 3개 점수 계산
        print("[Step 1.2-1.4] 3개 점수 계산 (Momentum, Volume, Technical)")
        df = await report_service._calculate_all_scores(df, test_date)
        print()

        # 점수 통계
        print("=" * 80)
        print("점수 통계")
        print("=" * 80)
        print()

        scores = ['momentum_score', 'volume_score', 'technical_score']
        for score_name in scores:
            if score_name in df.columns:
                mean = df[score_name].mean()
                std = df[score_name].std()
                min_val = df[score_name].min()
                max_val = df[score_name].max()
                print(f"{score_name:20s}: 평균 {mean:5.2f}, 표준편차 {std:4.2f}, 범위 [{min_val:5.2f}, {max_val:5.2f}]")
        print()

        # Top 50 선정 (M:40%, V:30%, T:20%)
        print("[Step 2.1] Top 50 선정 (M:40%, V:30%, T:20%)")
        df['base_score'] = (
            df['momentum_score'] * 0.40 +
            df['volume_score'] * 0.30 +
            df['technical_score'] * 0.20
        )

        top_50 = df.nlargest(50, 'base_score').copy()
        print(f"  - Top 50 평균 점수: {top_50['base_score'].mean():.2f}")
        print()

        # Top 10 출력
        print("=" * 80)
        print("Top 10 종목")
        print("=" * 80)
        print()

        top_10 = top_50.head(10)
        for idx, row in top_10.iterrows():
            print(f"{row['ticker']:6s} | 종합 {row['base_score']:5.2f} | "
                  f"M:{row['momentum_score']:4.1f} V:{row['volume_score']:4.1f} "
                  f"T:{row['technical_score']:4.1f} | "
                  f"종가 {row['종가']:>8,.0f}원 | PER {row['per']:>6.1f} PBR {row['pbr']:>5.2f}")
        print()

        # 점수별 상위 5개 종목
        print("=" * 80)
        print("점수별 상위 5개 종목")
        print("=" * 80)
        print()

        score_names = {
            'momentum_score': 'Momentum',
            'volume_score': 'Volume',
            'technical_score': 'Technical'
        }

        for score_col, score_label in score_names.items():
            print(f"[{score_label} Top 5]")
            top_5 = df.nlargest(5, score_col)
            for idx, row in top_5.iterrows():
                print(f"  {row['ticker']:6s} | {score_label} {row[score_col]:5.2f} | "
                      f"종가 {row['종가']:>8,.0f}원 | {row.get('name', 'N/A')}")
            print()

        # CSV 저장
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_file = data_dir / "top50_test_result.csv"
        top_50.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ Top 50 결과 저장: {output_file}")
        print()

        print("=" * 80)
        print("테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_top50_selection())
