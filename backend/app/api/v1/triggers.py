# 참고: docs/architecture/03-api-design.md
# 참고: docs/backend/02-trigger-detection.md

"""
급등주 트리거 API 엔드포인트

오전/오후 트리거 결과 조회
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, timedelta
from typing import Optional, List
import logging
import time

from app.models import TriggerResponse, Trigger, TriggerType, SessionType
from app.services import TriggerService
from app.api.dependencies import get_trigger_service
from app.db.database import get_db
from app.db.models import TriggerResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.get("/", response_model=TriggerResponse)
async def get_triggers(
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본값: 오늘)"),
    session: Optional[SessionType] = Query(None, description="세션 (morning/afternoon)")
):
    """
    급등주 트리거 조회

    Args:
        date: 조회 날짜 (기본값: 오늘)
        session: 세션 필터 (morning/afternoon, 선택)

    Returns:
        TriggerResponse: 트리거 결과
    """
    try:
        # 날짜 파싱
        if date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            query_date = datetime.now()

        date_str = query_date.strftime("%Y-%m-%d")

        # DB에서 트리거 조회 및 Pydantic 모델로 변환
        triggers = []
        with get_db() as db:
            query = db.query(TriggerResult).filter(TriggerResult.date == date_str)

            # 세션 필터링
            if session:
                query = query.filter(TriggerResult.session == session)

            results = query.order_by(TriggerResult.composite_score.desc()).all()

            # 세션 안에서 Trigger 모델로 변환
            for result in results:
                triggers.append(Trigger(
                    ticker=result.ticker,
                    name=result.name,
                    trigger_type=result.trigger_type,
                    current_price=result.current_price,
                    change_rate=result.change_rate,
                    volume=result.volume,
                    trading_value=result.trading_value,
                    composite_score=result.composite_score,
                    session=result.session,
                    detected_at=result.detected_at
                ))

        # 메타데이터 생성
        trigger_types = {}
        for trigger in triggers:
            trigger_types[trigger.trigger_type] = trigger_types.get(trigger.trigger_type, 0) + 1

        metadata = {
            "date": date_str,
            "session": session if session else "all",
            "total": len(triggers),
            "trigger_types": trigger_types
        }

        return {
            "success": True,
            "data": {
                "triggers": [t.model_dump() for t in triggers],
                "metadata": metadata
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except Exception as e:
        logger.error(f"트리거 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=TriggerResponse)
async def get_latest_triggers():
    """
    최신 트리거 조회

    현재 시간 기준으로 가장 최근 실행된 트리거 결과 반환
    - 09:10 이전: 전일 오후 트리거
    - 09:10-15:30: 당일 오전 트리거
    - 15:30 이후: 당일 오후 트리거

    Returns:
        TriggerResponse: 최신 트리거 결과
    """
    try:
        now = datetime.now()
        current_time = now.time()

        # 시간대별 세션 결정
        if current_time < datetime.strptime("09:10", "%H:%M").time():
            # 09:10 이전 - 전일 오후 트리거
            target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            target_session = "afternoon"
        elif current_time < datetime.strptime("15:30", "%H:%M").time():
            # 09:10-15:30 - 당일 오전 트리거
            target_date = now.strftime("%Y-%m-%d")
            target_session = "morning"
        else:
            # 15:30 이후 - 당일 오후 트리거
            target_date = now.strftime("%Y-%m-%d")
            target_session = "afternoon"

        # DB에서 트리거 조회 및 Pydantic 모델로 변환
        triggers = []
        with get_db() as db:
            results = db.query(TriggerResult).filter(
                TriggerResult.date == target_date,
                TriggerResult.session == target_session
            ).order_by(TriggerResult.composite_score.desc()).all()

            # 세션 안에서 Trigger 모델로 변환
            for result in results:
                triggers.append(Trigger(
                    ticker=result.ticker,
                    name=result.name,
                    trigger_type=result.trigger_type,
                    current_price=result.current_price,
                    change_rate=result.change_rate,
                    volume=result.volume,
                    trading_value=result.trading_value,
                    composite_score=result.composite_score,
                    session=result.session,
                    detected_at=result.detected_at
                ))

        # 메타데이터 생성
        trigger_types = {}
        for trigger in triggers:
            trigger_types[trigger.trigger_type] = trigger_types.get(trigger.trigger_type, 0) + 1

        metadata = {
            "date": target_date,
            "session": target_session,
            "total": len(triggers),
            "trigger_types": trigger_types
        }

        return {
            "success": True,
            "data": {
                "triggers": [t.model_dump() for t in triggers],
                "metadata": metadata
            }
        }

    except Exception as e:
        logger.error(f"최신 트리거 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types/{trigger_type}")
async def get_triggers_by_type(
    trigger_type: TriggerType,
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본값: 오늘)"),
    limit: int = Query(3, description="최대 결과 수", ge=1, le=10)
):
    """
    특정 트리거 타입별 조회

    Args:
        trigger_type: 트리거 타입 (volume_surge, gap_up, fund_inflow, 등)
        date: 조회 날짜
        limit: 최대 결과 수

    Returns:
        트리거 리스트
    """
    try:
        # 날짜 파싱
        if date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            query_date = datetime.now()

        date_str = query_date.strftime("%Y-%m-%d")

        # DB에서 특정 타입 트리거 조회 및 Pydantic 모델로 변환
        triggers = []
        with get_db() as db:
            results = db.query(TriggerResult).filter(
                TriggerResult.date == date_str,
                TriggerResult.trigger_type == trigger_type
            ).order_by(TriggerResult.composite_score.desc()).limit(limit).all()

            # 세션 안에서 Trigger 모델로 변환
            for result in results:
                triggers.append(Trigger(
                    ticker=result.ticker,
                    name=result.name,
                    trigger_type=result.trigger_type,
                    current_price=result.current_price,
                    change_rate=result.change_rate,
                    volume=result.volume,
                    trading_value=result.trading_value,
                    composite_score=result.composite_score,
                    session=result.session,
                    detected_at=result.detected_at
                ))

        return {
            "success": True,
            "data": {
                "trigger_type": trigger_type,
                "date": date_str,
                "total": len(triggers),
                "triggers": [t.model_dump() for t in triggers]
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except Exception as e:
        logger.error(f"트리거 타입별 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/history")
async def get_trigger_history(
    ticker: str,
    days: int = Query(30, description="조회 기간 (일)", ge=1, le=90)
):
    """
    종목별 트리거 히스토리

    특정 종목이 얼마나 자주 트리거에 걸렸는지 확인

    Args:
        ticker: 종목 코드
        days: 조회 기간 (일)

    Returns:
        트리거 히스토리
    """
    try:
        # 날짜 범위 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        # DB에서 종목별 트리거 조회 및 변환
        with get_db() as db:
            results = db.query(TriggerResult).filter(
                TriggerResult.ticker == ticker,
                TriggerResult.date >= start_str,
                TriggerResult.date <= end_str
            ).order_by(TriggerResult.date.desc()).all()

            if not results:
                return {
                    "success": True,
                    "data": {
                        "ticker": ticker,
                        "name": ticker,
                        "period": {"start": start_str, "end": end_str},
                        "total_triggers": 0,
                        "trigger_breakdown": {},
                        "triggers": []
                    }
                }

            # 세션 안에서 통계 집계
            trigger_breakdown = {}
            triggers_list = []
            stock_name = results[0].name

            for result in results:
                # 트리거 타입별 카운트
                trigger_breakdown[result.trigger_type] = trigger_breakdown.get(result.trigger_type, 0) + 1

                # 트리거 목록
                triggers_list.append({
                    "date": result.date,
                    "session": result.session,
                    "trigger_type": result.trigger_type,
                    "current_price": result.current_price,
                    "change_rate": result.change_rate,
                    "composite_score": result.composite_score
                })

        return {
            "success": True,
            "data": {
                "ticker": ticker,
                "name": stock_name,
                "period": {"start": start_str, "end": end_str},
                "total_triggers": len(results),
                "trigger_breakdown": trigger_breakdown,
                "triggers": triggers_list
            }
        }

    except Exception as e:
        logger.error(f"트리거 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/{session}")
async def run_triggers_manually(
    session: SessionType,
    trigger_service: TriggerService = Depends(get_trigger_service)
):
    """
    트리거 수동 실행 (관리자용)

    스케줄러가 아닌 수동으로 트리거 실행

    Args:
        session: 실행할 세션 (morning/afternoon)

    Returns:
        실행 결과
    """
    try:
        start_time = time.time()
        today = datetime.now()

        logger.info(f"트리거 수동 실행 시작: {session} ({today.strftime('%Y-%m-%d')})")

        # 세션별 트리거 실행
        if session == "morning":
            results = await trigger_service.run_morning_triggers(today)
        else:
            results = await trigger_service.run_afternoon_triggers(today)

        # 총 감지 종목 수
        total_triggers = sum(len(triggers) for triggers in results.values())

        # 실행 시간
        execution_time = round(time.time() - start_time, 2)

        # 트리거 타입별 개수
        trigger_counts = {
            trigger_type: len(triggers)
            for trigger_type, triggers in results.items()
        }

        logger.info(f"✅ 트리거 수동 실행 완료: {total_triggers}개 종목, {execution_time}초")

        return {
            "success": True,
            "data": {
                "session": session,
                "date": today.strftime("%Y-%m-%d"),
                "triggers_detected": total_triggers,
                "trigger_breakdown": trigger_counts,
                "execution_time": execution_time,
                "message": f"{'오전' if session == 'morning' else '오후'} 트리거 실행 완료"
            }
        }

    except Exception as e:
        logger.error(f"트리거 수동 실행 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_trigger_stats(
    start_date: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)")
):
    """
    트리거 통계 조회

    기간별 트리거 감지 통계

    Args:
        start_date: 시작일 (기본값: 30일 전)
        end_date: 종료일 (기본값: 오늘)

    Returns:
        통계 정보
    """
    try:
        # 날짜 범위 파싱
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.now()

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = end_dt - timedelta(days=30)

        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")

        # DB에서 기간 내 모든 트리거 조회 및 통계 집계
        with get_db() as db:
            results = db.query(TriggerResult).filter(
                TriggerResult.date >= start_str,
                TriggerResult.date <= end_str
            ).all()

            if not results:
                return {
                    "success": True,
                    "data": {
                        "period": {"start": start_str, "end": end_str},
                        "total_triggers": 0,
                        "daily_average": 0,
                        "by_type": {},
                        "by_session": {},
                        "top_frequent_stocks": []
                    }
                }

            # 세션 안에서 통계 집계
            total_triggers = len(results)
            days_count = (end_dt - start_dt).days + 1
            daily_average = round(total_triggers / days_count, 1)

            # 타입별 집계
            by_type = {}
            for result in results:
                by_type[result.trigger_type] = by_type.get(result.trigger_type, 0) + 1

            # 세션별 집계
            by_session = {}
            for result in results:
                by_session[result.session] = by_session.get(result.session, 0) + 1

            # 종목별 빈도 집계
            stock_counts = {}
            for result in results:
                key = (result.ticker, result.name)
                stock_counts[key] = stock_counts.get(key, 0) + 1

            # Top 10 빈출 종목
            top_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_frequent_stocks = [
                {"ticker": ticker, "name": name, "count": count}
                for (ticker, name), count in top_stocks
            ]

        return {
            "success": True,
            "data": {
                "period": {"start": start_str, "end": end_str},
                "total_triggers": total_triggers,
                "daily_average": daily_average,
                "by_type": by_type,
                "by_session": by_session,
                "top_frequent_stocks": top_frequent_stocks
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except Exception as e:
        logger.error(f"트리거 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
