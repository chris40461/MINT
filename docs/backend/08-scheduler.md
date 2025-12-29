# 스케줄러 (Scheduler)

## 📌 문서 목적

APScheduler를 사용한 배치 작업 스케줄링을 설명합니다.

---

## ⏰ 스케줄 작업 목록

| 작업 | 실행 시간 | 설명 |
|------|---------|------|
| 오전 트리거 | 09:10 (평일) | 급등주 감지 |
| 오후 트리거 | 15:30 (평일) | 급등주 감지 |
| 장 시작 리포트 | 08:30 (평일) | 시장 전망 |
| 장 마감 리포트 | 15:40 (평일) | 시장 요약 |
| D+1 평가 | 16:00 (매일) | 예측 정확도 |
| 주간 평가 | 월 09:00 | 종합 평가 |

---

## 🔧 설정

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone='Asia/Seoul')

# 오전 트리거
scheduler.add_job(
    func=run_morning_triggers,
    trigger=CronTrigger(day_of_week='mon-fri', hour=9, minute=10),
    id='morning_triggers'
)

# 장 시작 리포트
scheduler.add_job(
    func=generate_morning_report,
    trigger=CronTrigger(day_of_week='mon-fri', hour=8, minute=30),
    id='morning_report'
)

scheduler.start()
```

---

## ⚠️ 에러 처리

```python
async def run_morning_triggers():
    """에러 처리가 포함된 트리거 실행"""
    try:
        results = await trigger_service.run_morning_triggers(datetime.now())
        logger.info(f"Morning triggers completed: {len(results)} stocks")
    except Exception as e:
        logger.error(f"Morning triggers failed: {e}", exc_info=True)
        # 알림 발송
        await send_error_notification("오전 트리거 실패", str(e))
```

---

**마지막 업데이트**: 2025-11-06
