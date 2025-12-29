"""
Retry logic with exponential backoff
API 호출 실패 시 재시도 로직
"""

import time
import random
from functools import wraps
from typing import Callable, Any, Optional, Tuple, Type
from utils.logger import get_logger

from config.settings import MAX_RETRIES, BASE_DELAY, MAX_DELAY

logger = get_logger(__name__)


def retry_with_backoff(
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    jitter: bool = True
):
    """
    Exponential backoff with jitter를 사용한 재시도 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        exceptions: 재시도할 예외 타입 튜플
        jitter: 랜덤 jitter 추가 여부

    Returns:
        함수 데코레이터

    Example:
        @retry_with_backoff(max_retries=3, base_delay=1)
        def api_call():
            # API 호출 코드
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    if attempt == max_retries - 1:
                        # 마지막 시도 실패 시
                        logger.error(
                            f"{func.__name__} failed after {max_retries} attempts: {str(e)}"
                        )
                        raise

                    # Exponential backoff 계산: 2^attempt * base_delay
                    wait_time = min(base_delay * (2 ** attempt), max_delay)

                    # Jitter 추가 (0~3초 랜덤)
                    if jitter:
                        wait_time += random.uniform(0, 3)

                    # 특정 에러 키워드 감지 시 대기 시간 조정
                    error_str = str(e).lower()
                    if 'rate limit' in error_str or '429' in error_str:
                        wait_time *= 2
                        logger.warning(f"Rate limit detected, waiting {wait_time:.1f}s")
                    elif 'overloaded' in error_str or '503' in error_str:
                        wait_time *= 1.5
                        logger.warning(f"Server overload detected, waiting {wait_time:.1f}s")

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}"
                    )
                    logger.info(f"Retrying in {wait_time:.1f}s...")

                    time.sleep(wait_time)

            return None  # Should not reach here

        return wrapper
    return decorator


class RetryableError(Exception):
    """재시도 가능한 에러"""
    pass


class NonRetryableError(Exception):
    """재시도 불가능한 에러"""
    pass


def execute_with_retry(
    func: Callable,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    *args,
    **kwargs
) -> Optional[Any]:
    """
    함수를 재시도 로직과 함께 실행

    Args:
        func: 실행할 함수
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간
        *args: func에 전달할 positional arguments
        **kwargs: func에 전달할 keyword arguments

    Returns:
        함수 실행 결과 또는 None (실패 시)

    Example:
        result = execute_with_retry(api_call, max_retries=3, arg1=value1)
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except NonRetryableError as e:
            # 재시도 불가능한 에러는 즉시 중단
            logger.error(f"Non-retryable error: {str(e)}")
            raise

        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"{func.__name__} failed after {max_retries} attempts: {str(e)}"
                )
                return None

            wait_time = min(base_delay * (2 ** attempt), MAX_DELAY)
            wait_time += random.uniform(0, 3)

            logger.warning(
                f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}"
            )
            logger.info(f"Retrying in {wait_time:.1f}s...")

            time.sleep(wait_time)

    return None


# 테스트용
if __name__ == "__main__":
    # 테스트 1: 데코레이터 사용
    @retry_with_backoff(max_retries=3, base_delay=1)
    def failing_function(should_fail: bool = True):
        """테스트용 함수"""
        if should_fail:
            raise ValueError("Simulated error")
        return "Success!"

    # 테스트 2: execute_with_retry 사용
    def another_failing_function():
        raise ConnectionError("Connection failed")

    print("Test 1: Decorator (will fail)")
    try:
        result = failing_function(should_fail=True)
    except ValueError:
        print("  → Failed as expected after retries")

    print("\nTest 2: Decorator (will succeed)")
    result = failing_function(should_fail=False)
    print(f"  → Result: {result}")

    print("\nTest 3: execute_with_retry (will fail)")
    result = execute_with_retry(another_failing_function, max_retries=2, base_delay=0.5)
    print(f"  → Result: {result}")
