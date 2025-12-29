# 에러 처리 (Error Handling)

## 📌 문서 목적

시스템 안정성을 위한 에러 처리 전략, 재시도 로직, 로깅, 모니터링 방법을 정의합니다.

---

## 🎯 에러 분류

### 1. 데이터 수집 에러

| 에러 타입 | 원인 | 처리 방법 |
|---------|------|---------|
| **NetworkError** | API 서버 다운, 네트워크 장애 | 3회 재시도 (2초 간격) |
| **TimeoutError** | 응답 시간 초과 | 타임아웃 증가 후 재시도 |
| **RateLimitError** | API 호출 제한 초과 | 지수 백오프 대기 |
| **DataNotFoundError** | 데이터 없음 (휴장일, 신규 상장) | 스킵, 로그 기록 |
| **InvalidDataError** | 잘못된 형식의 데이터 | 검증 실패 로그, 알림 |

### 2. LLM 에러

| 에러 타입 | 원인 | 처리 방법 |
|---------|------|---------|
| **APIKeyError** | 잘못된 API 키 | 즉시 중단, 알림 |
| **QuotaExceededError** | API 할당량 초과 | 대기 후 재시도 |
| **ModelOverloadError** | 모델 과부하 | 지수 백오프 재시도 |
| **InvalidPromptError** | 프롬프트 형식 오류 | 프롬프트 수정 필요 |
| **ResponseParsingError** | 응답 파싱 실패 | 재시도 또는 기본값 반환 |

### 3. 데이터베이스 에러

| 에러 타입 | 원인 | 처리 방법 |
|---------|------|---------|
| **ConnectionError** | DB 연결 실패 | 재연결 시도 (5회) |
| **IntegrityError** | 중복 키, 제약조건 위반 | 로그 기록, 스킵 |
| **TransactionError** | 트랜잭션 실패 | 롤백 후 재시도 |
| **DiskFullError** | 디스크 용량 부족 | 알림, 정리 작업 |

### 4. Redis 캐시 에러

| 에러 타입 | 원인 | 처리 방법 |
|---------|------|---------|
| **ConnectionError** | Redis 서버 다운 | Fallback to DB |
| **MemoryError** | 메모리 부족 | LRU 정책으로 자동 삭제 |
| **KeyNotFoundError** | 캐시 미스 | DB 조회 후 캐싱 |

---

## 🔄 재시도 로직

### 1. 기본 재시도 데코레이터

```python
# backend/app/utils/retry.py

from functools import wraps
import time
import asyncio
from typing import Callable, Type
import logging

logger = logging.getLogger(__name__)

def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    재시도 데코레이터

    Args:
        max_attempts: 최대 시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 지수 백오프 배수 (1.0 = 고정, 2.0 = 지수)
        exceptions: 재시도할 예외 타입 튜플

    Example:
        @retry(max_attempts=3, delay=2, backoff=2.0)
        def fetch_data():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1

                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            exc_info=True
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay}s..."
                    )

                    time.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator
```

### 2. 비동기 재시도

```python
def async_retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    비동기 함수용 재시도 데코레이터
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1

                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                            exc_info=True
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay}s..."
                    )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

        return wrapper
    return decorator
```

### 3. tenacity 라이브러리 사용

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
async def fetch_market_data(date: str):
    """
    시장 데이터 수집 (재시도 포함)
    """
    # pykrx 호출
    pass
```

---

## 📝 로깅 전략

### 1. 로깅 설정

```python
# backend/app/core/logging_config.py

import logging
import logging.handlers
from pathlib import Path

def setup_logging(
    log_level: str = "INFO",
    log_file: str = "./data/logs/app.log"
):
    """
    로깅 설정

    로그 레벨:
    - DEBUG: 상세한 디버깅 정보
    - INFO: 일반 정보 (배치 실행, API 호출)
    - WARNING: 경고 (재시도, 캐시 미스)
    - ERROR: 에러 (API 실패, DB 오류)
    - CRITICAL: 치명적 오류 (서비스 중단)
    """
    # 로그 디렉토리 생성
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 루트 로거 설정
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # 포맷터
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 파일 핸들러 (자동 로테이션)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
```

### 2. 로깅 예시

```python
import logging

logger = logging.getLogger(__name__)

# 정보 로그
logger.info("Morning triggers started")

# 경고 로그
logger.warning(f"Cache miss for ticker {ticker}")

# 에러 로그 (스택 트레이스 포함)
try:
    result = fetch_data()
except Exception as e:
    logger.error(f"Data fetch failed: {e}", exc_info=True)

# 디버그 로그
logger.debug(f"Composite score calculated: {score}")
```

---

## 🚨 예외 처리 패턴

### 1. 커스텀 예외 정의

```python
# backend/app/core/exceptions.py

class MintException(Exception):
    """
    프로젝트 기본 예외
    """
    pass

class DataCollectionError(MintException):
    """
    데이터 수집 실패
    """
    pass

class LLMServiceError(MintException):
    """
    LLM 서비스 오류
    """
    pass

class CacheError(MintException):
    """
    캐시 오류
    """
    pass

class AnalysisError(MintException):
    """
    분석 실패
    """
    pass
```

### 2. FastAPI 예외 핸들러

```python
# backend/app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import MintException
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

@app.exception_handler(MintException)
async def skku_exception_handler(request: Request, exc: MintException):
    """
    프로젝트 커스텀 예외 핸들러
    """
    logger.error(f"Custom exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    전역 예외 핸들러
    """
    logger.critical(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "path": str(request.url)
        }
    )
```

### 3. 서비스 레이어 에러 처리

```python
# backend/app/services/trigger_service.py

async def run_morning_triggers(date: datetime) -> List[Dict]:
    """
    오전 트리거 실행 (에러 처리 포함)
    """
    try:
        # 데이터 수집
        try:
            current_data = await data_service.get_market_snapshot(date)
        except ConnectionError as e:
            logger.error(f"Failed to fetch market data: {e}")
            raise DataCollectionError(f"Market data unavailable for {date}")

        # 트리거 실행
        results = []

        for trigger_func in [morning_volume_surge, morning_gap_up, morning_fund_inflow]:
            try:
                trigger_results = await trigger_func(current_data)
                results.extend(trigger_results)
            except Exception as e:
                logger.error(f"Trigger {trigger_func.__name__} failed: {e}", exc_info=True)
                # 일부 트리거 실패해도 계속 진행
                continue

        if not results:
            logger.warning("No triggers produced results")

        return results

    except DataCollectionError:
        # 상위로 전파
        raise
    except Exception as e:
        logger.critical(f"Unexpected error in run_morning_triggers: {e}", exc_info=True)
        raise MintException("Morning triggers failed")
```

---

## 📊 모니터링 및 알림

### 1. 헬스 체크 엔드포인트

```python
# backend/app/api/v1/health.py

from fastapi import APIRouter
from app.services.data_service import DataService
from app.core.cache import redis_client
from app.db.session import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    시스템 헬스 체크

    Returns:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "services": {
                "database": "ok" | "error",
                "redis": "ok" | "error",
                "pykrx": "ok" | "error"
            }
        }
    """
    services = {}

    # 데이터베이스 체크
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        services['database'] = 'ok'
    except Exception as e:
        services['database'] = 'error'
        logger.error(f"Database health check failed: {e}")

    # Redis 체크
    try:
        redis_client.ping()
        services['redis'] = 'ok'
    except Exception as e:
        services['redis'] = 'error'
        logger.error(f"Redis health check failed: {e}")

    # pykrx 체크
    try:
        from pykrx import stock
        # 간단한 테스트 호출
        services['pykrx'] = 'ok'
    except Exception as e:
        services['pykrx'] = 'error'
        logger.error(f"pykrx health check failed: {e}")

    # 전체 상태 판단
    if all(v == 'ok' for v in services.values()):
        status = 'healthy'
    elif any(v == 'ok' for v in services.values()):
        status = 'degraded'
    else:
        status = 'unhealthy'

    return {
        "status": status,
        "services": services
    }
```

### 2. 에러 알림 (이메일/Slack)

```python
# backend/app/utils/notifications.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
import logging

logger = logging.getLogger(__name__)

async def send_error_notification(
    error_type: str,
    error_message: str,
    traceback: str = None
):
    """
    에러 알림 발송

    Args:
        error_type: 에러 유형 (예: "DataCollectionError")
        error_message: 에러 메시지
        traceback: 스택 트레이스 (선택)
    """
    # Slack 웹훅 (선택)
    slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if slack_webhook_url:
        try:
            payload = {
                "text": f"⚠️ MINT 에러 발생",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*에러 타입*: {error_type}\n*메시지*: {error_message}"
                        }
                    }
                ]
            }

            if traceback:
                payload["blocks"].append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{traceback[:500]}```"  # 처음 500자만
                    }
                })

            async with httpx.AsyncClient() as client:
                response = await client.post(slack_webhook_url, json=payload)

                if response.status_code != 200:
                    logger.error(f"Slack notification failed: {response.text}")

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
```

---

## 🔧 Fallback 전략

### 1. Redis 캐시 Fallback

```python
async def get_analysis(ticker: str) -> dict:
    """
    기업 분석 조회 (Redis 실패 시 DB로 Fallback)
    """
    # 1차: Redis 캐시 시도
    try:
        cached = await redis_client.get(f"analysis:{ticker}")
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Redis cache failed, falling back to DB: {e}")

    # 2차: DB 조회
    try:
        result = await db.query("SELECT * FROM analysis WHERE ticker = ?", (ticker,))
        if result:
            return result
    except Exception as e:
        logger.error(f"DB query failed: {e}")

    # 3차: LLM 생성
    return await llm_service.analyze_company(ticker)
```

### 2. 데이터 소스 Fallback

```python
async def get_stock_price(ticker: str) -> float:
    """
    종목 가격 조회 (여러 소스 시도)
    """
    # 1차: pykrx
    try:
        price = await fetch_price_from_pykrx(ticker)
        if price:
            return price
    except Exception as e:
        logger.warning(f"pykrx failed: {e}")

    # 2차: MCP 서버 (kospi_kosdaq)
    try:
        price = await fetch_price_from_mcp(ticker)
        if price:
            return price
    except Exception as e:
        logger.warning(f"MCP server failed: {e}")

    # 3차: 캐시된 과거 데이터
    try:
        price = await get_cached_price(ticker)
        if price:
            logger.warning(f"Using cached price for {ticker}")
            return price
    except Exception as e:
        logger.error(f"All price sources failed for {ticker}")

    raise DataCollectionError(f"Unable to fetch price for {ticker}")
```

---

## 📈 메트릭 수집

```python
# backend/app/utils/metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

# 카운터
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

llm_calls_total = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['model', 'status']
)

data_collection_errors = Counter(
    'data_collection_errors_total',
    'Total data collection errors',
    ['source']
)

# 히스토그램
api_response_time = Histogram(
    'api_response_time_seconds',
    'API response time',
    ['endpoint']
)

llm_generation_time = Histogram(
    'llm_generation_time_seconds',
    'LLM generation time',
    ['prompt_type']
)

# 게이지
active_triggers = Gauge(
    'active_triggers',
    'Number of active triggers',
    ['session']
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate',
    ['cache_type']
)
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
