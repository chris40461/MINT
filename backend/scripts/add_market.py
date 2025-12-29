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
from datetime import datetime
import time
from tqdm.asyncio import tqdm

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from pykrx import stock as pykrx_stock
from app.db.database import init_db, get_db
from app.db.models import FinancialData
from app.services.data_service import DataService
from app.utils.filters import StockFilter

def add_market_info():
    """DB의 모든 종목에 market 정보 일괄 추가"""
    print()
    print("=" * 60)
    print("5. Market 정보 일괄 추가")
    print("=" * 60)

    # KOSPI/KOSDAQ 목록 조회 (API 2회만 호출)
    print("   시장 정보 조회 중...")
    date_str = datetime.now().strftime("%Y%m%d")

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


async def main():
    """메인 실행"""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 25 + "Financial Data Batch Collector" + " " * 23 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        add_market_info()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자 중단")
    except Exception as e:
        print(f"\n\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
