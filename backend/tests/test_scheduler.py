"""
스케줄러 테스트 스크립트

스케줄러가 제대로 등록되고 실행되는지 확인합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scheduler import start_scheduler, stop_scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """스케줄러 테스트"""
    print("=" * 80)
    print("스케줄러 테스트")
    print("=" * 80)
    print()

    # 스케줄러 시작
    logger.info("스케줄러 시작...")
    start_scheduler()

    # 등록된 작업 출력
    from app.scheduler.jobs import scheduler
    jobs = scheduler.get_jobs()

    print()
    print(f"📋 등록된 작업: {len(jobs)}개")
    print("-" * 80)
    for job in jobs:
        next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "없음"
        print(f"  [{job.id}]")
        print(f"    이름: {job.name}")
        print(f"    다음 실행: {next_run}")
        print()

    print("=" * 80)
    print("✅ 스케줄러가 정상적으로 실행 중입니다!")
    print("   (Ctrl+C로 종료)")
    print("=" * 80)

    try:
        # 스케줄러 계속 실행 (무한 대기)
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n사용자 중단")
    finally:
        stop_scheduler()
        logger.info("스케줄러 종료됨")


if __name__ == "__main__":
    asyncio.run(main())
