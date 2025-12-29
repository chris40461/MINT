# 참고: docs/backend/02-trigger-detection.md
# 참고: docs/database/01-schema-design.md

"""
급등주 트리거 데이터 모델

6개 트리거 타입 및 급등주 감지 결과 모델을 정의합니다.
"""

from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime


# 트리거 타입 정의
TriggerType = Literal[
    "volume_surge",        # 거래량 급증
    "gap_up",              # 갭 상승
    "fund_inflow",         # 자금 유입
    "intraday_rise",       # 일중 상승
    "closing_strength",    # 마감 강도
    "sideways_volume"      # 횡보주 거래량
]

SessionType = Literal["morning", "afternoon"]


class Trigger(BaseModel):
    """급등주 트리거 결과"""

    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    trigger_type: TriggerType = Field(..., description="트리거 타입")
    current_price: int = Field(..., description="현재가")
    change_rate: float = Field(..., description="등락률 (%)")
    volume: int = Field(..., description="거래량")
    trading_value: int = Field(..., description="거래대금")
    composite_score: float = Field(..., description="복합 점수 (0-1)")
    session: SessionType = Field(..., description="세션 (morning/afternoon)")
    detected_at: datetime = Field(default_factory=datetime.now, description="감지 시간")

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "005930",
                "name": "삼성전자",
                "trigger_type": "volume_surge",
                "current_price": 72000,
                "change_rate": 5.2,
                "volume": 20_000_000,
                "trading_value": 1_440_000_000_000,
                "composite_score": 0.85,
                "session": "morning",
                "detected_at": "2025-11-06T09:15:00"
            }
        }


class TriggerMetadata(BaseModel):
    """트리거 메타데이터"""

    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    session: SessionType = Field(..., description="세션")
    total: int = Field(..., description="전체 트리거 수")
    trigger_types: dict = Field(..., description="트리거 타입별 개수")


class TriggerResponse(BaseModel):
    """급등주 트리거 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: dict = Field(..., description="트리거 데이터")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "triggers": [],
                    "metadata": {
                        "date": "2025-11-06",
                        "session": "morning",
                        "total": 18,
                        "trigger_types": {
                            "volume_surge": 3,
                            "gap_up": 3,
                            "fund_inflow": 3
                        }
                    }
                }
            }
        }
