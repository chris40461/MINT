"""
센티먼트 분석 테스트 (Phase 2.2/2.3)

Top 50 선정 후 뉴스 센티먼트 분석 및 최종 Top 10 선정 테스트
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


async def test_sentiment_analysis():
    """센티먼트 분석 테스트 (Phase 2.2/2.3)"""
    print("=" * 80)
    print("센티먼트 분석 테스트 시작")
    print("=" * 80)
    print()

    # DB 초기화
    init_db()

    # LLMReport 서비스 생성
    report_service = LLMReport()

    # 테스트 날짜
    test_date = datetime(2025, 11, 14)
    print(f"테스트 날짜: {test_date.strftime('%Y-%m-%d')}")
    print()

    try:
        # Phase 1: Top 50 선정 (센티먼트 제외)
        print("=" * 80)
        print("Phase 1: Top 50 선정 (M:40%, V:30%, T:20%)")
        print("=" * 80)
        print()

        # select_top_stocks_for_morning 호출하되, 센티먼트 분석 전까지만
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

        # Top 50 선정
        print("[Step 2.1] Top 50 선정 (M:40%, V:30%, T:20%)")
        df['base_score'] = (
            df['momentum_score'] * 0.40 +
            df['volume_score'] * 0.30 +
            df['technical_score'] * 0.20
        )

        top_50 = df.nlargest(50, 'base_score').copy()
        print(f"  - Top 50 평균 base_score: {top_50['base_score'].mean():.2f}")
        print()

        # Phase 2.2: 뉴스 크롤링 + STS 중복 제거
        print("=" * 80)
        print("Phase 2.2: 50개 종목 뉴스 크롤링 + STS 중복 제거")
        print("=" * 80)
        print()

        news_by_ticker = await report_service._crawl_and_deduplicate_news(top_50)

        # 통계 출력
        total_news = sum(len(news_list) for news_list in news_by_ticker.values())
        stocks_with_news = sum(1 for news_list in news_by_ticker.values() if len(news_list) > 0)
        print(f"  - 뉴스 있는 종목: {stocks_with_news}/50개")
        print(f"  - 총 뉴스 개수 (중복 제거 후): {total_news}개")
        print(f"  - 평균 뉴스 개수: {total_news / 50:.1f}개/종목")
        print()

        # Phase 2.3: LLM 센티먼트 순위 분석
        print("=" * 80)
        print("Phase 2.3: LLM 센티먼트 순위 분석 (1-50위)")
        print("=" * 80)
        print()

        sentiment_ranks = await report_service._analyze_sentiment_batch_all(news_by_ticker)
        print(f"  - 순위 분석 완료: {len(sentiment_ranks)}개 종목")
        print()

        # 순위 → 점수 변환
        sentiment_scores = report_service._convert_ranks_to_scores(sentiment_ranks)

        # 상위 5개 종목 출력
        print("센티먼트 Top 5:")
        sorted_sentiment = sorted(sentiment_scores.items(), key=lambda x: x[1], reverse=True)
        for i, (ticker, score) in enumerate(sorted_sentiment[:5], 1):
            rank = sentiment_ranks.get(ticker, 25)
            name = top_50[top_50['ticker'] == ticker]['name'].values[0] if len(top_50[top_50['ticker'] == ticker]) > 0 else 'N/A'
            print(f"  {i}. {ticker} ({name}): Rank {rank} → Score {score:.2f}")
        print()

        # Phase 2.4: 최종 점수 통합
        print("=" * 80)
        print("Phase 2.4: 최종 점수 통합 (base 90% + sentiment 10%)")
        print("=" * 80)
        print()

        top_50['sentiment_score'] = top_50['ticker'].map(sentiment_scores).fillna(5.0)
        top_50['final_score'] = (
            top_50['base_score'] * 0.90 +
            top_50['sentiment_score'] * 0.10
        )

        top_10 = top_50.nlargest(10, 'final_score')
        print(f"  - Top 10 평균 final_score: {top_10['final_score'].mean():.2f}")
        print()

        # Top 10 출력
        print("=" * 80)
        print("최종 Top 10 (센티먼트 통합)")
        print("=" * 80)
        print()

        for idx, row in top_10.iterrows():
            print(f"{row['ticker']:6s} | 최종 {row['final_score']:5.2f} | "
                  f"Base {row['base_score']:5.2f} (M:{row['momentum_score']:4.1f} V:{row['volume_score']:4.1f} T:{row['technical_score']:4.1f}) | "
                  f"Sentiment {row['sentiment_score']:4.2f} | "
                  f"{row.get('name', 'N/A')}")
        print()

        # CSV 저장
        data_dir = Path(__file__).parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_file = data_dir / "top10_final_result.csv"
        top_10.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"✅ Top 10 결과 저장: {output_file}")
        print()

        print("=" * 80)
        print("테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_sentiment_analysis())
