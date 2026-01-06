"""
전체 종목 재무 데이터 Batch 수집 스크립트

모든 상장 종목의 재무 데이터를 DART API로 조회하여 DB에 저장합니다.
- 속도보다 안정성 우선 (천천히 처리)
- 에러 발생 시 기본값으로 저장
- tqdm 진행률 표시
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time
from tqdm.asyncio import tqdm

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.krx_data_client import stock as pykrx_stock
from app.db.database import init_db, get_db
from app.db.models import FinancialData
from app.services.data_service import DataService
from app.utils.filters import StockFilter

def add_market_info():
    """DB의 모든 종목에 market 정보 일괄 추가"""
    print()
    print("=" * 60)
    print("6. Market 정보 일괄 추가")
    print("=" * 60)

    # KOSPI/KOSDAQ 목록 조회 (API 2회만 호출)
    # 전날 데이터 사용 (00:00 실행 시 당일 데이터 없음)
    # 주말 건너뛰기
    print("   시장 정보 조회 중...")
    target_date = datetime.now() - timedelta(days=1)

    # 주말이면 금요일까지 거슬러 올라감
    while target_date.weekday() >= 5:  # 토(5), 일(6)
        target_date -= timedelta(days=1)

    date_str = target_date.strftime("%Y%m%d")
    print(f"   조회 날짜: {target_date.strftime('%Y-%m-%d %a')} (이전 거래일 기준)")

    kospi_set = set(pykrx_stock.get_market_ticker_list(date_str, market="KOSPI"))
    kosdaq_set = set(pykrx_stock.get_market_ticker_list(date_str, market="KOSDAQ"))

    print(f"   KOSPI: {len(kospi_set):,}개, KOSDAQ: {len(kosdaq_set):,}개")

    # DB 업데이트
    kospi_count = 0
    kosdaq_count = 0
    other_count = 0

    with get_db() as db:
        records = db.query(FinancialData).all()

        for record in records:
            ticker = record.ticker

            if ticker in kospi_set:
                record.market = "KOSPI"
                kospi_count += 1
            elif ticker in kosdaq_set:
                record.market = "KOSDAQ"
                kosdaq_count += 1
            else:
                record.market = "기타"
                other_count += 1

    print(f"   완료: KOSPI {kospi_count:,}개, KOSDAQ {kosdaq_count:,}개, 기타 {other_count:,}개")


async def collect_all_financial_data():
    """전체 종목 재무 데이터 수집"""
    print("=" * 80)
    print("전체 종목 재무 데이터 Batch 수집")
    print("=" * 80)
    print()

    # 1. DB 초기화
    print("1. 데이터베이스 초기화...")
    init_db()
    print()

    # 2. 전체 종목 목록 조회
    print("2. 전체 종목 목록 조회...")
    print("   전날 종가 기준으로 필터링 (00:00 실행 시 당일 데이터 없음)")
    data_service = DataService()
    target_date = datetime.now() - timedelta(days=1)
    df = await data_service.get_market_snapshot(target_date)
    print(f"   조회 날짜: {target_date.strftime('%Y-%m-%d')}")

    initial_count = len(df)
    print(f"✅ {initial_count:,}개 종목 발견")
    print()

    # 3. 필터링 적용 (거래대금 5억↑, 시총 500억↑)
    print("3. 필터링 적용 (투자 대상 종목만 선별)...")
    print(f"   - 최소 거래대금: 5억원")
    print(f"   - 최소 시가총액: 500억원")
    print(f"   - 평균 거래량 20% 이상")
    df = StockFilter.apply_absolute_filters(df)

    total_stocks = len(df)
    print(f"✅ {total_stocks:,}개 종목 선정 ({initial_count:,}개 → {total_stocks:,}개, {total_stocks/initial_count*100:.1f}%)")
    print()

    # 4. 기존 데이터 전체 삭제
    print("4. 기존 financial_data 테이블 초기화...")
    with get_db() as db:
        deleted_count = db.query(FinancialData).delete()
        print(f"✅ {deleted_count:,}개 기존 레코드 삭제")
    print()

    # 5. 재무 데이터 수집 및 삽입
    print("5. 재무 데이터 수집 시작 (천천히 처리, 에러 최소화 우선)")
    print("-" * 80)

    success_count = 0
    error_count = 0
    start_time = time.time()

    async def fetch_and_save(ticker: str, market_cap: float, trading_value: float):
        nonlocal success_count, error_count

        try:
            # 종목명 조회 (pykrx)
            try:
                stock_name = pykrx_stock.get_market_ticker_name(ticker)
            except:
                stock_name = ticker

            # 재무 데이터 조회
            financial_data = await data_service.get_financial_data(ticker)

            # DB 저장 (신규 INSERT만)
            with get_db() as db:
                new_data = FinancialData(
                    ticker=ticker,
                    name=stock_name,
                    bps=financial_data.get('bps', 0.0),
                    per=financial_data.get('per', 0.0),
                    pbr=financial_data.get('pbr', 0.0),
                    eps=financial_data.get('eps', 0.0),
                    div=financial_data.get('div', 0.0),
                    dps=financial_data.get('dps', 0.0),
                    roe=financial_data.get('roe', 0.0),
                    debt_ratio=financial_data.get('debt_ratio', 0.0),
                    revenue_growth_yoy=financial_data.get('revenue_growth_yoy', 0.0),
                    market_cap=market_cap / 100000000,  # 원 -> 억원
                    trading_value=trading_value / 100000000,  # 원 -> 억원
                    filter_status='pass',  # 필터 통과
                    last_filter_check_date=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(new_data)

            success_count += 1

        except Exception as e:
            error_count += 1
            # 에러 발생 시 기본값으로 저장
            try:
                stock_name = pykrx_stock.get_market_ticker_name(ticker)
            except:
                stock_name = ticker

            with get_db() as db:
                new_data = FinancialData(
                    ticker=ticker,
                    name=stock_name,
                    bps=0.0,
                    per=0.0,
                    pbr=0.0,
                    eps=0.0,
                    div=0.0,
                    dps=0.0,
                    roe=0.0,
                    debt_ratio=0.0,
                    revenue_growth_yoy=0.0,
                    market_cap=market_cap / 100000000,  # 원 -> 억원
                    trading_value=trading_value / 100000000,  # 원 -> 억원
                    filter_status='pass',  # 필터 통과 (에러 발생해도 필터는 통과한 종목)
                    last_filter_check_date=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(new_data)

    # 순차적으로 한 개씩 처리 (Semaphore 없이)
    from tqdm import tqdm as tqdm_sync

    for idx, row in tqdm_sync(df.iterrows(), total=len(df), desc="재무 데이터 수집", unit="stock"):
        ticker = row.get('ticker', idx)
        market_cap = row.get('시가총액', 0)
        trading_value = row.get('거래대금', 0)

        # 한 개씩 처리
        await fetch_and_save(ticker, market_cap, trading_value)

        # 1초 대기 (KRX 서버 차단 방지)
        await asyncio.sleep(1.0)
        
    # market 정보 일괄 추가
    add_market_info()

    # 7. 결과 요약
    elapsed_total = time.time() - start_time
    print()
    print("=" * 80)
    print("✅ 수집 완료!")
    print("=" * 80)
    print(f"총 종목 수: {total_stocks:,}개")
    print(f"성공: {success_count:,}개 ({success_count/total_stocks*100:.1f}%)")
    print(f"에러 (기본값 저장): {error_count:,}개 ({error_count/total_stocks*100:.1f}%)")
    print(f"총 소요 시간: {elapsed_total:.1f}초 ({elapsed_total/60:.1f}분)")
    print(f"종목당 평균: {elapsed_total/total_stocks*1000:.0f}ms")
    print()

    # 8. DB 통계
    with get_db() as db:
        total_records = db.query(FinancialData).count()
        print(f"💾 DB 저장: {total_records:,}개 레코드")
        print()
        print(f"📊 필터링 효과:")
        print(f"   - 전체 종목: {initial_count:,}개")
        print(f"   - 선정 종목: {total_stocks:,}개")
        print(f"   - 절감률: {(1 - total_stocks/initial_count)*100:.1f}%")
        print(f"   - 예상 소요시간 단축: {(initial_count - total_stocks) / 60:.1f}분")


async def main():
    """메인 실행"""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "Financial Data Batch Collector" + " " * 23 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        await collect_all_financial_data()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단")
    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
