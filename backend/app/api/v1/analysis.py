# 참고: docs/architecture/03-api-design.md
# 참고: docs/backend/06-company-analysis.md

"""
기업 분석 API 엔드포인트

LLM 기반 기업 분석 조회
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
import logging
from datetime import datetime

# Note: AnalysisResponse, Analysis 모델은 더 이상 사용하지 않음
# 프론트엔드 CompanyAnalysis 타입과 호환되는 딕셔너리를 직접 반환
from app.services import AnalysisService
from app.api.dependencies import get_analysis_service
from app.db.models import AnalysisResult
from app.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])


# TODO batch, popular 모두 LLM CALL 를 worker 을 늘려 처리하도록 수정
@router.post("/batch")
async def batch_analyze(
    tickers: List[str] = Query(..., description="종목 코드 리스트 (최대 10개)"),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    여러 종목 일괄 분석

    Args:
        tickers: 종목 코드 리스트 (최대 10개)

    Returns:
        분석 결과 맵

    Example:
        POST /api/v1/analysis/batch?tickers=005930&tickers=000660

        Response:
        {
            "success": true,
            "data": {
                "total": 2,
                "succeeded": 2,
                "failed": 0,
                "analyses": {
                    "005930": {...},
                    "000660": {...}
                },
                "errors": {}
            }
        }
    """
    try:
        # 종목 수 제한
        if len(tickers) > 10:
            raise HTTPException(
                status_code=400,
                detail="최대 10개 종목까지 분석 가능합니다"
            )

        if len(tickers) == 0:
            raise HTTPException(
                status_code=400,
                detail="최소 1개 종목을 지정해야 합니다"
            )

        logger.info(f"배치 분석 요청: {len(tickers)}개 종목")

        # 일괄 분석
        results = await analysis_service.batch_analyze(tickers)

        # 성공/실패 분리
        analyses = {}
        errors = {}

        for ticker in tickers:
            if ticker in results:
                analyses[ticker] = results[ticker]
            else:
                errors[ticker] = "분석 실패"

        return {
            "success": True,
            "data": {
                "total": len(tickers),
                "succeeded": len(analyses),
                "failed": len(errors),
                "analyses": analyses,
                "errors": errors
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"배치 분석 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular")
async def get_popular_analysis(
    limit: int = Query(10, description="조회 개수", ge=1, le=20),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    주요 종목 분석 조회

    거래대금 상위 종목의 분석 결과 반환

    Args:
        limit: 조회 개수 (기본값: 10)

    Returns:
        분석 결과 리스트

    Example:
        GET /api/v1/analysis/popular?limit=10

        Response:
        {
            "success": true,
            "data": {
                "date": "2025-11-06",
                "analyses": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "summary": "...",
                        "opinion": "STRONG_BUY",
                        ...
                    },
                    ...
                ]
            }
        }
    """
    try:
        logger.info(f"주요 종목 분석 조회: Top {limit}")

        # 거래대금 상위 종목 분석
        today = datetime.now()
        analyses = await analysis_service.get_popular_stocks_analysis(
            date=today,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "date": today.strftime("%Y-%m-%d"),
                "analyses": analyses
            }
        }

    except Exception as e:
        logger.error(f"주요 종목 분석 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}")
async def get_company_analysis(
    ticker: str,
    force_refresh: bool = Query(
        False,
        description="캐시 무시하고 재분석 (기본값: False)"
    ),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    기업 분석 조회

    캐싱 전략:
    - 캐시 TTL: 24시간
    - 캐시 무효화: 중요 공시, 급등/급락 (10% 이상) - 스케줄러에서 장 마감 후 자동 처리 (scheduler/jobs.py)

    Args:
        ticker: 종목 코드
        force_refresh: 강제 재분석 여부

    Returns:
        프론트엔드 CompanyAnalysis 타입과 호환되는 분석 결과

    Example:
        GET /api/v1/analysis/005930

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "date": "2025-12-03",
                "summary": {
                    "opinion": "strong_buy",
                    "target_price": 80000,
                    "current_price": 72000,
                    "upside": 11.1,
                    "key_points": ["HBM3 수주 증가", "AI 반도체 성장", "글로벌 점유율 1위"]
                },
                "financial_analysis": {
                    "profitability": "ROE 15.2%로 업계 평균 상회",
                    "growth": "매출 YoY 12.5% 성장",
                    "stability": "부채비율 45%로 안정적",
                    "valuation": "PER 12.5배로 저평가"
                },
                "industry_analysis": {
                    "industry_trend": "반도체 업황 회복세",
                    "competitive_advantage": "메모리 반도체 글로벌 1위",
                    "market_position": "시장 지배적 위치"
                },
                "technical_analysis": {
                    "trend": "상승 추세",
                    "support_resistance": "지지 70,000원 / 저항 75,000원",
                    "indicators": "RSI 65, MACD 골든크로스"
                },
                "news_analysis": {
                    "sentiment": "positive",
                    "key_news": ["AI 반도체 수주 계약 체결", "HBM3 양산 가속화"],
                    "impact": "긍정적 뉴스가 다수로 단기 주가 상승 기대"
                },
                "risk_factors": [
                    "미중 무역 분쟁 심화 가능성",
                    "글로벌 반도체 수요 둔화 우려",
                    "환율 변동성 확대"
                ],
                "investment_strategy": {
                    "short_term": "단기 조정 시 분할 매수",
                    "mid_term": "3개월 목표가 80,000원",
                    "long_term": "장기 보유 추천"
                },
                "generated_at": "2025-12-03T10:30:00",
                "model_name": "gemini-2.5-pro",
                "tokens_used": 2500
            }
        }
    """
    try:
        logger.info(f"기업 분석 요청: {ticker} (force_refresh={force_refresh})")

        # 기업 분석 조회 (캐시 포함)
        analysis = await analysis_service.get_analysis(
            ticker=ticker,
            force_refresh=force_refresh
        )

        return {"success": True, "data": analysis}

    except ValueError as e:
        logger.error(f"잘못된 종목 코드 ({ticker}): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"기업 분석 조회 실패 ({ticker}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticker}/refresh")
async def refresh_analysis(
    ticker: str,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    기업 분석 강제 재생성

    캐시를 무효화하고 새로운 분석 생성

    Args:
        ticker: 종목 코드

    Returns:
        재생성된 분석 결과

    Example:
        POST /api/v1/analysis/005930/refresh

        Response:
        {
            "success": true,
            "data": {...},  # 새로운 분석 결과
            "message": "분석이 재생성되었습니다"
        }
    """
    try:
        logger.info(f"기업 분석 재생성 요청: {ticker}")

        # 캐시 무효화
        await analysis_service.invalidate_cache(ticker)

        # 새로운 분석 생성
        analysis = await analysis_service.get_analysis(
            ticker=ticker,
            force_refresh=True
        )

        return {
            "success": True,
            "data": analysis,
            "message": "분석이 재생성되었습니다"
        }

    except ValueError as e:
        logger.error(f"잘못된 종목 코드 ({ticker}): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"기업 분석 재생성 실패 ({ticker}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/cache-status")
async def get_cache_status(ticker: str):
    """
    분석 캐시 상태 조회 (DB 기반)

    Args:
        ticker: 종목 코드

    Returns:
        캐시 상태 정보

    Example:
        GET /api/v1/analysis/005930/cache-status

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "cache_exists": true,
                "cache_key": "analysis:005930:2025-11-06",
                "cached_at": "2025-11-06T10:30:00",
                "expires_at": "2025-11-07T00:00:00",
                "ttl_seconds": 43200
            }
        }
    """
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"analysis:{ticker}:{today}"

        # DB에서 캐시 조회
        with get_db() as db:
            cached = db.query(AnalysisResult).filter(
                AnalysisResult.ticker == ticker,
                AnalysisResult.date == today
            ).first()

            if not cached:
                return {
                    "success": True,
                    "data": {
                        "ticker": ticker,
                        "cache_exists": False,
                        "cache_key": cache_key,
                        "message": "캐시가 없습니다"
                    }
                }

            # 세션이 열려있는 동안 데이터 추출
            cached_at = cached.generated_at.isoformat() if cached.generated_at else None

        # TTL 계산 (자정까지 남은 시간)
        from datetime import datetime as dt, timedelta
        now = dt.now()
        midnight = dt.combine(dt.today() + timedelta(days=1), dt.min.time())
        ttl_seconds = int((midnight - now).total_seconds())

        return {
            "success": True,
            "data": {
                "ticker": ticker,
                "cache_exists": True,
                "cache_key": cache_key,
                "cached_at": cached_at,
                "expires_at": midnight.isoformat(),
                "ttl_seconds": ttl_seconds
            }
        }

    except Exception as e:
        logger.error(f"캐시 상태 조회 실패 ({ticker}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ticker}/comparison")
async def compare_with_peers(
    ticker: str,
    sector: Optional[str] = Query(None, description="업종 (미지정 시 자동 감지)"),
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    동종 업종 비교 분석

    Args:
        ticker: 종목 코드
        sector: 업종 (미지정 시 해당 종목의 업종)

    Returns:
        업종 내 비교 분석

    Example:
        GET /api/v1/analysis/005930/comparison

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "name": "삼성전자",
                "sector": "전기전자",
                "sector_average": {
                    "per": 15.3,
                    "pbr": 2.1,
                    "roe": 12.5
                },
                "comparison": {
                    "per": "하회",  # 업종 평균 대비
                    "pbr": "하회",
                    "roe": "상회"
                },
                "ranking": {
                    "market_cap": 1,
                    "per": 3,
                    "roe": 2
                },
                "peers": [
                    {
                        "ticker": "000660",
                        "name": "SK하이닉스",
                        "per": 14.2,
                        "pbr": 1.9
                    },
                    ...
                ]
            }
        }
    """
    try:
        logger.info(f"동종 업종 비교 분석 요청: {ticker}")

        # TODO: 실제 구현 시 업종별 비교 로직 필요
        # 현재는 더미 데이터 반환

        # 기본 정보 조회
        stock_info = await analysis_service.data_service.get_stock_info(ticker)

        # 재무 데이터 조회
        financial = await analysis_service.data_service.get_financial_data(ticker)

        # 더미 응답 (실제로는 동종 업종 종목들과 비교)
        return {
            "success": True,
            "data": {
                "ticker": ticker,
                "name": stock_info['name'],
                "sector": sector or "미분류",
                "sector_average": {
                    "per": 15.3,
                    "pbr": 2.1,
                    "roe": 12.5
                },
                "comparison": {
                    "per": "하회" if financial.get('per', 0) < 15.3 else "상회",
                    "pbr": "하회" if financial.get('pbr', 0) < 2.1 else "상회",
                    "roe": "상회" if financial.get('roe', 0) > 12.5 else "하회"
                },
                "ranking": {
                    "market_cap": 1,
                    "per": 3,
                    "roe": 2
                },
                "peers": [
                    {
                        "ticker": "000660",
                        "name": "SK하이닉스",
                        "per": 14.2,
                        "pbr": 1.9,
                        "roe": 13.5
                    }
                ],
                "message": "동종 업종 비교 기능은 향후 구현 예정입니다"
            }
        }

    except ValueError as e:
        logger.error(f"잘못된 종목 코드 ({ticker}): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"동종 업종 비교 실패 ({ticker}): {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
