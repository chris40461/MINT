"""
API 의존성 주입 (Dependency Injection)

FastAPI의 Depends를 사용하여 서비스 레이어를 주입합니다.
"""

from typing import Generator
from functools import lru_cache

from app.services import (
    DataService,
    TriggerService,
    AnalysisService,
    LLMCompanyAnalysis,
    LLMReport,
)


# 싱글톤 패턴으로 서비스 인스턴스 생성
@lru_cache()
def get_data_service() -> DataService:
    """
    DataService 의존성 주입

    Returns:
        DataService: 데이터 수집 서비스 인스턴스
    """
    return DataService()


@lru_cache()
def get_llm_company_analysis() -> LLMCompanyAnalysis:
    """
    LLMCompanyAnalysis 의존성 주입

    Returns:
        LLMCompanyAnalysis: LLM 기업 분석 서비스 인스턴스
    """
    return LLMCompanyAnalysis()


@lru_cache()
def get_llm_report() -> LLMReport:
    """
    LLMReport 의존성 주입

    Returns:
        LLMReport: LLM 리포트 생성 서비스 인스턴스
    """
    return LLMReport()


@lru_cache()
def get_trigger_service() -> TriggerService:
    """
    TriggerService 의존성 주입

    Returns:
        TriggerService: 트리거 감지 서비스 인스턴스
    """
    data_service = get_data_service()
    return TriggerService(data_service=data_service)


@lru_cache()
def get_analysis_service() -> AnalysisService:
    """
    AnalysisService 의존성 주입

    Returns:
        AnalysisService: 분석 오케스트레이션 서비스 인스턴스
    """
    data_service = get_data_service()
    llm_company_analysis = get_llm_company_analysis()
    return AnalysisService(
        data_service=data_service,
        llm_service=llm_company_analysis
    )


# Alias for backward compatibility and scheduler
def get_report_service() -> LLMReport:
    """
    ReportService 의존성 주입 (LLMReport와 동일)

    Returns:
        LLMReport: 리포트 생성 서비스 인스턴스
    """
    return get_llm_report()
