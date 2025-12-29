# 참고: docs/architecture/01-system-overview.md
# 참고: docs/architecture/03-api-design.md

"""
SKKU-INSIGHT FastAPI 애플리케이션

장 시작/마감 리포트, 급등주 감지, 기업 분석을 제공하는 API 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.scheduler import start_scheduler, stop_scheduler

# 로거 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 앱의 생명주기 관리

    시작 시: 스케줄러 시작 + 놓친 배치 작업 실행
    종료 시: 스케줄러 정리
    """
    import asyncio
    from datetime import datetime, time
    from app.scheduler.jobs import batch_collect_financial_data_job
    from app.db.database import get_db
    from app.db.models import FinancialData

    # 앱 시작
    logger.info("🚀 SKKU-INSIGHT 애플리케이션 시작")

    # 스케줄러 시작 (개발 환경에서도 실행)
    if settings.SCHEDULER_ENABLED:
        start_scheduler()

        # 서버 시작 시 놓친 작업들 실행
        async def run_missed_jobs():
            """
            서버 시작 시 놓친 스케줄 작업들을 체크하고 실행

            [스케줄 시간]
            - 00:00 (매일): 재무 데이터 배치 수집
            - 08:00 (평일): 장 시작 리포트
            - 09:10 (평일): 오전 트리거
            - 15:30 (평일): 오후 트리거
            - 15:40 (평일): 장 마감 리포트

            [실행 로직]
            - 재무 데이터: 가장 최근 데이터의 날짜가 오늘이 아니면 실행
            - 트리거/리포트: 오늘 스케줄 시간 이후 + DB에 해당 날짜 데이터 없으면 실행
            """
            try:
                from app.scheduler.jobs import (
                    run_morning_triggers_job,
                    run_afternoon_triggers_job,
                    generate_morning_report_job,
                    generate_afternoon_report_job,
                )
                from app.db.models import TriggerResult, ReportResult

                # ===== 시간 변수 정의 =====
                now = datetime.now()  # 현재 시각 (datetime 객체, 시간 포함)
                today_date = now.date()  # 오늘 날짜 (date 객체, 날짜만)
                today_str = today_date.strftime('%Y-%m-%d')  # 오늘 날짜 문자열
                is_weekday = now.weekday() < 5  # 평일 여부 (0=월, 4=금, 5=토, 6=일)

                logger.info(
                    f"📅 놓친 작업 체크 시작\n"
                    f"   현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"   오늘 날짜: {today_str}\n"
                    f"   평일 여부: {is_weekday}"
                )

                # ============= 1. 재무 데이터 배치 (00:00, 매일) =============
                logger.info("--- [1/5] 재무 데이터 배치 체크 시작 ---")

                with get_db() as db:
                    # 가장 최근 업데이트된 재무 데이터 조회
                    latest_financial_data = db.query(FinancialData).order_by(
                        FinancialData.updated_at.desc()
                    ).first()

                    # 데이터가 없거나, 마지막 업데이트 날짜가 오늘이 아니면 실행
                    if latest_financial_data is None:
                        logger.info("📊 재무 데이터가 DB에 없음 → 배치 수집 실행")
                        await batch_collect_financial_data_job()
                    elif latest_financial_data.updated_at.date() < today_date:
                        logger.info(
                            f"📊 재무 데이터 오래됨 (마지막 업데이트: {latest_financial_data.updated_at.date()}) "
                            f"→ 배치 수집 실행"
                        )
                        await batch_collect_financial_data_job()
                    else:
                        logger.info(
                            f"✅ 재무 데이터 최신 상태 (마지막 업데이트: {latest_financial_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')})"
                        )

                # ============= 2. 트리거/리포트 체크 (평일만) =============
                if not is_weekday:
                    logger.info("📅 오늘은 주말 → 트리거/리포트 체크 스킵")
                    logger.info("✅ 놓친 작업 체크 완료")
                    return

                logger.info("📅 오늘은 평일 → 트리거/리포트 체크 진행")

                # --- [2/5] 장 시작 리포트 (08:00, 평일) ---
                logger.info("--- [2/5] 장 시작 리포트 체크 시작 ---")
                morning_report_time = datetime.combine(today_date, time(8, 0))  # 오늘 08:00

                if now >= morning_report_time:
                    with get_db() as db:
                        morning_report = db.query(ReportResult).filter(
                            ReportResult.date == today_str,
                            ReportResult.report_type == 'morning'
                        ).first()

                        if morning_report is None:
                            logger.info(f"📰 오늘({today_str}) 장 시작 리포트 없음 → 생성 실행")
                            await generate_morning_report_job()
                        else:
                            logger.info(
                                f"✅ 장 시작 리포트 존재 (생성 시각: {morning_report.generated_at.strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                else:
                    logger.info(f"⏳ 아직 스케줄 시간 전 (08:00 > {now.strftime('%H:%M:%S')})")

                # --- [3/5] 오전 트리거 (09:10, 평일) ---
                logger.info("--- [3/5] 오전 트리거 체크 시작 ---")
                morning_trigger_time = datetime.combine(today_date, time(9, 10))  # 오늘 09:10

                if now >= morning_trigger_time:
                    with get_db() as db:
                        morning_trigger_count = db.query(TriggerResult).filter(
                            TriggerResult.date == today_str,
                            TriggerResult.session == 'morning'
                        ).count()

                        if morning_trigger_count == 0:
                            logger.info(f"🔔 오늘({today_str}) 오전 트리거 없음 → 실행")
                            await run_morning_triggers_job()
                        else:
                            logger.info(f"✅ 오전 트리거 존재 ({morning_trigger_count}개 종목)")
                else:
                    logger.info(f"⏳ 아직 스케줄 시간 전 (09:10 > {now.strftime('%H:%M:%S')})")

                # --- [4/5] 오후 트리거 (15:30, 평일) ---
                logger.info("--- [4/5] 오후 트리거 체크 시작 ---")
                afternoon_trigger_time = datetime.combine(today_date, time(15, 30))  # 오늘 15:30

                if now >= afternoon_trigger_time:
                    with get_db() as db:
                        afternoon_trigger_count = db.query(TriggerResult).filter(
                            TriggerResult.date == today_str,
                            TriggerResult.session == 'afternoon'
                        ).count()

                        if afternoon_trigger_count == 0:
                            logger.info(f"🔔 오늘({today_str}) 오후 트리거 없음 → 실행")
                            await run_afternoon_triggers_job()
                        else:
                            logger.info(f"✅ 오후 트리거 존재 ({afternoon_trigger_count}개 종목)")
                else:
                    logger.info(f"⏳ 아직 스케줄 시간 전 (15:30 > {now.strftime('%H:%M:%S')})")

                # --- [5/5] 장 마감 리포트 (15:40, 평일) ---
                logger.info("--- [5/5] 장 마감 리포트 체크 시작 ---")
                afternoon_report_time = datetime.combine(today_date, time(15, 40))  # 오늘 15:40

                if now >= afternoon_report_time:
                    with get_db() as db:
                        afternoon_report = db.query(ReportResult).filter(
                            ReportResult.date == today_str,
                            ReportResult.report_type == 'afternoon'
                        ).first()

                        if afternoon_report is None:
                            logger.info(f"📰 오늘({today_str}) 장 마감 리포트 없음 → 생성 실행")
                            await generate_afternoon_report_job()
                        else:
                            logger.info(
                                f"✅ 장 마감 리포트 존재 (생성 시각: {afternoon_report.generated_at.strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                else:
                    logger.info(f"⏳ 아직 스케줄 시간 전 (15:40 > {now.strftime('%H:%M:%S')})")

                logger.info("=" * 60)
                logger.info("✅ 놓친 작업 체크 완료")
                logger.info("=" * 60)

            except Exception as e:
                logger.error(f"❌ 놓친 작업 체크 실패: {e}", exc_info=True)

        # 백그라운드에서 실행
        asyncio.create_task(run_missed_jobs())
    else:
        logger.warning("⚠️ 스케줄러가 비활성화되어 있습니다 (SCHEDULER_ENABLED=False)")

    yield  # 앱 실행 중

    # 앱 종료
    logger.info("🛑 SKKU-INSIGHT 애플리케이션 종료")
    if settings.SCHEDULER_ENABLED:
        stop_scheduler()


def create_app() -> FastAPI:
    """
    FastAPI 애플리케이션 생성 및 설정

    Returns:
        FastAPI: 설정된 FastAPI 인스턴스
    """
    app = FastAPI(
        title="SKKU-INSIGHT API",
        description="한국 주식 컨설팅 플랫폼 API",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan  # 생명주기 이벤트 추가
    )

    # 미들웨어 설정
    setup_middleware(app)

    # 라우터 등록
    setup_routers(app)

    logger.info("FastAPI application initialized")

    return app


def setup_middleware(app: FastAPI) -> None:
    """
    미들웨어 설정 (CORS, 로깅 등)

    Args:
        app: FastAPI 인스턴스
    """
    # CORS 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    logger.info("Middleware configured")


def setup_routers(app: FastAPI) -> None:
    """
    API 라우터 등록

    Args:
        app: FastAPI 인스턴스
    """
    # API v1 라우터 등록
    from app.api import api_router
    app.include_router(api_router)

    @app.get("/")
    async def root():
        """루트 엔드포인트"""
        return {
            "message": "SKKU-INSIGHT API",
            "version": "0.1.0",
            "docs": "/docs"
        }

    @app.get("/health")
    async def health_check():
        """헬스 체크 엔드포인트"""
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT
        }

    logger.info("Routers registered")


# 앱 인스턴스 생성
app = create_app()
