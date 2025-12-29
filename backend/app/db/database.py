# 참고: docs/database/02-cache-strategy.md

"""
데이터베이스 연결 및 세션 관리
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import os
from pathlib import Path

from app.db.models import Base

# DB 파일 경로 (프로젝트 루트/data/db.sqlite)
DB_DIR = Path(__file__).parent.parent.parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "mint.db"

# SQLite 연결 문자열
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Engine 생성
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite용
    echo=False  # SQL 로그 출력 (개발 시 True)
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database initialized at {DB_PATH}")


@contextmanager
def get_db() -> Session:
    """
    데이터베이스 세션 컨텍스트 매니저

    Example:
        >>> with get_db() as db:
        ...     financial_data = db.query(FinancialData).filter_by(ticker='005930').first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    단일 세션 반환 (FastAPI dependency용)

    Example:
        >>> db = get_db_session()
        >>> try:
        ...     financial_data = db.query(FinancialData).all()
        ... finally:
        ...     db.close()
    """
    return SessionLocal()
