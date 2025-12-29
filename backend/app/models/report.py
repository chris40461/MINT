# 참고: docs/backend/07-market-reports.md

"""
장 시작/마감 리포트 데이터 모델

MorningReport, AfternoonReport 등 리포트 관련 모델을 정의합니다.
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Optional, Any, Union
from datetime import datetime


class EntryStrategy(BaseModel):
    """진입 전략 (상세)"""

    # Chain-of-Thought: 분석을 먼저 수행
    analysis: Optional[str] = Field(None, description="진입 판단 분석 (시간외 동향, ATR 변동성, 지지/저항 등)")

    entry_price: Union[int, float] = Field(..., description="진입가 (원)")
    entry_timing: str = Field(..., description="진입 타이밍")
    target_price_1: Union[int, float] = Field(..., description="1차 목표가 (원, ATR 기반)")
    target_price_2: Union[int, float] = Field(..., description="2차 목표가 (원, ATR 기반)")
    stop_loss: Union[int, float] = Field(..., description="손절가 (원, ATR 기반)")
    risk_reward_ratio: str = Field(..., description="손익비 (예: 1:2)")
    holding_period: str = Field(..., description="예상 보유기간")
    technical_basis: str = Field(..., description="기술적 근거")
    volume_strategy: str = Field(..., description="거래량 전략")
    exit_condition: str = Field(..., description="청산 조건")

    # Confidence Score
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="전략 신뢰도 (0.0~1.0)")


class TopStock(BaseModel):
    """주목 종목"""

    rank: int = Field(..., description="순위")
    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    current_price: Union[int, float] = Field(..., description="현재가")
    score: Optional[float] = Field(None, description="점수 (0-10)")
    reason: str = Field(..., description="선정 이유")
    entry_strategy: Optional[EntryStrategy] = Field(None, description="진입 전략")


class MorningReport(BaseModel):
    """장 시작 리포트"""

    report_type: Literal["morning"] = Field(default="morning", description="리포트 타입")
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시간")

    # 시장 전망
    market_forecast: str = Field(..., description="시장 전망")
    kospi_range: Dict[str, Any] = Field(..., description="KOSPI 예상 범위 (low, high, reasoning)")
    market_risks: Optional[List[str]] = Field(default_factory=list, description="주요 리스크 요인")

    # 주목 종목
    top_stocks: List[TopStock] = Field(..., description="주목 종목 Top 10")

    # 섹터 분석
    sector_analysis: Dict[str, Any] = Field(..., description="섹터 분석 (강세/약세)")

    # 투자 전략
    investment_strategy: str = Field(..., description="오늘의 투자 전략")
    daily_schedule: Optional[Dict[str, str]] = Field(default_factory=dict, description="시간대별 전략")

    # 메타데이터
    metadata: Dict = Field(default_factory=dict, description="메타데이터")

    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "morning",
                "date": "2025-11-06",
                "market_forecast": "오늘의 시장은 미국 증시 상승과 환율 안정에 힘입어 소폭 상승 출발 예상",
                "kospi_range": {
                    "low": 2630.0,
                    "high": 2680.0
                },
                "top_stocks": [],
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


class SurgeStock(BaseModel):
    """급등주"""

    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    change_rate: float = Field(default=0.0, description="등락률 (%)")
    trigger_type: str = Field(default="", description="트리거 타입")
    category: str = Field(default="", description="테마/업종")
    reason: str = Field(..., description="급등 이유")
    outlook: str = Field(..., description="향후 전망")


class MarketBreadth(BaseModel):
    """시장 폭 (Market Breadth) 분석"""

    sentiment: str = Field(..., description="시장 분위기 (강세장/약세장/혼조세)")
    interpretation: str = Field(..., description="상승/하락 종목 비율 해석")


class SectorInfo(BaseModel):
    """업종 정보"""

    sector: str = Field(..., description="업종명")
    change: str = Field(..., description="등락률 (예: +2.09%)")
    reason: str = Field(..., description="상승/하락 이유")


class SectorAnalysis(BaseModel):
    """업종별 분석"""

    bullish: List[SectorInfo] = Field(default_factory=list, description="강세 업종 목록")
    bearish: List[SectorInfo] = Field(default_factory=list, description="약세 업종 목록")


class ThemeAnalysis(BaseModel):
    """테마 분석"""

    theme: str = Field(..., description="테마명")
    drivers: str = Field(..., description="상승 원인")
    leading_stocks: List[str] = Field(default_factory=list, description="관련 대장주")


class ExtendedMarketSummary(BaseModel):
    """확장된 시장 요약 (KOSPI + KOSDAQ + 수급 + 시장폭)"""

    # KOSPI
    kospi_close: float = Field(default=0.0, description="KOSPI 종가")
    kospi_change: float = Field(default=0.0, description="KOSPI 등락률 (%)")
    kospi_point_change: float = Field(default=0.0, description="KOSPI 포인트 변동")

    # KOSDAQ
    kosdaq_close: float = Field(default=0.0, description="KOSDAQ 종가")
    kosdaq_change: float = Field(default=0.0, description="KOSDAQ 등락률 (%)")
    kosdaq_point_change: float = Field(default=0.0, description="KOSDAQ 포인트 변동")

    # 거래대금 (억원)
    trading_value: int = Field(default=0, description="전체 거래대금 (억원)")

    # 수급 - KOSPI (억원)
    foreign_net_kospi: int = Field(default=0, description="외국인 순매수 KOSPI (억원)")
    institution_net_kospi: int = Field(default=0, description="기관 순매수 KOSPI (억원)")
    individual_net_kospi: int = Field(default=0, description="개인 순매수 KOSPI (억원)")

    # 수급 - KOSDAQ (억원)
    foreign_net_kosdaq: int = Field(default=0, description="외국인 순매수 KOSDAQ (억원)")
    institution_net_kosdaq: int = Field(default=0, description="기관 순매수 KOSDAQ (억원)")
    individual_net_kosdaq: int = Field(default=0, description="개인 순매수 KOSDAQ (억원)")

    # 시장 폭
    advance_count: int = Field(default=0, description="상승 종목 수")
    decline_count: int = Field(default=0, description="하락 종목 수")
    unchanged_count: int = Field(default=0, description="보합 종목 수")


class AfternoonReport(BaseModel):
    """장 마감 리포트 (증권사 장마감 시황 보고서 형식)"""

    report_type: Literal["afternoon"] = Field(default="afternoon", description="리포트 타입")
    date: str = Field(..., description="날짜 (YYYY-MM-DD)")
    generated_at: datetime = Field(default_factory=datetime.now, description="생성 시간")

    # 시장 요약 (확장)
    market_summary: ExtendedMarketSummary = Field(..., description="확장된 시장 요약")
    market_summary_text: str = Field(default="", description="시장 요약 텍스트 (LLM 생성)")

    # 시장 폭 분석
    market_breadth: Optional[MarketBreadth] = Field(None, description="시장 폭 분석")

    # 업종별 분석
    sector_analysis: Optional[SectorAnalysis] = Field(None, description="업종별 분석")

    # 수급 해석
    supply_demand_analysis: str = Field(default="", description="수급 해석 텍스트")

    # 오늘의 테마
    today_themes: List[ThemeAnalysis] = Field(default_factory=list, description="오늘의 주도 테마")

    # 급등주 분석
    surge_stocks: List[SurgeStock] = Field(default_factory=list, description="급등주 상세 분석")

    # 내일 전략
    tomorrow_strategy: str = Field(..., description="내일의 투자 전략")

    # 체크 포인트
    check_points: List[str] = Field(default_factory=list, description="내일 확인할 주요 일정/이슈")

    # 메타데이터
    metadata: Dict = Field(default_factory=dict, description="메타데이터")

    class Config:
        json_schema_extra = {
            "example": {
                "report_type": "afternoon",
                "date": "2025-11-06",
                "market_summary": {
                    "kospi_close": 2650.34,
                    "kospi_change": 1.2,
                    "kospi_point_change": 31.5,
                    "kosdaq_close": 850.12,
                    "kosdaq_change": 0.8,
                    "kosdaq_point_change": 6.7,
                    "trading_value": 125000,
                    "foreign_net_kospi": 2500,
                    "institution_net_kospi": -1500,
                    "individual_net_kospi": -1000,
                    "foreign_net_kosdaq": 500,
                    "institution_net_kosdaq": 300,
                    "individual_net_kosdaq": -800,
                    "advance_count": 500,
                    "decline_count": 300,
                    "unchanged_count": 100
                },
                "market_summary_text": "KOSPI가 외국인 매수세에 힘입어 1.2% 상승 마감",
                "market_breadth": {
                    "sentiment": "강세장",
                    "interpretation": "상승 종목이 하락 종목을 압도하며 전반적 매수세 우위"
                },
                "sector_analysis": {
                    "bullish": [
                        {"sector": "전기전자", "change": "+2.09%", "reason": "반도체주 반등"}
                    ],
                    "bearish": [
                        {"sector": "건설", "change": "-1.5%", "reason": "금리 우려 지속"}
                    ]
                },
                "supply_demand_analysis": "외국인이 KOSPI에서 2,500억원 순매수하며 시장을 견인",
                "today_themes": [
                    {
                        "theme": "2차전지",
                        "drivers": "테슬라 실적 호조",
                        "leading_stocks": ["LG에너지솔루션", "삼성SDI"]
                    }
                ],
                "surge_stocks": [],
                "tomorrow_strategy": "반도체 섹터의 모멘텀 지속 관찰 필요",
                "check_points": [
                    "美 FOMC 회의 결과 발표",
                    "삼성전자 실적 발표"
                ],
                "metadata": {
                    "model": "gemini-2.5-pro",
                    "tokens_used": 3000
                }
            }
        }


class ReportResponse(BaseModel):
    """리포트 API 응답"""

    success: bool = Field(..., description="성공 여부")
    data: MorningReport | AfternoonReport = Field(..., description="리포트 데이터")
