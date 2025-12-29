# Backend_US Directory Structure Proposal

## 서버 아키텍처

### 1. **Backend API Server** (기존 backend/)
- 역할: Frontend와 직접 소통
- 기능: REST API 제공, 사용자 요청 처리
- 데이터: DB 읽기 (read-only)

### 2. **Backend Worker Server** (backend_us/)
- 역할: 데이터 수집, DB 업데이트, LLM 처리
- 기능: 스케줄 작업, ETL 파이프라인
- 데이터: DB 쓰기 (write)

---

## 제안: backend_us/ (Worker Server) 구조

ETL Best Practices + Airflow/Celery Worker 패턴 기반

```
backend_us/
├── jobs/                       # 스케줄 작업 정의 (Airflow DAGs 또는 APScheduler)
│   ├── __init__.py
│   ├── daily_jobs.py           # 매일 실행 (08:00, 16:00)
│   ├── weekly_jobs.py          # 주 1회 실행 (일요일 00:00)
│   ├── quarterly_jobs.py       # 분기 1회 실행 (실적 시즌)
│   └── adhoc_jobs.py           # 수동 실행 작업
│
├── collectors/                 # 데이터 수집 (Extract)
│   ├── __init__.py
│   ├── fred_collector.py       # FRED 거시경제 지표
│   ├── price_collector.py      # yfinance OHLCV
│   ├── financial_collector.py  # yfinance 재무제표
│   ├── fundamental_collector.py # Finviz 펀더멘탈
│   ├── news_collector.py       # yfinance 뉴스
│   ├── options_collector.py    # CBOE 옵션 요약
│   └── stock_collector.py      # NASDAQ FTP 종목 리스트
│
├── processors/                 # 데이터 변환 (Transform, 필요 시)
│   ├── __init__.py
│   ├── fred_processor.py       # CPI YoY 계산, Yield Spread 등
│   ├── options_processor.py    # PCR, IV 계산
│   └── deduplicator.py         # 뉴스 중복 제거 (STS)
│
├── loaders/                    # 데이터 적재 (Load)
│   ├── __init__.py
│   ├── db_loader.py            # SQLite/PostgreSQL 적재
│   └── batch_loader.py         # 대량 데이터 upsert
│
├── models/                     # DB 스키마 (SQLAlchemy ORM)
│   ├── __init__.py
│   ├── schemas.py              # database_schema.py 내용 이동
│   └── connection.py           # DB 연결 관리
│
├── utils/                      # 공통 유틸리티
│   ├── __init__.py
│   ├── retry.py                # Exponential backoff retry 로직
│   ├── rate_limiter.py         # API rate limiting
│   ├── logger.py               # 로깅 설정
│   └── validators.py           # 데이터 검증
│
├── config/                     # 설정 파일
│   ├── __init__.py
│   ├── settings.py             # 환경 변수, 상수
│   └── providers.py            # OpenBB provider 설정
│
├── logs/                       # 로그 파일 (severity별 분리)
│   ├── critical/
│   ├── error/
│   ├── warning/
│   └── info/
│
├── data/                       # 데이터 저장
│   ├── nasdaq.db               # SQLite 데이터베이스
│   └── cache/                  # 임시 캐시 (필요 시)
│
├── scripts/                    # 유틸리티 스크립트
│   ├── initial_setup.py        # 최초 DB 생성, 전체 수집
│   ├── retry_failed.py         # 실패한 종목 재시도
│   ├── check_db.py             # DB 통계 확인
│   └── cleanup.py              # 오래된 데이터 삭제
│
├── tests/                      # 테스트
│   ├── test_collectors/
│   ├── test_processors/
│   ├── test_loaders/
│   └── test_jobs/
│
├── docs/                       # 문서
│   ├── UPDATE_STRATEGY.md      # 업데이트 전략
│   ├── API_USAGE.md            # OpenBB API 사용법
│   └── DEPLOYMENT.md           # 배포 가이드
│
├── .env                        # 환경 변수 (FRED_API_KEY 등)
├── .gitignore
├── requirements.txt            # Python 의존성
├── scheduler.py                # 메인 스케줄러 (APScheduler 또는 Cron)
└── README.md
```

---

## 주요 변경 사항

### 기존 → 제안

| 기존 파일 | 제안 위치 | 비고 |
|----------|----------|------|
| `database_schema.py` | `models/schemas.py` | DB 스키마 |
| `batch_collect_nasdaq.py` | `scripts/initial_setup.py` | 최초 수집 스크립트 |
| `retry_failed_stocks.py` | `scripts/retry_failed.py` | 재시도 스크립트 |
| `check_db.py` | `scripts/check_db.py` | DB 확인 |
| (없음) | `jobs/daily_jobs.py` | 매일 업데이트 로직 |
| (없음) | `jobs/weekly_jobs.py` | 주간 업데이트 로직 |
| (없음) | `jobs/quarterly_jobs.py` | 분기 업데이트 로직 |
| (없음) | `collectors/*.py` | 수집 로직 분리 |
| (없음) | `scheduler.py` | 메인 스케줄러 |

---

## 스케줄러 선택

### Option 1: APScheduler (권장)
- 간단한 Python 스케줄러
- 별도 인프라 불필요
- Cron-like 스케줄링 지원
- 적합: 단일 워커 서버

```python
# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from jobs.daily_jobs import morning_update, afternoon_update
from jobs.weekly_jobs import weekly_stock_update

scheduler = BlockingScheduler()

# 매일 08:00
scheduler.add_job(morning_update, 'cron', hour=8, minute=0)

# 매일 16:00
scheduler.add_job(afternoon_update, 'cron', hour=16, minute=0)

# 주 1회 (일요일 00:00)
scheduler.add_job(weekly_stock_update, 'cron', day_of_week='sun', hour=0)

scheduler.start()
```

### Option 2: Celery + Redis
- 분산 작업 큐
- Worker 확장 가능
- 복잡한 설정 필요
- 적합: 다중 워커 환경

### Option 3: Cron (시스템)
- OS 레벨 스케줄러
- 가장 간단
- Python 코드 외부 관리
- 적합: 간단한 배포

```bash
# crontab -e
0 8 * * * cd /path/to/backend_us && python jobs/daily_jobs.py morning
0 16 * * * cd /path/to/backend_us && python jobs/daily_jobs.py afternoon
0 0 * * 0 cd /path/to/backend_us && python jobs/weekly_jobs.py
```

---

## 작업 흐름 예시

### Daily Morning Update (08:00)

```python
# jobs/daily_jobs.py

from collectors.fred_collector import FREDCollector
from collectors.news_collector import NewsCollector
from loaders.db_loader import DBLoader
from utils.logger import get_logger

logger = get_logger(__name__)

def morning_update():
    """매일 08:00 - 장 시작 전 업데이트"""
    logger.info("Starting morning update...")

    loader = DBLoader()

    # 1. FRED 거시경제 지표
    fred_collector = FREDCollector()
    fred_data = fred_collector.collect()
    loader.load_fred_macro(fred_data)

    # 2. 뉴스 수집
    news_collector = NewsCollector()
    news_data = news_collector.collect_all(limit=10)
    loader.load_news(news_data)

    logger.info("Morning update completed")


def afternoon_update():
    """매일 16:00 - 장 마감 후 업데이트"""
    logger.info("Starting afternoon update...")

    loader = DBLoader()

    # 1. 가격 데이터 (D-1)
    from collectors.price_collector import PriceCollector
    price_collector = PriceCollector()
    price_data = price_collector.collect_yesterday()
    loader.load_prices(price_data)

    # 2. 뉴스 재수집
    from collectors.news_collector import NewsCollector
    news_collector = NewsCollector()
    news_data = news_collector.collect_all(limit=10)
    loader.load_news(news_data)

    # 3. 옵션 요약 (전체 종목)
    from collectors.options_collector import OptionsCollector
    options_collector = OptionsCollector()
    options_summary = options_collector.collect_summary_all()
    loader.load_options_summary(options_summary)

    logger.info("Afternoon update completed")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'morning':
        morning_update()
    elif len(sys.argv) > 1 and sys.argv[1] == 'afternoon':
        afternoon_update()
    else:
        print("Usage: python daily_jobs.py [morning|afternoon]")
```

---

## 장점

### 1. **관심사의 분리 (Separation of Concerns)**
- Collectors: 데이터 수집만 담당
- Processors: 데이터 변환만 담당
- Loaders: DB 적재만 담당
- Jobs: 스케줄 및 오케스트레이션

### 2. **재사용성 (Reusability)**
```python
# 다른 job에서 collector 재사용
from collectors.news_collector import NewsCollector

news_collector = NewsCollector()
aapl_news = news_collector.collect_ticker('AAPL', limit=20)
```

### 3. **테스트 용이성 (Testability)**
```python
# tests/test_collectors/test_news_collector.py
from collectors.news_collector import NewsCollector

def test_news_collector():
    collector = NewsCollector()
    news = collector.collect_ticker('AAPL', limit=5)
    assert len(news) <= 5
    assert all('title' in item for item in news)
```

### 4. **확장성 (Scalability)**
- 새로운 데이터 소스 추가 시: `collectors/` 에 새 파일만 추가
- 새로운 스케줄 추가 시: `jobs/` 에 새 파일만 추가

### 5. **유지보수성 (Maintainability)**
- 각 모듈이 독립적
- 버그 발생 시 해당 모듈만 수정

---

## 다음 단계

1. **디렉토리 구조 생성**
2. **기존 코드 분리 및 이동**
   - `database_schema.py` → `models/schemas.py`
   - `batch_collect_nasdaq.py` 로직 → `collectors/*.py` 분리
3. **Jobs 작성**
   - `jobs/daily_jobs.py`
   - `jobs/weekly_jobs.py`
   - `jobs/quarterly_jobs.py`
4. **Scheduler 구현**
   - `scheduler.py` (APScheduler 사용)
5. **테스트 작성**
6. **문서화**

---

**작성일**: 2025-11-20
**참고**: ETL Best Practices, Airflow/Celery Worker Pattern
