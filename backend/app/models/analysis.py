# 참고: docs/backend/06-company-analysis.md
# 참고: docs/backend/05-llm-service.md

"""
기업 분석 데이터 모델

기업 분석 결과, 재무 분석, 뉴스 분석, 기술적 분석 모델을 정의합니다.
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from datetime import datetime


OpinionType = Literal["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]


class FinancialData(BaseModel):
    """재무 데이터"""

    roe: float = Field(..., description="ROE (%)")
    per: float = Field(..., description="PER")
    pbr: float = Field(..., description="PBR")
    debt_ratio: float = Field(..., description="부채비율 (%)")
    revenue_growth_yoy: float = Field(..., description="매출 성장률 (%)")


class NewsData(BaseModel):
    """뉴스 데이터"""

    positive_count: int = Field(..., description="긍정 뉴스 개수")
    negative_count: int = Field(..., description="부정 뉴스 개수")
    neutral_count: int = Field(..., description="중립 뉴스 개수")
    sentiment: Literal["positive", "neutral", "negative"] = Field(..., description="종합 센티먼트")


class TechnicalData(BaseModel):
    """기술적 지표 데이터"""

    rsi: float = Field(..., description="RSI (0-100)")
    macd_status: Literal["golden_cross", "dead_cross", "neutral"] = Field(..., description="MACD 상태")
    ma_position: Literal["상회", "하회", "중립"] = Field(..., description="이동평균선 위치")


class Analysis(BaseModel):
    """기업 분석 결과"""

    # 기본 정보
    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    current_price: int = Field(..., description="현재가 (원)")
    change_rate: float = Field(..., description="등락률 (%)")
    market_cap: int = Field(..., description="시가총액 (억원)")

    # 분석 결과
    summary: str = Field(..., description="한줄 요약")
    opinion: OpinionType = Field(..., description="투자 의견")
    target_price: int = Field(..., description="목표가")

    # 상세 분석
    financial: FinancialData = Field(..., description="재무 분석")
    news: NewsData = Field(..., description="뉴스 분석")
    technical: TechnicalData = Field(..., description="기술적 분석")
    risks: List[str] = Field(..., description="리스크 요인")

    # 메타데이터
    analyzed_at: datetime = Field(default_factory=datetime.now, description="분석 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "005930",
                "name": "삼성전자",
                "current_price": 72000,
                "change_rate": 5.2,
                "market_cap": 4_300_000,  # 억원
                "summary": "HBM3 수주 증가로 향후 3개월간 상승 여력 높음",
                "opinion": "STRONG_BUY",
                "target_price": 80000,
                "financial": {
                    "roe": 15.2,
                    "per": 12.5,
                    "pbr": 1.8,
                    "debt_ratio": 45.0,
                    "revenue_growth_yoy": 12.5
                },
                "news": {
                    "positive_count": 8,
                    "negative_count": 2,
                    "neutral_count": 3,
                    "sentiment": "positive"
                },
                "technical": {
                    "rsi": 65.0,
                    "macd_status": "golden_cross",
                    "ma_position": "상회"
                },
                "risks": [
                    "미중 무역 분쟁 심화 가능성",
                    "글로벌 반도체 수요 둔화 우려",
                    "환율 변동성 확대"
                ],
                "analyzed_at": "2025-11-06T10:30:00"
            }
        }


class AnalysisResponse(BaseModel):
    """기업 분석 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: Analysis = Field(..., description="분석 데이터")
