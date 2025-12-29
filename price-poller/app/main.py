"""
Price Poller Service - Main Entry Point

KIS REST API를 사용하여 625개 종목의 준실시간 가격을 폴링하고
realtime_prices 테이블에 업데이트하는 백그라운드 서비스입니다.

Architecture:
- KIS REST API (멀티종목 시세조회)
- 625개 종목 → 21개 배치 (30개씩)
- 0.5초 간격 폴링
- 10.5초마다 전체 종목 갱신 완료

Usage:
    python3 -m app.main
"""

import asyncio
import signal
import logging
import sys
from datetime import datetime

from app.config import settings
from app.kis_rest_client import KISRestClient
from app.database import DatabaseWriter
from app.polling_manager import PollingManager, is_market_open

# Logging setup
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# httpx 로그 레벨을 WARNING으로 설정 (HTTP 요청 로그 숨기기)
logging.getLogger('httpx').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class PricePollerService:
    """Price Poller 서비스"""

    def __init__(self):
        self.kis_client = KISRestClient()
        self.db_writer = DatabaseWriter()
        self.polling_manager = PollingManager()

        self.running = False
        self.polling_task: asyncio.Task = None

    async def start(self):
        """서비스 시작"""
        logger.info("=" * 60)
        logger.info("🚀 Price Poller Service Starting...")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Log Level: {settings.LOG_LEVEL}")
        logger.info(f"KIS Mock Mode: {settings.KIS_IS_MOCK}")
        logger.info(f"Database: {settings.DATABASE_URL}")
        logger.info(f"Polling Interval: {settings.POLLING_INTERVAL}s")
        logger.info(f"Batch Size: {settings.BATCH_SIZE} stocks")
        logger.info("=" * 60)

        try:
            # 1. KIS API 연결 확인 (토큰 발급 - 1분당 1회 제한 있음)
            logger.info("🔌 Connecting to KIS API...")
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    if await self.kis_client.health_check():
                        logger.info(f"✅ Connected to KIS API (Mock: {settings.KIS_IS_MOCK})")
                        break
                    else:
                        raise Exception("Health check returned False")
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"⚠️ KIS API 연결 실패 (시도 {attempt}/{max_retries}): {e}")
                        logger.info(f"⏳ 60초 대기 후 재시도... (KIS 토큰 발급 제한: 1분당 1회)")
                        await asyncio.sleep(60)
                    else:
                        logger.error(f"❌ KIS API 연결 최종 실패 (시도 {attempt}/{max_retries}): {e}")
                        raise Exception("KIS API 연결 실패")

            # 2. Database 연결
            logger.info("💾 Connecting to database...")
            self.db_writer.connect()
            logger.info("✅ Database connected")

            # 3. 필터 통과 종목 확인
            tickers = self.db_writer.get_filtered_tickers()
            if not tickers:
                raise Exception("필터 통과 종목이 없습니다")
            logger.info(f"📊 {len(tickers)}개 종목 추적 예정")

            # 4. 폴링 시작
            self.running = True
            self.polling_task = asyncio.create_task(self._run_forever())

            logger.info("✅ Price Poller Service started successfully")
            logger.info("=" * 60)

            # 메인 루프 유지
            await self.polling_task

        except Exception as e:
            logger.error(f"❌ Service start failed: {e}", exc_info=True)
            await self.stop()
            sys.exit(1)

    async def _run_forever(self):
        """메인 이벤트 루프 (장 운영 시간 체크)"""
        logger.info("🔄 Main event loop started")

        while self.running:
            try:
                # 폴링 시작 (시간대별 API는 poll_forever에서 자동 선택)
                try:
                    await self.polling_manager.poll_forever(
                        kis_client=self.kis_client,
                        db_writer=self.db_writer
                    )
                except Exception as e:
                    error_msg = str(e)

                    # 폴링 불가 구간 (동시호가, 장 마감 후) - 5분 대기
                    if "시세조회 불가" in error_msg or "폴링 불가" in error_msg or "동시호가" in error_msg:
                        logger.info(f"⏸️ {error_msg}")
                        logger.info("⏳ 5분 후 재확인...")
                        await asyncio.sleep(300)
                    else:
                        # 기타 에러 - 30초 대기
                        logger.error(f"❌ Polling error: {e}", exc_info=True)
                        logger.info("🔄 30초 후 재시도...")
                        await asyncio.sleep(30)

            except asyncio.CancelledError:
                logger.info("⚠️ Main loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Main loop error: {e}", exc_info=True)
                await asyncio.sleep(60)

        logger.info("Main event loop stopped")

    async def stop(self):
        """서비스 종료 (Graceful Shutdown)"""
        logger.info("=" * 60)
        logger.info("🛑 Stopping Price Poller Service...")

        self.running = False

        # 1. 폴링 중지
        if self.polling_manager:
            self.polling_manager.stop()
            logger.info("✅ Polling manager stopped")

        # 2. 폴링 태스크 취소
        if self.polling_task and not self.polling_task.done():
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
            logger.info("✅ Polling task cancelled")

        # 3. KIS 클라이언트 종료
        if self.kis_client:
            await self.kis_client.close()
            logger.info("✅ KIS client closed")

        # 4. Database 연결 종료
        if self.db_writer:
            self.db_writer.close()
            logger.info("✅ Database connection closed")

        logger.info("✅ Price Poller Service stopped")
        logger.info("=" * 60)


# Global service instance
service = PricePollerService()


def signal_handler(sig, frame):
    """시그널 핸들러 (SIGINT, SIGTERM)"""
    logger.info(f"⚠️ Signal {sig} received")
    asyncio.create_task(service.stop())


async def main():
    """메인 함수"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 서비스 시작
    await service.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Keyboard interrupt received")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)
