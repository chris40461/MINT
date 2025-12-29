"""
Polling Manager

필터 통과 종목을 30개씩 분할하여
0.5초 간격으로 순차 폴링합니다.

Polling Strategy:
1. financial_data에서 필터 통과 종목 로드
2. 30개씩 배치로 분할
3. 각 배치를 KIS Multi-Quote API로 조회 (0.5초 간격)
4. realtime_prices 테이블에 업데이트
5. 전체 사이클 완료 (약 10초) → 즉시 다시 시작

Note:
- Multi-Quote API는 모든 시간대(정규/시간외/동시호가)에서 작동
- 시간대에 따라 API가 자동으로 적절한 값 반환
"""

import asyncio
import logging
from typing import List
from datetime import datetime, timedelta
import time

from app.config import settings
from app.kis_rest_client import KISRestClient
from app.database import DatabaseWriter, split_into_batches

logger = logging.getLogger(__name__)


class PollingManager:
    """폴링 관리자"""

    def __init__(self):
        self.batch_size = settings.BATCH_SIZE  # 30
        self.polling_interval = settings.POLLING_INTERVAL  # 0.5초
        self.cycle_complete_delay = settings.CYCLE_COMPLETE_DELAY  # 0.5초

        self.is_running = False

    async def poll_forever(
        self,
        kis_client: KISRestClient,
        db_writer: DatabaseWriter
    ):
        """
        무한 폴링 루프 (Multi-Quote API 사용)

        Multi-Quote API는 모든 시간대에서 작동하므로
        장_마감 시간을 제외하고 항상 배치 폴링 수행.

        Args:
            kis_client: KIS REST API 클라이언트
            db_writer: Database writer

        Raises:
            Exception: 치명적인 오류 발생 시
        """
        self.is_running = True
        logger.info("🚀 폴링 시작")

        # 필터 통과 종목 로드
        tickers = db_writer.get_filtered_tickers()

        if not tickers:
            logger.error("❌ 필터 통과 종목이 없습니다")
            return

        logger.info(f"📋 {len(tickers)}개 종목 추적")

        while self.is_running:
            # 현재 거래 시간대 확인
            session = get_trading_session()

            if session == '장_마감':
                # 장 마감 (18:00 이후) - 다음 장 시작(07:30)까지 대기
                next_market_open = get_next_market_open_time()
                sleep_seconds = (next_market_open - datetime.now()).total_seconds()

                logger.info(f"⏸️ 장 마감 - 다음 장 시작까지 대기")
                logger.info(f"   현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"   다음 시작: {next_market_open.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"   대기 시간: {sleep_seconds / 3600:.1f}시간")

                await asyncio.sleep(sleep_seconds)

                # 07:30 깨어나면 tickers 새로고침 (financial_data 00:00 업데이트 반영)
                tickers = db_writer.get_filtered_tickers()
                logger.info(f"📋 종목 새로고침 완료: {len(tickers)}개")
            else:
                # 모든 시간대: Multi-Quote API 사용 (정규/시간외/동시호가 모두)
                await self._poll_multi(kis_client, db_writer, tickers, session)

    async def _poll_multi(
        self,
        kis_client: KISRestClient,
        db_writer: DatabaseWriter,
        tickers: List[str],
        session: str = '정규시간'
    ):
        """
        Multi-Quote API 폴링 (모든 시간대)

        Multi-Quote API는 시간대에 따라 자동으로 적절한 값 반환:
        - 정규시간: 실시간 체결가
        - 동시호가: 예상 체결가
        - 시간외: 시간외 거래가
        """
        # 배치 분할
        batches = split_into_batches(tickers, self.batch_size)

        cycle_start = time.time()

        logger.info(f"🔄 [{session}] 폴링 시작 ({len(batches)}개 배치)")

        total_success = 0
        total_failed = 0

        # 각 배치 순차 처리
        for batch_index, batch in enumerate(batches, start=1):
            try:
                # KIS 멀티 API 호출
                prices = await kis_client.get_multi_quote(batch)

                if not prices:
                    logger.warning(f"  ⚠️ 배치 {batch_index}/{len(batches)}: 응답 없음")
                    total_failed += len(batch)
                else:
                    # DB 업데이트 (session 전달하여 동시호가 처리)
                    success_count = db_writer.batch_update_realtime_prices(prices, session)
                    failed_count = len(batch) - success_count

                    total_success += success_count
                    total_failed += failed_count

            except Exception as e:
                logger.error(f"  ❌ 배치 {batch_index}/{len(batches)} 실패: {e}")
                total_failed += len(batch)

            # API 제한 준수 (0.5초 대기)
            if batch_index < len(batches):  # 마지막 배치가 아니면
                await asyncio.sleep(self.polling_interval)

        cycle_time = time.time() - cycle_start

        logger.info(
            f"✅ [{session}] 폴링 완료 "
            f"({cycle_time:.1f}초 | 성공 {total_success}개 | 실패 {total_failed}개)"
        )

        # 사이클 완료 후 짧은 대기
        await asyncio.sleep(self.cycle_complete_delay)

    def stop(self):
        """폴링 중지"""
        logger.info("🛑 폴링 중지 요청")
        self.is_running = False


def get_trading_session() -> str:
    """
    현재 거래 시간대 판별

    Returns:
        '장전_준비' (07:30~08:30) - 종목 새로고침 및 초기 데이터 폴링
        '장전_시간외' (08:30~08:40)
        '장_시작_동시호가' (08:40~09:00)
        '정규시간' (09:00~15:20)
        '장_마감_동시호가' (15:20~15:30)
        '장후_시간외' (15:30~16:00)
        '시간외_단일가' (16:00~18:00)
        '장_마감' (그 외 시간)
    """
    now = datetime.now()

    # 주말 체크
    if now.weekday() >= 5:  # 토(5), 일(6)
        return '장_마감'

    hour = now.hour
    minute = now.minute
    current_time = hour * 60 + minute

    # 시간대 구분 (분 단위)
    if 7 * 60 + 30 <= current_time < 8 * 60 + 30:
        return '장전_준비'
    elif 8 * 60 + 30 <= current_time < 8 * 60 + 40:
        return '장전_시간외'
    elif 8 * 60 + 40 <= current_time < 9 * 60:
        return '장_시작_동시호가'
    elif 9 * 60 <= current_time < 15 * 60 + 20:
        return '정규시간'
    elif 15 * 60 + 20 <= current_time < 15 * 60 + 30:
        return '장_마감_동시호가'
    elif 15 * 60 + 30 <= current_time < 16 * 60:
        return '장후_시간외'
    elif 16 * 60 <= current_time < 18 * 60:
        return '시간외_단일가'
    else:
        return '장_마감'


def is_market_open() -> bool:
    """
    장 운영 시간 확인 (09:00 ~ 15:30, 평일)

    Returns:
        장 중 여부
    """
    now = datetime.now()

    # 주말 체크
    if now.weekday() >= 5:  # 토(5), 일(6)
        return False

    # 시간 체크
    market_open_hour = settings.MARKET_OPEN_HOUR
    market_open_minute = settings.MARKET_OPEN_MINUTE
    market_close_hour = settings.MARKET_CLOSE_HOUR
    market_close_minute = settings.MARKET_CLOSE_MINUTE

    current_time = now.hour * 60 + now.minute
    open_time = market_open_hour * 60 + market_open_minute
    close_time = market_close_hour * 60 + market_close_minute

    return open_time <= current_time < close_time


def get_next_market_open_time() -> datetime:
    """
    다음 장 시작 시간 계산 (07:30 기준)

    Returns:
        다음 장 시작 시간 (datetime)
    """
    now = datetime.now()
    target_time = now.replace(hour=7, minute=30, second=0, microsecond=0)

    # 오늘 07:30이 아직 안 지났으면 오늘
    if now < target_time:
        return target_time

    # 07:30 지났으면 다음 평일 07:30
    next_day = now + timedelta(days=1)
    next_day = next_day.replace(hour=7, minute=30, second=0, microsecond=0)

    # 주말이면 다음 월요일로
    while next_day.weekday() >= 5:  # 토(5), 일(6)
        next_day += timedelta(days=1)

    return next_day
