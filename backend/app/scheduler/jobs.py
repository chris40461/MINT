"""
스케줄러 작업 정의

APScheduler를 사용하여 정기 작업을 자동으로 실행합니다.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime
import sys
from pathlib import Path

from app.api.dependencies import get_trigger_service, get_report_service, get_data_service, get_analysis_service

logger = logging.getLogger(__name__)

# 글로벌 스케줄러 인스턴스
scheduler = AsyncIOScheduler()


# ============= 작업 함수 =============

async def run_morning_triggers_job():
    """오전 트리거 실행 (09:10, 평일)"""
    try:
        logger.info("⏰ [오전 트리거] 시작")
        trigger_service = get_trigger_service()
        today = datetime.now()

        results = await trigger_service.run_morning_triggers(today)
        total = sum(len(v) for v in results.values())

        logger.info(f"✅ [오전 트리거] 완료 - {total}개 종목 감지")
    except Exception as e:
        logger.error(f"❌ [오전 트리거] 실패: {e}", exc_info=True)


async def run_afternoon_triggers_job():
    """오후 트리거 실행 (15:30, 평일)"""
    try:
        logger.info("⏰ [오후 트리거] 시작")
        trigger_service = get_trigger_service()
        today = datetime.now()

        results = await trigger_service.run_afternoon_triggers(today)
        total = sum(len(v) for v in results.values())

        logger.info(f"✅ [오후 트리거] 완료 - {total}개 종목 감지")

        # 급등/급락 10% 이상 종목 캐시 무효화
        await check_surge_and_invalidate_cache_job()

    except Exception as e:
        logger.error(f"❌ [오후 트리거] 실패: {e}", exc_info=True)


async def check_surge_and_invalidate_cache_job():
    """
    급등/급락 10% 이상 종목의 분석 캐시 무효화

    장 마감 후 10% 이상 등락한 종목의 분석 캐시를 무효화하여
    다음 분석 요청 시 최신 데이터로 재생성되도록 함
    """
    try:
        logger.info("⏰ [캐시 무효화] 급등/급락 10% 체크 시작")

        data_service = get_data_service()
        analysis_service = get_analysis_service()
        today = datetime.now()

        # 필터 통과 종목 실시간 가격 조회 (직접 쿼리 패턴)
        try:
            from app.db.database import get_db
            from app.db.models import FinancialData

            # 1. 필터 통과 종목 조회
            with get_db() as db:
                tickers = [row.ticker for row in db.query(FinancialData).filter_by(filter_status='pass').all()]

            if not tickers:
                logger.warning("[캐시 무효화] 필터 통과 종목 없음")
                return

            logger.debug(f"[캐시 무효화] {len(tickers)}개 종목 조회 시작")

            # 2. 실시간 가격 배치 조회
            realtime_prices = await data_service.get_realtime_prices_bulk(tickers)

            if not realtime_prices:
                logger.warning("[캐시 무효화] 실시간 가격 데이터 없음")
                return

            # 3. 10% 이상 급등/급락 필터링
            surge_tickers = []
            plunge_tickers = []

            for ticker, price_data in realtime_prices.items():
                change_rate = price_data.get('change_rate', 0.0)
                if change_rate >= 10.0:
                    surge_tickers.append(ticker)
                elif change_rate <= -10.0:
                    plunge_tickers.append(ticker)

            all_extreme_tickers = surge_tickers + plunge_tickers

            if not all_extreme_tickers:
                logger.info("[캐시 무효화] 10% 이상 급등/급락 종목 없음")
                return

            logger.info(f"[캐시 무효화] 급등 {len(surge_tickers)}개, 급락 {len(plunge_tickers)}개 감지")

            # 4. 캐시 무효화
            invalidated_count = 0
            for ticker in all_extreme_tickers:
                try:
                    price_data = realtime_prices[ticker]
                    current_price = price_data['current_price']
                    change_rate = price_data['change_rate']

                    # check_analysis_trigger 호출
                    should_invalidate = await analysis_service.check_analysis_trigger(
                        ticker=ticker,
                        current_price=current_price,
                        change_rate=change_rate
                    )

                    if should_invalidate:
                        await analysis_service.invalidate_cache(ticker)
                        invalidated_count += 1
                        direction = "급등" if change_rate > 0 else "급락"
                        logger.info(f"  📌 {ticker} 캐시 무효화 ({direction} {change_rate:+.1f}%)")

                except Exception as e:
                    logger.warning(f"  ⚠️ {ticker} 캐시 무효화 실패: {e}")

            logger.info(f"✅ [캐시 무효화] 완료 - {invalidated_count}개 종목 캐시 무효화")

        except Exception as e:
            logger.warning(f"[캐시 무효화] 실시간 가격 조회 실패: {e}")

    except Exception as e:
        logger.error(f"❌ [캐시 무효화] 실패: {e}", exc_info=True)


async def generate_morning_report_job():
    """장 시작 리포트 생성 (08:00, 평일)"""
    try:
        logger.info("⏰ [장 시작 리포트] 생성 시작")
        report_service = get_report_service()
        today = datetime.now()

        report = await report_service.generate_morning_report(today)

        # DB에 저장
        from app.db.database import get_db
        from app.db.models import ReportResult
        import json

        with get_db() as db:
            date_str = today.strftime('%Y-%m-%d')

            # 기존 리포트 확인
            existing = db.query(ReportResult).filter(
                ReportResult.date == date_str,
                ReportResult.report_type == 'morning'
            ).first()

            if existing:
                # 업데이트
                existing.content = json.dumps(report, ensure_ascii=False)
                existing.generated_at = datetime.now()
                logger.info(f"📝 [장 시작 리포트] DB 업데이트")
            else:
                # 신규 생성
                new_report = ReportResult(
                    date=date_str,
                    report_type='morning',
                    content=json.dumps(report, ensure_ascii=False),
                    generated_at=datetime.now()
                )
                db.add(new_report)
                logger.info(f"📝 [장 시작 리포트] DB 저장")

        logger.info(f"✅ [장 시작 리포트] 생성 완료")
    except Exception as e:
        logger.error(f"❌ [장 시작 리포트] 생성 실패: {e}", exc_info=True)


async def generate_afternoon_report_job():
    """장 마감 리포트 생성 (15:40, 평일)"""
    try:
        logger.info("⏰ [장 마감 리포트] 생성 시작")

        # 서비스 초기화
        trigger_service = get_trigger_service()
        data_service = get_data_service()
        report_service = get_report_service()
        today = datetime.now()

        # 1. 오후 트리거 결과 조회 (DB에서)
        from app.db.database import get_db
        from app.db.models import TriggerResult, ReportResult
        import json

        date_str = today.strftime('%Y-%m-%d')

        # 급등주 리스트 생성 (세션 안에서 dict 변환)
        surge_stocks = []
        with get_db() as db:
            afternoon_triggers = db.query(TriggerResult).filter(
                TriggerResult.date == date_str,
                TriggerResult.session == 'afternoon'
            ).all()

            # 세션이 열려있을 때 dict로 변환
            for trigger in afternoon_triggers:
                surge_stocks.append({
                    'ticker': trigger.ticker,
                    'name': trigger.name,
                    'change_rate': trigger.change_rate,
                    'trigger_type': trigger.trigger_type,
                    'composite_score': trigger.composite_score
                })

        logger.info(f"오후 트리거 종목 {len(surge_stocks)}개 조회 완료")

        # 2. 시장 요약 데이터 수집 (확장된 형식)
        try:
            market_data = await data_service.get_market_index(today)
            # ExtendedMarketSummary 형식에 맞게 변환 (억원 단위)
            market_summary = {
                # KOSPI
                'kospi_close': market_data.get('kospi_close', 0.0),
                'kospi_change': market_data.get('kospi_change', 0.0),
                'kospi_point_change': market_data.get('kospi_point_change', 0.0),
                # KOSDAQ
                'kosdaq_close': market_data.get('kosdaq_close', 0.0),
                'kosdaq_change': market_data.get('kosdaq_change', 0.0),
                'kosdaq_point_change': market_data.get('kosdaq_point_change', 0.0),
                # 거래대금 (원 -> 억원)
                'trading_value': int(market_data.get('trading_value', 0) // 100000000),
                # 수급 - KOSPI (원 -> 억원)
                'foreign_net_kospi': int(market_data.get('foreign_net_kospi', 0) // 100000000),
                'institution_net_kospi': int(market_data.get('institution_net_kospi', 0) // 100000000),
                'individual_net_kospi': int(market_data.get('individual_net_kospi', 0) // 100000000),
                # 수급 - KOSDAQ (원 -> 억원)
                'foreign_net_kosdaq': int(market_data.get('foreign_net_kosdaq', 0) // 100000000),
                'institution_net_kosdaq': int(market_data.get('institution_net_kosdaq', 0) // 100000000),
                'individual_net_kosdaq': int(market_data.get('individual_net_kosdaq', 0) // 100000000),
                # 시장 폭
                'advance_count': market_data.get('advance_count', 0),
                'decline_count': market_data.get('decline_count', 0),
                'unchanged_count': market_data.get('unchanged_count', 0)
            }
            logger.info(f"시장 요약 데이터 수집 완료: KOSPI {market_summary['kospi_close']} ({market_summary['kospi_change']:+.2f}%), "
                       f"KOSDAQ {market_summary['kosdaq_close']} ({market_summary['kosdaq_change']:+.2f}%)")
        except Exception as e:
            logger.warning(f"시장 요약 데이터 수집 실패 (기본값 사용): {e}")
            market_summary = {
                'kospi_close': 0.0, 'kospi_change': 0.0, 'kospi_point_change': 0.0,
                'kosdaq_close': 0.0, 'kosdaq_change': 0.0, 'kosdaq_point_change': 0.0,
                'trading_value': 0,
                'foreign_net_kospi': 0, 'institution_net_kospi': 0, 'individual_net_kospi': 0,
                'foreign_net_kosdaq': 0, 'institution_net_kosdaq': 0, 'individual_net_kosdaq': 0,
                'advance_count': 0, 'decline_count': 0, 'unchanged_count': 0
            }

        # 3. 장 마감 리포트 생성
        report = await report_service.generate_afternoon_report(today, market_summary, surge_stocks)

        # 4. DB에 저장
        with get_db() as db:
            # 기존 리포트 확인
            existing = db.query(ReportResult).filter(
                ReportResult.date == date_str,
                ReportResult.report_type == 'afternoon'
            ).first()

            if existing:
                # 업데이트
                existing.content = json.dumps(report, ensure_ascii=False)
                existing.generated_at = datetime.now()
                logger.info(f"📝 [장 마감 리포트] DB 업데이트")
            else:
                # 신규 생성
                new_report = ReportResult(
                    date=date_str,
                    report_type='afternoon',
                    content=json.dumps(report, ensure_ascii=False),
                    generated_at=datetime.now()
                )
                db.add(new_report)
                logger.info(f"📝 [장 마감 리포트] DB 저장")

        logger.info(f"✅ [장 마감 리포트] 생성 완료")
    except Exception as e:
        logger.error(f"❌ [장 마감 리포트] 생성 실패: {e}", exc_info=True)


async def batch_collect_financial_data_job():
    """재무 데이터 배치 수집 (00:00, 매일)"""
    try:
        logger.info("⏰ [재무 데이터 배치] 수집 시작")

        # scripts/batch_collect_financial_data.py의 함수 import
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        from batch_collect_financial_data import collect_all_financial_data

        await collect_all_financial_data()

        logger.info(f"✅ [재무 데이터 배치] 수집 완료")
    except Exception as e:
        logger.error(f"❌ [재무 데이터 배치] 수집 실패: {e}", exc_info=True)


# ============= 스케줄러 관리 =============

def start_scheduler():
    """스케줄러 시작 및 작업 등록"""

    # 1. 장 시작 리포트 (08:00, 평일)
    scheduler.add_job(
        func=generate_morning_report_job,
        trigger=CronTrigger(
            day_of_week='mon-fri',  # 월~금
            hour=8,
            minute=0
        ),
        id='morning_report',
        name='장 시작 리포트 생성',
        replace_existing=True
    )

    # 2. 오전 트리거 (09:10, 평일)
    scheduler.add_job(
        func=run_morning_triggers_job,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=9,
            minute=10
        ),
        id='morning_triggers',
        name='오전 트리거 실행',
        replace_existing=True
    )

    # 3. 오후 트리거 (15:00, 평일)
    scheduler.add_job(
        func=run_afternoon_triggers_job,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=15,
            minute=0
        ),
        id='afternoon_triggers',
        name='오후 트리거 실행',
        replace_existing=True
    )

    # 4. 장 마감 리포트 (15:40, 평일)
    scheduler.add_job(
        func=generate_afternoon_report_job,
        trigger=CronTrigger(
            day_of_week='mon-fri',
            hour=15,
            minute=40
        ),
        id='afternoon_report',
        name='장 마감 리포트 생성',
        replace_existing=True
    )

    # 5. 재무 데이터 배치 수집 (00:00, 매일)
    scheduler.add_job(
        func=batch_collect_financial_data_job,
        trigger=CronTrigger(
            hour=0,
            minute=0
        ),
        id='batch_financial_data',
        name='재무 데이터 배치 수집',
        replace_existing=True
    )

    # 스케줄러 시작
    scheduler.start()
    logger.info("📅 스케줄러 시작됨")

    # 등록된 작업 출력
    jobs = scheduler.get_jobs()
    logger.info(f"📋 등록된 작업: {len(jobs)}개")
    for job in jobs:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "없음"
        logger.info(f"  - {job.name} (다음 실행: {next_run})")


def stop_scheduler():
    """스케줄러 정리"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("📅 스케줄러 종료됨")
