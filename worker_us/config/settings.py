"""
Configuration settings for worker_us
환경 변수, 상수, OpenBB provider 설정 등
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# ==================================================================================
# 기본 경로 설정
# ==================================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR / 'logs'
CACHE_DIR = DATA_DIR / 'cache'

# 디렉토리 생성
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ==================================================================================
# 데이터베이스 설정
# ==================================================================================
DB_PATH = str(DATA_DIR / 'nasdaq.db')
DB_URL = f'sqlite:///{DB_PATH}'

# ==================================================================================
# API Keys
# ==================================================================================
FRED_API_KEY = os.getenv('FRED_API_KEY', '')

# OpenBB API 키 설정 (필요한 경우)
# OPENBB_API_KEY = os.getenv('OPENBB_API_KEY', '')

# ==================================================================================
# 데이터 수집 설정
# ==================================================================================

# 날짜 범위
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=365)  # 1년치 데이터

# NASDAQ FTP 설정
NASDAQ_FTP_URL = "ftp://ftp.nasdaqtrader.com/symboldirectory/nasdaqlisted.txt"

# 급등/급락 임계값
PRICE_CHANGE_THRESHOLD = 0.05  # 5% 이상 변동 시 fundamentals 즉시 업데이트

# ==================================================================================
# Rate Limiting 설정
# ==================================================================================

# API 호출 간격 (초)
RATE_LIMIT_SLEEP = 0.2  # 기본 0.2초
RATE_LIMIT_SLEEP_FRED = 0.3  # FRED는 조금 더 여유있게
RATE_LIMIT_SLEEP_OPTIONS = 0.5  # CBOE는 더 여유있게

# Retry 설정
MAX_RETRIES = 5  # 최대 재시도 횟수
BASE_DELAY = 2  # Exponential backoff 시작값 (초)
MAX_DELAY = 180  # 최대 대기 시간 (초)

# ==================================================================================
# 수집 제한
# ==================================================================================

# 종목별 수집 제한
NEWS_LIMIT_PER_STOCK = 20  # 종목당 최대 뉴스 개수
FINANCIAL_YEARS_LIMIT = 5  # 재무제표 최근 5년

# 배치 처리
BATCH_SIZE = 100  # 배치 처리 시 묶음 크기
PROGRESS_REPORT_INTERVAL = 50  # 진행 상황 출력 간격

# ==================================================================================
# 데이터 보관 정책 (Retention)
# ==================================================================================

# Rolling Window (일 단위)
NEWS_RETENTION_DAYS = 30  # 뉴스 30일 보관
FUNDAMENTALS_RETENTION_DAYS = 90  # Fundamentals 90일 보관
OPTIONS_SUMMARY_RETENTION_DAYS = 90  # Options Summary 90일 보관
FRED_RETENTION_YEARS = 5  # FRED 5년 보관

# ==================================================================================
# 스케줄 설정 (Cron 표현식 또는 시간)
# ==================================================================================

# 매일 실행
MORNING_UPDATE_HOUR = 8  # 08:00 (장 시작 전)
MORNING_UPDATE_MINUTE = 0

AFTERNOON_UPDATE_HOUR = 16  # 16:00 (장 마감 후)
AFTERNOON_UPDATE_MINUTE = 0

# 주간 실행
WEEKLY_UPDATE_DAY = 'sun'  # 일요일
WEEKLY_UPDATE_HOUR = 0  # 00:00
WEEKLY_UPDATE_MINUTE = 0

# 분기 실행 (실적 시즌)
QUARTERLY_EARNINGS_SEASONS = {
    'Q1': {'month': 4, 'day': 15},   # 4월 15일
    'Q2': {'month': 7, 'day': 15},   # 7월 15일
    'Q3': {'month': 10, 'day': 15},  # 10월 15일
    'Q4': {'month': 1, 'day': 15}    # 1월 15일 (다음해)
}

# ==================================================================================
# 로깅 설정
# ==================================================================================

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# 로그 파일 경로
LOG_FILE_CRITICAL = LOG_DIR / 'critical' / 'critical.log'
LOG_FILE_ERROR = LOG_DIR / 'error' / 'error.log'
LOG_FILE_WARNING = LOG_DIR / 'warning' / 'warning.log'
LOG_FILE_INFO = LOG_DIR / 'info' / 'info.log'

# 로그 파일 최대 크기 및 백업 개수
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5  # 최대 5개 백업 파일

# ==================================================================================
# OpenBB Provider 설정
# ==================================================================================

OPENBB_PROVIDERS = {
    'yfinance': {
        'description': 'Yahoo Finance - OHLCV, 재무제표, 뉴스, 프로필',
        'requires_api_key': False,
        'rate_limit': RATE_LIMIT_SLEEP
    },
    'cboe': {
        'description': 'CBOE - 옵션 체인',
        'requires_api_key': False,
        'rate_limit': RATE_LIMIT_SLEEP_OPTIONS
    },
    'fred': {
        'description': 'FRED - 거시경제 지표',
        'requires_api_key': True,
        'api_key': FRED_API_KEY,
        'rate_limit': RATE_LIMIT_SLEEP_FRED
    },
    'finviz': {
        'description': 'Finviz - 펀더멘탈 지표',
        'requires_api_key': False,
        'rate_limit': RATE_LIMIT_SLEEP
    }
}

# ==================================================================================
# 유효성 검사
# ==================================================================================

def validate_settings():
    """설정값 검증"""
    errors = []

    # FRED API 키 확인
    if not FRED_API_KEY:
        errors.append("FRED_API_KEY is not set in .env file")

    # 디렉토리 존재 확인
    if not DATA_DIR.exists():
        errors.append(f"Data directory does not exist: {DATA_DIR}")

    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    return True


# ==================================================================================
# 설정 요약 출력
# ==================================================================================

def print_settings():
    """현재 설정 출력"""
    print("=" * 80)
    print("  WORKER_US CONFIGURATION")
    print("=" * 80)
    print(f"Database: {DB_PATH}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Log Directory: {LOG_DIR}")
    print(f"\nDate Range: {START_DATE.date()} ~ {END_DATE.date()}")
    print(f"FRED API Key: {'✓ Set' if FRED_API_KEY else '✗ Not Set'}")
    print(f"\nRate Limits:")
    print(f"  - Default: {RATE_LIMIT_SLEEP}s")
    print(f"  - FRED: {RATE_LIMIT_SLEEP_FRED}s")
    print(f"  - Options: {RATE_LIMIT_SLEEP_OPTIONS}s")
    print(f"\nRetry Settings:")
    print(f"  - Max Retries: {MAX_RETRIES}")
    print(f"  - Base Delay: {BASE_DELAY}s")
    print(f"  - Max Delay: {MAX_DELAY}s")
    print(f"\nSchedule:")
    print(f"  - Morning Update: {MORNING_UPDATE_HOUR:02d}:{MORNING_UPDATE_MINUTE:02d}")
    print(f"  - Afternoon Update: {AFTERNOON_UPDATE_HOUR:02d}:{AFTERNOON_UPDATE_MINUTE:02d}")
    print(f"  - Weekly Update: {WEEKLY_UPDATE_DAY} {WEEKLY_UPDATE_HOUR:02d}:{WEEKLY_UPDATE_MINUTE:02d}")
    print("=" * 80)


if __name__ == "__main__":
    validate_settings()
    print_settings()
