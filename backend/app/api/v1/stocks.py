# 참고: docs/architecture/03-api-design.md
# 참고: docs/backend/01-data-collection.md

"""
종목 관련 API 엔드포인트

종목 정보 조회, 가격 히스토리 조회 등
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime, timedelta
from typing import Optional
import logging

from app.models import Stock, StockResponse, StockPriceHistoryResponse
from app.services import DataService
from app.api.dependencies import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/{ticker}", response_model=StockResponse)
async def get_stock_info(
    ticker: str,
    data_service: DataService = Depends(get_data_service)
):
    """
    종목 기본 정보 조회 (DB 저장 데이터 중심)

    Args:
        ticker: 종목 코드 (예: 005930)

    Returns:
        StockResponse: 종목 정보 (재무 지표 포함)

    Example:
        GET /api/v1/stocks/005930

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "name": "삼성전자",
                "market": "KOSPI",
                "market_cap": 4300000,
                "per": 15.5,
                "pbr": 1.2,
                "roe": 8.5,
                "debt_ratio": 35.2
            }
        }
    """
    try:
        # ticker를 6자리로 변환
        ticker = str(ticker).zfill(6)

        # DB에서 재무 데이터 조회
        from app.db.database import get_db
        from app.db.models import FinancialData

        with get_db() as db:
            financial_data = db.query(FinancialData).filter(
                FinancialData.ticker == ticker
            ).first()

            if not financial_data:
                raise ValueError(f"종목 {ticker}의 정보를 찾을 수 없습니다")

            # 시장 정보: DB에 있으면 사용, 없으면 기본값
            market = financial_data.market or 'KOSPI'

            # Stock 모델로 변환 (세션 안에서 모든 속성 접근)
            stock = Stock(
                ticker=financial_data.ticker,
                name=financial_data.name or ticker,
                market=market,
                market_cap=int(financial_data.market_cap) if financial_data.market_cap else 0,
                per=float(financial_data.per) if financial_data.per else None,
                pbr=float(financial_data.pbr) if financial_data.pbr else None,
                eps=float(financial_data.eps) if financial_data.eps else None,
                bps=float(financial_data.bps) if financial_data.bps else None,
                roe=float(financial_data.roe) if financial_data.roe else None,
                debt_ratio=float(financial_data.debt_ratio) if financial_data.debt_ratio else None,
                div=float(financial_data.div) if financial_data.div else None,
                dps=float(financial_data.dps) if financial_data.dps else None,
                revenue_growth_yoy=float(financial_data.revenue_growth_yoy) if financial_data.revenue_growth_yoy else None,
                updated_at=financial_data.updated_at.isoformat() if financial_data.updated_at else None
            )

        return StockResponse(success=True, data=stock)

    except ValueError as e:
        logger.error(f"종목 정보 조회 실패 ({ticker}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"종목 정보 조회 중 예상치 못한 오류 ({ticker}): {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")


@router.get("/{ticker}/price", response_model=StockPriceHistoryResponse)
async def get_price_history(
    ticker: str,
    start_date: Optional[str] = Query(
        None,
        description="시작일 (YYYY-MM-DD)",
        example="2025-10-01"
    ),
    end_date: Optional[str] = Query(
        None,
        description="종료일 (YYYY-MM-DD, 기본값: 오늘)",
        example="2025-11-06"
    ),
    period: Optional[int] = Query(
        30,
        description="기간 (일, start_date 미지정 시 사용)",
        ge=1,
        le=365
    ),
    data_service: DataService = Depends(get_data_service)
):
    """
    종목 가격 히스토리 조회

    Args:
        ticker: 종목 코드
        start_date: 시작일 (선택)
        end_date: 종료일 (선택, 기본값: 오늘)
        period: 기간 (일, start_date 미지정 시 사용)

    Returns:
        StockPriceHistoryResponse: 가격 히스토리

    Example:
        GET /api/v1/stocks/005930/price?period=30

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "period": {
                    "start": "2025-10-01",
                    "end": "2025-11-06"
                },
                "prices": [
                    {
                        "date": "2025-10-01",
                        "open": 70000,
                        "high": 74000,
                        "low": 69500,
                        "close": 72000,
                        "volume": 15000000,
                        "trading_value": 1080000000000
                    },
                    ...
                ]
            }
        }
    """
    try:
        # 날짜 파싱 및 유효성 검증
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = datetime.now()

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            # start_date 미지정 시 period 기반 계산
            start_dt = end_dt - timedelta(days=period)

        # DataService로 가격 히스토리 조회
        df = await data_service.get_price_history(ticker, start_dt, end_dt)

        if df.empty:
            raise ValueError(f"종목 {ticker}의 가격 데이터가 없습니다")

        # DataFrame을 리스트로 변환
        prices = []
        for _, row in df.iterrows():
            # 날짜 변환 (datetime → YYYY-MM-DD)
            date_val = row['date']
            if isinstance(date_val, str):
                date_str = date_val
            else:
                date_str = date_val.strftime("%Y-%m-%d")

            prices.append({
                "date": date_str,
                "open": int(row['시가']),
                "high": int(row['고가']),
                "low": int(row['저가']),
                "close": int(row['종가']),
                "volume": int(row['거래량']),
                "trading_value": int(row['종가'] * row['거래량'])
            })

        # StockPriceHistoryResponse 반환
        response_data = {
            "ticker": ticker,
            "period": {
                "start": start_dt.strftime("%Y-%m-%d"),
                "end": end_dt.strftime("%Y-%m-%d")
            },
            "prices": prices
        }

        return StockPriceHistoryResponse(success=True, data=response_data)

    except ValueError as e:
        logger.error(f"가격 히스토리 조회 실패 ({ticker}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"가격 히스토리 조회 중 예상치 못한 오류 ({ticker}): {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")


@router.get("/{ticker}/current")
async def get_current_price(
    ticker: str,
    data_service: DataService = Depends(get_data_service)
):
    """
    종목 현재가 조회

    Args:
        ticker: 종목 코드

    Returns:
        현재가 정보

    Example:
        GET /api/v1/stocks/005930/current

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "name": "삼성전자",
                "current_price": 72000,
                "change_rate": 2.5,
                "volume": 15000000,
                "trading_value": 1080000000000,
                "timestamp": "2025-11-06T14:30:00"
            }
        }
    """
    try:
        # ticker를 6자리로 변환
        ticker = str(ticker).zfill(6)

        # 실시간 가격 직접 조회 (realtime_prices 우선)
        realtime = await data_service.get_realtime_price(ticker)

        if realtime:
            # KIS 실시간 데이터 사용
            stock_info = await data_service.get_stock_info(ticker)

            response_data = {
                "ticker": ticker,
                "name": stock_info['name'],
                "current_price": realtime['current_price'],
                "change_rate": realtime['change_rate'],
                "volume": realtime['volume'],
                "trading_value": realtime['trading_value'],
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            }

            return {"success": True, "data": response_data}

        else:
            # pykrx 폴백 (realtime_prices 없을 때)
            current_price = await data_service.get_current_price(ticker)
            stock_info = await data_service.get_stock_info(ticker)

            # pykrx에서는 실시간 정보 부족, 기본값 사용
            response_data = {
                "ticker": ticker,
                "name": stock_info['name'],
                "current_price": current_price,
                "change_rate": 0.0,
                "volume": 0,
                "trading_value": 0,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            }

            return {"success": True, "data": response_data}

    except ValueError as e:
        logger.error(f"현재가 조회 실패 ({ticker}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"현재가 조회 중 예상치 못한 오류 ({ticker}): {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")


@router.get("/")
async def search_stocks(
    keyword: Optional[str] = Query(None, description="검색 키워드 (종목명 or 코드)"),
    market: Optional[str] = Query(None, description="시장 (KOSPI/KOSDAQ)"),
    min_per: Optional[float] = Query(None, description="최소 PER", ge=0),
    max_per: Optional[float] = Query(None, description="최대 PER"),
    min_pbr: Optional[float] = Query(None, description="최소 PBR", ge=0),
    max_pbr: Optional[float] = Query(None, description="최대 PBR"),
    min_roe: Optional[float] = Query(None, description="최소 ROE (%)"),
    max_roe: Optional[float] = Query(None, description="최대 ROE (%)"),
    min_market_cap: Optional[float] = Query(None, description="최소 시가총액 (억원)"),
    max_market_cap: Optional[float] = Query(None, description="최대 시가총액 (억원)"),
    sort_by: Optional[str] = Query(None, description="정렬 기준 (market_cap/per/pbr/roe/name)"),
    sort_order: Optional[str] = Query("desc", description="정렬 순서 (asc/desc)"),
    limit: int = Query(20, description="최대 결과 수", ge=1, le=500),
    data_service: DataService = Depends(get_data_service)
):
    """
    종목 검색

    Args:
        keyword: 검색 키워드
        market: 시장 필터 (KOSPI/KOSDAQ)
        limit: 최대 결과 수

    Returns:
        종목 리스트

    Example:
        GET /api/v1/stocks?keyword=삼성&market=KOSPI&limit=10

        Response:
        {
            "success": true,
            "data": {
                "total": 3,
                "stocks": [
                    {
                        "ticker": "005930",
                        "name": "삼성전자",
                        "market": "KOSPI",
                        "market_cap": 430000000000000
                    },
                    ...
                ]
            }
        }
    """
    try:
        from app.db.database import get_db
        from app.db.models import FinancialData
        from sqlalchemy import or_

        stocks = []

        # keyword가 콤마로 구분된 ticker 리스트인 경우 (예: "005930,000660,035420")
        if keyword and ',' in keyword:
            tickers = [k.strip() for k in keyword.split(',')]

            # DB에서 해당 ticker만 조회 (빠름)
            with get_db() as db:
                financial_data = db.query(FinancialData).filter(
                    FinancialData.ticker.in_(tickers)
                ).all()

                for f in financial_data:
                    stocks.append({
                        "ticker": f.ticker,
                        "name": f.name,
                        "market": f.market or "KOSPI",
                        "market_cap": int(f.market_cap) if f.market_cap else 0,
                        "per": f.per,
                        "pbr": f.pbr,
                        "roe": f.roe
                    })

            return {
                "success": True,
                "data": {
                    "total": len(stocks),
                    "stocks": stocks
                }
            }

        # keyword가 검색어인 경우
        elif keyword:
            with get_db() as db:
                # DB에서 종목명 또는 ticker로 검색 (LIKE 쿼리)
                query = db.query(FinancialData).filter(
                    or_(
                        FinancialData.name.like(f"%{keyword}%"),
                        FinancialData.ticker.like(f"%{keyword}%")
                    )
                )

                # market 필터링
                if market:
                    query = query.filter(FinancialData.market == market)

                financial_data = query.limit(limit).all()

                for f in financial_data:
                    stocks.append({
                        "ticker": f.ticker,
                        "name": f.name,
                        "market": f.market or "KOSPI",
                        "market_cap": int(f.market_cap) if f.market_cap else 0,
                        "per": f.per,
                        "pbr": f.pbr,
                        "roe": f.roe
                    })

            return {
                "success": True,
                "data": {
                    "total": len(stocks),
                    "stocks": stocks
                }
            }

        # keyword가 없는 경우 - DB에서 전체 조회 (다양한 필터링 지원)
        else:
            with get_db() as db:
                query = db.query(FinancialData)

                # market 필터링
                if market:
                    query = query.filter(FinancialData.market == market)

                # PER 필터링 (0보다 큰 값만)
                if min_per is not None:
                    query = query.filter(FinancialData.per >= min_per, FinancialData.per > 0)
                if max_per is not None:
                    query = query.filter(FinancialData.per <= max_per, FinancialData.per > 0)

                # PBR 필터링 (0보다 큰 값만)
                if min_pbr is not None:
                    query = query.filter(FinancialData.pbr >= min_pbr, FinancialData.pbr > 0)
                if max_pbr is not None:
                    query = query.filter(FinancialData.pbr <= max_pbr, FinancialData.pbr > 0)

                # ROE 필터링
                if min_roe is not None:
                    query = query.filter(FinancialData.roe >= min_roe)
                if max_roe is not None:
                    query = query.filter(FinancialData.roe <= max_roe)

                # 시가총액 필터링
                if min_market_cap is not None:
                    query = query.filter(FinancialData.market_cap >= min_market_cap)
                if max_market_cap is not None:
                    query = query.filter(FinancialData.market_cap <= max_market_cap)

                # 정렬
                if sort_by:
                    from sqlalchemy import asc, desc
                    sort_column = getattr(FinancialData, sort_by, None)
                    if sort_column is not None:
                        if sort_order == "asc":
                            query = query.order_by(asc(sort_column))
                        else:
                            query = query.order_by(desc(sort_column))
                else:
                    # 기본 정렬: 시가총액 내림차순
                    from sqlalchemy import desc
                    query = query.order_by(desc(FinancialData.market_cap))

                financial_data = query.limit(limit).all()

                for f in financial_data:
                    stocks.append({
                        "ticker": f.ticker,
                        "name": f.name,
                        "market": f.market or "KOSPI",
                        "market_cap": int(f.market_cap) if f.market_cap else 0,
                        "per": f.per,
                        "pbr": f.pbr,
                        "roe": f.roe
                    })

            return {
                "success": True,
                "data": {
                    "total": len(stocks),
                    "stocks": stocks
                }
            }

    except Exception as e:
        logger.error(f"종목 검색 중 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")


@router.get("/{ticker}/technical")
async def get_technical_indicators(
    ticker: str,
    date: Optional[str] = Query(None, description="기준일 (YYYY-MM-DD, 기본값: 오늘)"),
    data_service: DataService = Depends(get_data_service)
):
    """
    종목 기술적 지표 조회

    Args:
        ticker: 종목 코드
        date: 기준일

    Returns:
        기술적 지표

    Example:
        GET /api/v1/stocks/005930/technical

        Response:
        {
            "success": true,
            "data": {
                "ticker": "005930",
                "date": "2025-11-06",
                "rsi": 65.0,
                "macd": 120.5,
                "macd_signal": 115.3,
                "macd_status": "golden_cross",
                "ma5": 71000,
                "ma20": 70000,
                "ma60": 68000,
                "ma_position": "상회"
            }
        }
    """
    try:
        # ticker를 6자리로 변환
        ticker = str(ticker).zfill(6)

        # 날짜 파싱 (기본값: 오늘)
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            target_date = datetime.now()

        # DataService로 기술적 지표 조회
        indicators = await data_service.get_technical_indicators(ticker, target_date)

        # 응답 구성
        response_data = {
            "ticker": ticker,
            "date": target_date.strftime("%Y-%m-%d"),
            **indicators
        }

        return {"success": True, "data": response_data}

    except ValueError as e:
        logger.error(f"기술적 지표 조회 실패 ({ticker}): {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"기술적 지표 조회 중 예상치 못한 오류 ({ticker}): {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {e}")
