# 참고: docs/architecture/03-api-design.md
# 참고: docs/backend/07-market-reports.md

"""
시장 리포트 API 엔드포인트

장 시작 리포트 (08:30), 장 마감 리포트 (15:40)
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, timedelta
from typing import Optional
import logging
import json

from app.models import ReportResponse, MorningReport, AfternoonReport
from app.services import LLMReport, DataService, TriggerService
from app.api.dependencies import get_data_service
from app.db.database import get_db
from app.db.models import ReportResult, TriggerResult
from app.models.report import (
    ExtendedMarketSummary,
    MarketBreadth,
    SectorAnalysis,
    SectorInfo,
    ThemeAnalysis,
    SurgeStock
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/morning", response_model=ReportResponse)
async def get_morning_report(
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본값: 오늘)")
):
    """
    장 시작 리포트 조회 (08:30 생성)

    내용:
    - 시장 전망
    - KOSPI 예상 범위
    - 주목 종목 Top 5 (Metric 기반)
    - 섹터 분석 (강세/약세)
    - 투자 전략

    Args:
        date: 조회 날짜 (기본값: 오늘)

    Returns:
        ReportResponse: 장 시작 리포트

    Example:
        GET /api/v1/reports/morning?date=2025-11-06

        Response:
        {
            "success": true,
            "data": {
                "report_type": "morning",
                "date": "2025-11-06",
                "generated_at": "2025-11-06T08:30:00",
                "market_forecast": "오늘의 시장은 미국 증시 상승과 환율 안정에 힘입어 소폭 상승 출발 예상",
                "kospi_range": {
                    "low": 2630.0,
                    "high": 2680.0
                },
                "top_stocks": [
                    {
                        "rank": 1,
                        "ticker": "005930",
                        "name": "삼성전자",
                        "current_price": 72000,
                        "score": 8.5,
                        "reason": "HBM3 수주 증가 모멘텀"
                    },
                    ...
                ],
                "sector_analysis": {
                    "bullish": ["반도체", "2차전지"],
                    "bearish": ["은행", "건설"]
                },
                "investment_strategy": "반도체 중심의 포트폴리오 유지 권장",
                "metadata": {
                    "model": "gemini-2.5-flash",
                    "tokens_used": 2500
                }
            }
        }
    """
    try:
        # 날짜 파싱
        if date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            query_date = datetime.now()

        date_str = query_date.strftime("%Y-%m-%d")

        # DB에서 리포트 조회
        with get_db() as db:
            result = db.query(ReportResult).filter(
                ReportResult.report_type == "morning",
                ReportResult.date == date_str
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail=f"{date_str} 장 시작 리포트가 없습니다")

            # JSON 파싱 및 Pydantic 모델로 변환
            content = json.loads(result.content)
            report = MorningReport(**content)

        return {"success": True, "data": report}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장 시작 리포트 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/afternoon", response_model=ReportResponse)
async def get_afternoon_report(
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본값: 오늘)")
):
    """
    장 마감 리포트 조회 (15:40 생성)

    내용:
    - 시장 요약 (KOSPI, 거래대금, 외국인/기관 순매수)
    - 급등주 상세 분석 (오후 트리거 기반)
    - 내일의 투자 전략

    Args:
        date: 조회 날짜 (기본값: 오늘)

    Returns:
        ReportResponse: 장 마감 리포트

    Example:
        GET /api/v1/reports/afternoon?date=2025-11-06

        Response:
        {
            "success": true,
            "data": {
                "report_type": "afternoon",
                "date": "2025-11-06",
                "generated_at": "2025-11-06T15:40:00",
                "market_summary": {
                    "kospi_close": 2650.34,
                    "kospi_change": 1.2,
                    "trading_value": 12500000000000,
                    "foreign_net": 250000000000,
                    "institution_net": -150000000000
                },
                "surge_stocks": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "change_rate": 5.2,
                        "trigger_type": "intraday_rise",
                        "reason": "HBM3 수주 증가 보도",
                        "outlook": "단기 모멘텀 지속 예상"
                    },
                    ...
                ],
                "tomorrow_strategy": "반도체 섹터의 모멘텀 지속 관찰 필요",
                "metadata": {
                    "model": "gemini-2.5-flash",
                    "tokens_used": 3000
                }
            }
        }
    """
    try:
        # 날짜 파싱
        if date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            query_date = datetime.now()

        date_str = query_date.strftime("%Y-%m-%d")

        # DB에서 리포트 조회
        with get_db() as db:
            result = db.query(ReportResult).filter(
                ReportResult.report_type == "afternoon",
                ReportResult.date == date_str
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail=f"{date_str} 장 마감 리포트가 없습니다")

            # JSON 파싱 및 Pydantic 모델로 변환
            content = json.loads(result.content)
            report = AfternoonReport(**content)

        return {"success": True, "data": report}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"장 마감 리포트 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_report():
    """
    최신 리포트 조회

    현재 시간 기준으로 가장 최근 리포트 반환
    - 08:30 이전: 전일 오후 리포트
    - 08:30-15:40: 당일 오전 리포트
    - 15:40 이후: 당일 오후 리포트

    Returns:
        최신 리포트

    Example:
        GET /api/v1/reports/latest

        Response:
        {
            "success": true,
            "data": {
                "report_type": "morning",
                ...
            }
        }
    """
    try:
        now = datetime.now()
        current_time = now.time()

        # 시간대별 리포트 타입 결정
        if current_time < datetime.strptime("08:30", "%H:%M").time():
            # 08:30 이전 - 전일 오후 리포트
            target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            target_type = "afternoon"
        elif current_time < datetime.strptime("15:40", "%H:%M").time():
            # 08:30-15:40 - 당일 오전 리포트
            target_date = now.strftime("%Y-%m-%d")
            target_type = "morning"
        else:
            # 15:40 이후 - 당일 오후 리포트
            target_date = now.strftime("%Y-%m-%d")
            target_type = "afternoon"

        # DB에서 리포트 조회
        with get_db() as db:
            result = db.query(ReportResult).filter(
                ReportResult.report_type == target_type,
                ReportResult.date == target_date
            ).first()

            if not result:
                raise HTTPException(status_code=404, detail=f"{target_date} {target_type} 리포트가 없습니다")

            # JSON 파싱 및 Pydantic 모델로 변환
            content = json.loads(result.content)
            if target_type == "morning":
                report = MorningReport(**content)
            else:
                report = AfternoonReport(**content)

        return {"success": True, "data": report}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"최신 리포트 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/morning/generate")
async def generate_morning_report(
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본값: 오늘)")
):
    """
    장 시작 리포트 수동 생성 (관리자용)

    Args:
        date: 생성 날짜

    Returns:
        생성된 리포트

    Example:
        POST /api/v1/reports/morning/generate

        Response:
        {
            "success": true,
            "data": {...},
            "message": "장 시작 리포트가 생성되었습니다"
        }
    """
    try:
        # 날짜 파싱
        if date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            query_date = datetime.now()

        date_str = query_date.strftime("%Y-%m-%d")

        # 기존 리포트 확인 (중복 생성 방지)
        with get_db() as db:
            existing = db.query(ReportResult).filter(
                ReportResult.report_type == "morning",
                ReportResult.date == date_str
            ).first()

            if existing:
                logger.info(f"이미 존재하는 장 시작 리포트 (skip): {date_str}")
                content = json.loads(existing.content)
                return {
                    "success": True,
                    "data": MorningReport(**content),
                    "message": "이미 생성된 리포트입니다"
                }

        logger.info(f"장 시작 리포트 생성 시작: {date_str}")

        # LLMReport 서비스 초기화 및 리포트 생성
        llm_service = LLMReport()
        report_data = await llm_service.generate_morning_report(query_date)

        # Pydantic 모델로 변환 (검증 포함)
        try:
            morning_report = MorningReport(**report_data)
        except Exception as model_error:
            logger.error(f"MorningReport 모델 검증 실패: {model_error}")
            logger.error(f"report_data keys: {report_data.keys()}")
            logger.error(f"report_data sample: {str(report_data)[:500]}...")
            raise HTTPException(status_code=500, detail=f"리포트 모델 검증 실패: {str(model_error)}")

        # 토큰 사용량 추출
        tokens_used = report_data.get('metadata', {}).get('tokens_used', 0)

        # DB에 저장
        with get_db() as db:
            # 기존 리포트 삭제
            db.query(ReportResult).filter(
                ReportResult.report_type == "morning",
                ReportResult.date == date_str
            ).delete()

            # 새 리포트 저장
            report_result = ReportResult(
                report_type="morning",
                date=date_str,
                content=morning_report.model_dump_json(),
                generated_at=datetime.now(),
                model_name="gemini-2.5-flash",
                tokens_used=tokens_used
            )
            db.add(report_result)

        logger.info(f"✅ 장 시작 리포트 생성 완료: {date_str} (토큰: {tokens_used})")

        return {
            "success": True,
            "data": morning_report,
            "message": "장 시작 리포트가 생성되었습니다"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except Exception as e:
        logger.error(f"장 시작 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/afternoon/generate")
async def generate_afternoon_report(
    date: Optional[str] = Query(None, description="날짜 (YYYY-MM-DD, 기본값: 오늘)")
):
    """
    장 마감 리포트 수동 생성 (관리자용)

    Args:
        date: 생성 날짜

    Returns:
        생성된 리포트

    Example:
        POST /api/v1/reports/afternoon/generate

        Response:
        {
            "success": true,
            "data": {...},
            "message": "장 마감 리포트가 생성되었습니다"
        }
    """
    try:
        # 날짜 파싱
        if date:
            query_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            query_date = datetime.now()

        date_str = query_date.strftime("%Y-%m-%d")

        # 기존 리포트 확인 (중복 생성 방지)
        with get_db() as db:
            existing = db.query(ReportResult).filter(
                ReportResult.report_type == "afternoon",
                ReportResult.date == date_str
            ).first()

            if existing:
                logger.info(f"이미 존재하는 장 마감 리포트 (skip): {date_str}")
                content = json.loads(existing.content)
                return {
                    "success": True,
                    "data": AfternoonReport(**content),
                    "message": "이미 생성된 리포트입니다"
                }

        # 1. 시장 데이터 수집 (KOSPI + KOSDAQ + 수급 + 시장폭)
        logger.info(f"[1/3] 시장 데이터 수집: {date_str}")
        data_service = DataService()
        market_data = await data_service.get_market_index(query_date)

        # 2. 오후 트리거 결과 조회
        logger.info(f"[2/3] 오후 트리거 결과 조회: {date_str}")
        surge_stocks = []
        with get_db() as db:
            trigger_results = db.query(TriggerResult).filter(
                TriggerResult.date == date_str,
                TriggerResult.session == 'afternoon'
            ).order_by(TriggerResult.composite_score.desc()).limit(10).all()

            for r in trigger_results:
                surge_stocks.append({
                    'ticker': r.ticker,
                    'name': r.name,
                    'change_rate': r.change_rate or 0.0,
                    'volume': r.volume or 0,
                    'trigger_type': r.trigger_type,
                    'composite_score': r.composite_score or 0.0
                })

        if not surge_stocks:
            logger.warning(f"오후 트리거 결과 없음, 오전 트리거로 대체: {date_str}")
            # 오전 트리거로 fallback
            with get_db() as db:
                trigger_results = db.query(TriggerResult).filter(
                    TriggerResult.date == date_str,
                    TriggerResult.session == 'morning'
                ).order_by(TriggerResult.composite_score.desc()).limit(10).all()

                for r in trigger_results:
                    surge_stocks.append({
                        'ticker': r.ticker,
                        'name': r.name,
                        'change_rate': r.change_rate or 0.0,
                        'volume': r.volume or 0,
                        'trigger_type': r.trigger_type,
                        'composite_score': r.composite_score or 0.0
                    })

        # 3. LLM Report 생성
        logger.info(f"[3/3] LLM Afternoon Report 생성: {date_str}")
        llm_report = LLMReport()
        llm_result = await llm_report.generate_afternoon_report(
            query_date,
            market_data,
            surge_stocks
        )

        # 4. LLM 결과를 AfternoonReport 모델로 변환
        # 시장 요약 데이터 변환 (억원 단위)
        market_summary = ExtendedMarketSummary(
            kospi_close=market_data.get('kospi_close', 0.0),
            kospi_change=market_data.get('kospi_change', 0.0),
            kospi_point_change=market_data.get('kospi_point_change', 0.0),
            kosdaq_close=market_data.get('kosdaq_close', 0.0),
            kosdaq_change=market_data.get('kosdaq_change', 0.0),
            kosdaq_point_change=market_data.get('kosdaq_point_change', 0.0),
            trading_value=market_data.get('trading_value', 0) // 100000000,
            foreign_net_kospi=market_data.get('foreign_net_kospi', 0) // 100000000,
            institution_net_kospi=market_data.get('institution_net_kospi', 0) // 100000000,
            individual_net_kospi=market_data.get('individual_net_kospi', 0) // 100000000,
            foreign_net_kosdaq=market_data.get('foreign_net_kosdaq', 0) // 100000000,
            institution_net_kosdaq=market_data.get('institution_net_kosdaq', 0) // 100000000,
            individual_net_kosdaq=market_data.get('individual_net_kosdaq', 0) // 100000000,
            advance_count=market_data.get('advance_count', 0),
            decline_count=market_data.get('decline_count', 0),
            unchanged_count=market_data.get('unchanged_count', 0)
        )

        # 시장 폭 분석
        market_breadth_data = llm_result.get('market_breadth', {})
        market_breadth = MarketBreadth(
            sentiment=market_breadth_data.get('sentiment', '혼조세'),
            interpretation=market_breadth_data.get('interpretation', '')
        ) if market_breadth_data else None

        # 업종 분석
        sector_data = llm_result.get('sector_analysis', {})
        sector_analysis = None
        if sector_data:
            bullish_list = [
                SectorInfo(
                    sector=s.get('sector', ''),
                    change=s.get('change', ''),
                    reason=s.get('reason', '')
                ) for s in sector_data.get('bullish', [])
            ]
            bearish_list = [
                SectorInfo(
                    sector=s.get('sector', ''),
                    change=s.get('change', ''),
                    reason=s.get('reason', '')
                ) for s in sector_data.get('bearish', [])
            ]
            sector_analysis = SectorAnalysis(bullish=bullish_list, bearish=bearish_list)

        # 테마 분석
        themes_data = llm_result.get('today_themes', [])
        today_themes = [
            ThemeAnalysis(
                theme=t.get('theme', ''),
                drivers=t.get('drivers', ''),
                leading_stocks=t.get('leading_stocks', [])
            ) for t in themes_data
        ]

        # 급등주 분석
        surge_data = llm_result.get('surge_analysis', [])
        surge_stocks_model = [
            SurgeStock(
                ticker=s.get('ticker', ''),
                name=s.get('name', ''),
                category=s.get('category', ''),
                reason=s.get('reason', ''),
                outlook=s.get('outlook', '')
            ) for s in surge_data
        ]

        # AfternoonReport 생성
        afternoon_report = AfternoonReport(
            date=date_str,
            market_summary=market_summary,
            market_summary_text=llm_result.get('market_summary_text', ''),
            market_breadth=market_breadth,
            sector_analysis=sector_analysis,
            supply_demand_analysis=llm_result.get('supply_demand_analysis', ''),
            today_themes=today_themes,
            surge_stocks=surge_stocks_model,
            tomorrow_strategy=llm_result.get('tomorrow_strategy', ''),
            check_points=llm_result.get('check_points', []),
            metadata=llm_result.get('metadata', {})
        )

        # 5. DB에 저장
        with get_db() as db:
            # 기존 리포트 삭제
            db.query(ReportResult).filter(
                ReportResult.report_type == "afternoon",
                ReportResult.date == date_str
            ).delete()

            # 새 리포트 저장
            report_result = ReportResult(
                report_type="afternoon",
                date=date_str,
                content=afternoon_report.model_dump_json(),
                generated_at=datetime.now(),
                model_name="gemini-2.5-flash",
                tokens_used=llm_result.get('metadata', {}).get('tokens_used', 0)
            )
            db.add(report_result)

        logger.info(f"✅ 장 마감 리포트 생성 완료: {date_str}")

        return {
            "success": True,
            "data": afternoon_report,
            "message": "장 마감 리포트가 생성되었습니다"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"잘못된 날짜 형식: {str(e)}")
    except Exception as e:
        logger.error(f"장 마감 리포트 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_report_history(
    report_type: Optional[str] = Query(None, description="리포트 타입 (morning/afternoon)"),
    limit: int = Query(7, description="조회 개수", ge=1, le=30)
):
    """
    리포트 히스토리 조회

    Args:
        report_type: 리포트 타입 필터 (선택)
        limit: 조회 개수 (기본값: 7일치)

    Returns:
        리포트 목록

    Example:
        GET /api/v1/reports/history?report_type=morning&limit=7

        Response:
        {
            "success": true,
            "data": {
                "total": 7,
                "reports": [
                    {
                        "date": "2025-11-06",
                        "report_type": "morning",
                        "generated_at": "2025-11-06T08:30:00",
                        "summary": "...",
                        "id": "report_morning_20251106"
                    },
                    ...
                ]
            }
        }
    """
    try:
        # DB에서 리포트 목록 조회
        with get_db() as db:
            query = db.query(ReportResult).order_by(ReportResult.date.desc())

            # report_type 필터링
            if report_type:
                query = query.filter(ReportResult.report_type == report_type)

            # limit 적용
            results = query.limit(limit).all()

            # 리포트 목록 생성
            reports = []
            for result in results:
                content = json.loads(result.content)
                reports.append({
                    "date": result.date,
                    "report_type": result.report_type,
                    "generated_at": result.generated_at.isoformat() if result.generated_at else None,
                    "summary": content.get("market_forecast", "")[:100] + "..." if "market_forecast" in content else "",
                    "id": f"report_{result.report_type}_{result.date}"
                })

        return {
            "success": True,
            "data": {
                "total": len(reports),
                "reports": reports
            }
        }

    except Exception as e:
        logger.error(f"리포트 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_report_stats():
    """
    리포트 생성 통계

    Args:
        None

    Returns:
        리포트 통계

    Example:
        GET /api/v1/reports/stats

        Response:
        {
            "success": true,
            "data": {
                "total_reports": 60,
                "by_type": {
                    "morning": 30,
                    "afternoon": 30
                },
                "last_generated": {
                    "morning": "2025-11-06T08:30:00",
                    "afternoon": "2025-11-06T15:40:00"
                },
                "average_tokens": {
                    "morning": 2500,
                    "afternoon": 3000
                },
                "total_cost_estimate": 1.5  # USD
            }
        }
    """
    try:
        from sqlalchemy import func

        with get_db() as db:
            # 전체 리포트 수
            total_reports = db.query(func.count(ReportResult.id)).scalar()

            # 타입별 리포트 수
            type_counts = db.query(
                ReportResult.report_type,
                func.count(ReportResult.id)
            ).group_by(ReportResult.report_type).all()

            by_type = {report_type: count for report_type, count in type_counts}

            # 마지막 생성 시간 (타입별)
            last_generated = {}
            for report_type in ["morning", "afternoon"]:
                last_report = db.query(ReportResult).filter(
                    ReportResult.report_type == report_type
                ).order_by(ReportResult.generated_at.desc()).first()

                if last_report:
                    last_generated[report_type] = last_report.generated_at.isoformat()

            # 평균 토큰 사용량 (타입별)
            token_averages = db.query(
                ReportResult.report_type,
                func.avg(ReportResult.tokens_used)
            ).group_by(ReportResult.report_type).all()

            average_tokens = {
                report_type: round(avg_tokens, 0) if avg_tokens else 0
                for report_type, avg_tokens in token_averages
            }

            # 총 토큰 사용량
            total_tokens = db.query(func.sum(ReportResult.tokens_used)).scalar() or 0

            # 비용 추정 (Gemini 2.5 Pro: $0.00125 per 1K tokens for input)
            # 실제로는 input/output 토큰 구분 필요, 여기서는 단순화
            cost_per_1k_tokens = 0.00125
            total_cost_estimate = round((total_tokens / 1000) * cost_per_1k_tokens, 2)

        return {
            "success": True,
            "data": {
                "total_reports": total_reports,
                "by_type": by_type,
                "last_generated": last_generated,
                "average_tokens": average_tokens,
                "total_cost_estimate": total_cost_estimate
            }
        }

    except Exception as e:
        logger.error(f"리포트 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
