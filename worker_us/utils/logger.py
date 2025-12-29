"""
Logging configuration for worker_us
Severity별로 분리된 로그 파일 생성
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.settings import (
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_FILE_CRITICAL,
    LOG_FILE_ERROR,
    LOG_FILE_WARNING,
    LOG_FILE_INFO,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    LOG_DIR
)


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    로거 설정

    Args:
        name: 로거 이름 (일반적으로 __name__ 사용)

    Returns:
        logging.Logger: 설정된 로거
    """
    logger = logging.getLogger(name)

    # 이미 핸들러가 설정되어 있으면 재설정하지 않음 (중복 방지)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper()))
    logger.propagate = False

    # 포매터
    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT
    )

    # 1. Console Handler (INFO 이상)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. CRITICAL 파일 핸들러
    if not LOG_FILE_CRITICAL.parent.exists():
        LOG_FILE_CRITICAL.parent.mkdir(parents=True, exist_ok=True)

    critical_handler = RotatingFileHandler(
        LOG_FILE_CRITICAL,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(formatter)
    logger.addHandler(critical_handler)

    # 3. ERROR 파일 핸들러
    if not LOG_FILE_ERROR.parent.exists():
        LOG_FILE_ERROR.parent.mkdir(parents=True, exist_ok=True)

    error_handler = RotatingFileHandler(
        LOG_FILE_ERROR,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # 4. WARNING 파일 핸들러
    if not LOG_FILE_WARNING.parent.exists():
        LOG_FILE_WARNING.parent.mkdir(parents=True, exist_ok=True)

    warning_handler = RotatingFileHandler(
        LOG_FILE_WARNING,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(formatter)
    logger.addHandler(warning_handler)

    # 5. INFO 파일 핸들러
    if not LOG_FILE_INFO.parent.exists():
        LOG_FILE_INFO.parent.mkdir(parents=True, exist_ok=True)

    info_handler = RotatingFileHandler(
        LOG_FILE_INFO,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    logger.addHandler(info_handler)

    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """
    로거 가져오기 (setup_logger의 alias)

    Args:
        name: 로거 이름

    Returns:
        logging.Logger: 설정된 로거
    """
    return setup_logger(name)


# 테스트용
if __name__ == "__main__":
    logger = get_logger(__name__)

    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

    print(f"\nLog files created:")
    print(f"  CRITICAL: {LOG_FILE_CRITICAL}")
    print(f"  ERROR: {LOG_FILE_ERROR}")
    print(f"  WARNING: {LOG_FILE_WARNING}")
    print(f"  INFO: {LOG_FILE_INFO}")
