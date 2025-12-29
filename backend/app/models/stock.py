# 참고: docs/database/01-schema-design.md
# 참고: docs/architecture/03-api-design.md

"""
종목 관련 데이터 모델

Stock, StockPrice 등 종목 기본 정보 및 가격 데이터 모델을 정의합니다.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class Stock(BaseModel):
    """종목 기본 정보 (DB 저장 데이터 중심)"""

    ticker: str = Field(..., description="종목 코드 (예: 005930)")
    name: str = Field(..., description="종목명 (예: 삼성전자)")
    market: str = Field(..., description="시장 (KOSPI/KOSDAQ)")
    market_cap: int = Field(..., description="시가총액 (억원)")
    sector: Optional[str] = Field(None, description="업종")

    # 재무 지표 (DB에서 조회, 선택적)
    per: Optional[float] = Field(None, description="PER (주가수익비율)")
    pbr: Optional[float] = Field(None, description="PBR (주가순자산비율)")
    eps: Optional[float] = Field(None, description="EPS (주당순이익)")
    bps: Optional[float] = Field(None, description="BPS (주당순자산)")
    roe: Optional[float] = Field(None, description="ROE (자기자본이익률, %)")
    debt_ratio: Optional[float] = Field(None, description="부채비율 (%)")
    div: Optional[float] = Field(None, description="배당수익률 (%)")
    dps: Optional[float] = Field(None, description="주당배당금")
    revenue_growth_yoy: Optional[float] = Field(None, description="매출 성장률 (YoY, %)")
    updated_at: Optional[str] = Field(None, description="재무 데이터 업데이트 일시")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "005930",
                "name": "삼성전자",
                "market": "KOSPI",
                "market_cap": 4300000,  # 430조 -> 4300000억
                "sector": "전기전자",
                "per": 15.5,
                "pbr": 1.2,
                "eps": 5000,
                "bps": 45000,
                "roe": 8.5,
                "debt_ratio": 35.2,
                "div": 2.5,
                "dps": 1800
            }
        }


class StockPrice(BaseModel):
    """종목 가격 정보"""

    ticker: str = Field(..., description="종목 코드")
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    open: int = Field(..., description="시가")
    high: int = Field(..., description="고가")
    low: int = Field(..., description="저가")
    close: int = Field(..., description="종가")
    volume: int = Field(..., description="거래량")
    trading_value: int = Field(..., description="거래대금")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "005930",
                "date": "2025-11-06",
                "open": 70000,
                "high": 74000,
                "low": 69500,
                "close": 72000,
                "volume": 15_000_000,
                "trading_value": 1_080_000_000_000
            }
        }


class StockResponse(BaseModel):
    """종목 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: Stock = Field(..., description="종목 데이터")


class StockPriceHistoryResponse(BaseModel):
    """종목 가격 히스토리 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: dict = Field(..., description="가격 히스토리 데이터")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "ticker": "005930",
                    "period": {
                        "start": "2025-10-01",
                        "end": "2025-11-06"
                    },
                    "prices": []
                }
            }
        }
