"""
Database connection management
DB 연결 및 세션 관리
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from config.settings import DB_URL, DB_PATH
from utils.logger import get_logger

logger = get_logger(__name__)


# ==================================================================================
# Engine 생성 (Singleton)
# ==================================================================================

_engine = None
_SessionLocal = None


def get_engine():
    """
    SQLAlchemy Engine 반환 (Singleton)

    Returns:
        sqlalchemy.engine.Engine
    """
    global _engine

    if _engine is None:
        logger.info(f"Creating database engine: {DB_PATH}")

        _engine = create_engine(
            DB_URL,
            echo=False,  # SQL 쿼리 로깅 (디버깅 시 True)
            pool_pre_ping=True,  # 연결 상태 자동 체크
            connect_args={'check_same_thread': False}  # SQLite thread-safe
        )

        # SQLite Foreign Key 제약조건 활성화
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info("Database engine created successfully")

    return _engine


def get_session_local():
    """
    SessionLocal 클래스 반환 (Singleton)

    Returns:
        sqlalchemy.orm.sessionmaker
    """
    global _SessionLocal

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        logger.debug("SessionLocal created")

    return _SessionLocal


# ==================================================================================
# Session 관리
# ==================================================================================

def get_session() -> Session:
    """
    새로운 DB 세션 반환

    Returns:
        sqlalchemy.orm.Session

    Example:
        session = get_session()
        try:
            # DB 작업
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    """
    SessionLocal = get_session_local()
    return SessionLocal()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager로 DB 세션 관리

    Yields:
        sqlalchemy.orm.Session

    Example:
        with get_db_session() as session:
            # DB 작업
            session.add(obj)
            session.commit()
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {str(e)}")
        raise
    finally:
        session.close()


# ==================================================================================
# Database 초기화
# ==================================================================================

def init_database():
    """
    데이터베이스 초기화 (테이블 생성)

    Note:
        models/schemas.py의 create_database() 함수 사용
    """
    from models.schemas import create_database

    logger.info("Initializing database...")
    engine = create_database(DB_PATH)
    logger.info("Database initialized successfully")

    return engine


def check_database_exists() -> bool:
    """
    데이터베이스 파일 존재 여부 확인

    Returns:
        bool: 존재하면 True, 없으면 False
    """
    from pathlib import Path

    db_file = Path(DB_PATH)
    exists = db_file.exists()

    if exists:
        logger.debug(f"Database exists: {DB_PATH}")
    else:
        logger.warning(f"Database does not exist: {DB_PATH}")

    return exists


def get_table_row_counts() -> dict:
    """
    각 테이블의 row 개수 조회

    Returns:
        dict: {table_name: row_count}
    """
    from sqlalchemy import text

    tables = [
        'stocks', 'fred_macro', 'price_daily', 'income_statement',
        'balance_sheet', 'cash_flow', 'fundamentals', 'news',
        'options_summary'
    ]

    counts = {}

    with get_db_session() as session:
        for table in tables:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            counts[table] = count

    return counts


# 테스트용
if __name__ == "__main__":
    print("Testing database connection...")

    # 1. Engine 테스트
    engine = get_engine()
    print(f"✓ Engine created: {engine}")

    # 2. Session 테스트
    with get_db_session() as session:
        print(f"✓ Session created: {session}")

    # 3. DB 존재 확인
    exists = check_database_exists()
    print(f"✓ Database exists: {exists}")

    if exists:
        # 4. 테이블 row count
        counts = get_table_row_counts()
        print("\n테이블별 Row Count:")
        for table, count in counts.items():
            print(f"  {table:20s}: {count:,} rows")
