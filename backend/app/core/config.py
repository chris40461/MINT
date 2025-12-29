# 참고: docs/backend/01-data-collection.md
# 참고: docs/backend/05-llm-service.md

"""
환경 설정 관리

Pydantic Settings를 사용하여 .env 파일에서 환경 변수를 로드합니다.
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

# 프로젝트 루트 디렉토리 경로 (SKKU-insight/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 기본 설정
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./data/logs/app.log"

    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./skku_insight.db"

    # API Keys
    GEMINI_API_KEY: str = ""
    DART_API_KEY: Optional[str] = None
    KIS_APP_KEY: Optional[str] = None
    KIS_APP_SECRET: Optional[str] = None

    # LLM 설정
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MAX_TOKENS: int = 4000
    GEMINI_TEMPERATURE: float = 0.3

    # 스케줄러
    SCHEDULER_ENABLED: bool = True
    MORNING_TRIGGER_TIME: str = "09:10"
    AFTERNOON_TRIGGER_TIME: str = "15:30"
    MORNING_REPORT_TIME: str = "08:30"
    AFTERNOON_REPORT_TIME: str = "15:40"

    # 필터링 임계값
    MIN_TRADING_VALUE: int = 500_000_000      # 5억원
    MIN_MARKET_CAP: int = 50_000_000_000      # 500억원
    VOLUME_SURGE_THRESHOLD: float = 0.30      # 30%
    GAP_UP_THRESHOLD: float = 0.01            # 1%
    INTRADAY_RISE_THRESHOLD: float = 0.03     # 3%

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # 시크릿
    SECRET_KEY: str = "your-secret-key-change-in-production"

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True
        extra = "ignore"  


# 전역 설정 인스턴스
settings = Settings()
