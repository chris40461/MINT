"""
Configuration settings for Price Poller Service

환경 변수를 통해 설정을 관리합니다.
"""

from pydantic_settings import BaseSettings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings"""

    # Environment
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:////app/data/skku_insight.db"

    # KIS API
    KIS_APP_KEY: str
    KIS_APP_SECRET: str
    KIS_IS_MOCK: bool = True

    @property
    def KIS_BASE_URL(self) -> str:
        """KIS API Base URL (Mock or Real)"""
        if self.KIS_IS_MOCK:
            return "https://openapivts.koreainvestment.com:29443"  # Mock trading
        else:
            return "https://openapi.koreainvestment.com:9443"  # Real trading

    # Polling settings
    POLLING_INTERVAL: float = 0.5  # 초 (초당 2건 제한 준수)
    BATCH_SIZE: int = 30  # 멀티종목 시세조회 최대 30개
    CYCLE_COMPLETE_DELAY: float = 0.5  # 사이클 완료 후 대기 시간

    # Data staleness
    REALTIME_PRICE_STALENESS_THRESHOLD: int = 300  # 5분 (초)

    # Market hours (KST)
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 0
    MARKET_CLOSE_HOUR: int = 15
    MARKET_CLOSE_MINUTE: int = 30

    class Config:
        env_file = str(ENV_FILE)
        case_sensitive = True
        extra = "ignore"  # .env에 다른 서비스 설정 무시


settings = Settings()
