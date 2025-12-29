# 통합 테스트 (Integration Tests)

## 📌 문서 목적

API 엔드투엔드 테스트, 배치 작업 테스트, 캐싱 테스트 등 시스템 통합 테스트 전략을 정의합니다.

---

## 🎯 통합 테스트 범위

### 1. API 엔드투엔드 테스트

- 클라이언트 요청 → API → 데이터 수집 → 응답 전체 흐름
- 실제 DB, Redis 사용 (테스트용 인스턴스)
- HTTP 상태 코드, 응답 형식 검증

### 2. 배치 작업 테스트

- 스케줄러 작업 전체 플로우
- 오전/오후 트리거 생성
- 장 시작/마감 리포트 생성

### 3. 캐싱 테스트

- Redis 캐시 저장/조회
- TTL 만료 확인
- 캐시 무효화 검증

---

## 🌐 API 엔드투엔드 테스트

### 1. 테스트 환경 설정

```python
# backend/tests/integration/conftest.py

import pytest
from fastapi.testclient import TestClient
from app.main import app
import redis
import os

@pytest.fixture(scope="session")
def test_redis():
    """테스트용 Redis 연결"""
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=1,  # 테스트용 DB
        decode_responses=True
    )

    yield r

    # 테스트 후 정리
    r.flushdb()
    r.close()

@pytest.fixture(scope="session")
def test_db():
    """테스트용 PostgreSQL 연결"""
    from sqlalchemy import create_engine
    from app.db.base import Base

    DATABASE_URL = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://test:test@localhost/skku_insight_test"
    )

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db, test_redis):
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)
```

---

### 2. 급등주 API 테스트

```python
# backend/tests/integration/test_triggers_api.py

import pytest
from datetime import datetime

@pytest.mark.integration
class TestTriggersAPI:
    """급등주 API 통합 테스트"""

    def test_get_triggers_morning(self, client):
        """오전 급등주 목록 조회"""
        response = client.get(
            "/api/v1/triggers",
            params={
                "session": "morning",
                "date": "2025-11-06"
            }
        )

        # 상태 코드 확인
        assert response.status_code == 200

        # 응답 형식 확인
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "triggers" in data["data"]

        # 데이터 구조 확인
        if len(data["data"]["triggers"]) > 0:
            trigger = data["data"]["triggers"][0]
            assert "ticker" in trigger
            assert "name" in trigger
            assert "currentPrice" in trigger
            assert "changeRate" in trigger
            assert "triggerType" in trigger
            assert "compositeScore" in trigger

    def test_get_triggers_filter_by_type(self, client):
        """트리거 타입 필터링"""
        response = client.get(
            "/api/v1/triggers",
            params={
                "session": "morning",
                "type": "volume_surge",
                "date": "2025-11-06"
            }
        )

        assert response.status_code == 200

        data = response.json()
        triggers = data["data"]["triggers"]

        # 모든 트리거가 volume_surge 타입인지 확인
        for trigger in triggers:
            assert trigger["triggerType"] == "volume_surge"

    def test_get_triggers_invalid_session(self, client):
        """잘못된 세션 파라미터"""
        response = client.get(
            "/api/v1/triggers",
            params={
                "session": "invalid",
                "date": "2025-11-06"
            }
        )

        assert response.status_code == 400
        assert "error" in response.json()

    def test_get_triggers_no_data(self, client):
        """데이터 없는 날짜"""
        response = client.get(
            "/api/v1/triggers",
            params={
                "session": "morning",
                "date": "2000-01-01"  # 오래된 날짜
            }
        )

        assert response.status_code == 200

        data = response.json()
        assert len(data["data"]["triggers"]) == 0
```

---

### 3. 기업 분석 API 테스트

```python
# backend/tests/integration/test_analysis_api.py

@pytest.mark.integration
class TestAnalysisAPI:
    """기업 분석 API 통합 테스트"""

    @pytest.mark.asyncio
    async def test_get_analysis_cached(self, client, test_redis):
        """분석 조회 (캐싱)"""
        ticker = "005930"

        # 첫 번째 요청 (LLM 호출)
        response1 = client.get(f"/api/v1/analysis/{ticker}")

        assert response1.status_code == 200

        data1 = response1.json()
        assert data1["data"]["ticker"] == ticker
        assert "summary" in data1["data"]
        assert "opinion" in data1["data"]

        # Redis 캐시 확인
        cache_key = f"analysis:{ticker}:{datetime.now().date().isoformat()}"
        cached = test_redis.get(cache_key)
        assert cached is not None

        # 두 번째 요청 (캐시 반환)
        response2 = client.get(f"/api/v1/analysis/{ticker}")

        assert response2.status_code == 200

        # 동일한 데이터 반환
        assert response1.json() == response2.json()

    def test_get_analysis_invalid_ticker(self, client):
        """잘못된 종목 코드"""
        response = client.get("/api/v1/analysis/INVALID")

        assert response.status_code == 404
        assert "error" in response.json()

    @pytest.mark.asyncio
    async def test_refresh_analysis(self, client, test_redis):
        """강제 재분석"""
        ticker = "005930"

        # 기존 분석 조회
        response1 = client.get(f"/api/v1/analysis/{ticker}")
        assert response1.status_code == 200

        # 강제 재분석
        response2 = client.post(f"/api/v1/analysis/{ticker}/refresh")

        assert response2.status_code == 200

        # 캐시 무효화 확인
        cache_key = f"analysis:{ticker}:{datetime.now().date().isoformat()}"
        cached = test_redis.get(cache_key)
        assert cached is None  # 캐시 삭제됨
```

---

### 4. 리포트 API 테스트

```python
# backend/tests/integration/test_reports_api.py

@pytest.mark.integration
class TestReportsAPI:
    """장 리포트 API 통합 테스트"""

    def test_get_morning_report(self, client):
        """장 시작 리포트 조회"""
        response = client.get(
            "/api/v1/reports/morning",
            params={"date": "2025-11-06"}
        )

        assert response.status_code == 200

        data = response.json()
        report = data["data"]

        # 필수 필드 확인
        assert "reportType" in report
        assert report["reportType"] == "morning"
        assert "marketForecast" in report
        assert "topStocks" in report
        assert "sectorAnalysis" in report
        assert "investmentStrategy" in report

    def test_get_afternoon_report(self, client):
        """장 마감 리포트 조회"""
        response = client.get(
            "/api/v1/reports/afternoon",
            params={"date": "2025-11-06"}
        )

        assert response.status_code == 200

        data = response.json()
        report = data["data"]

        assert report["reportType"] == "afternoon"
        assert "marketSummary" in report
        assert "surgeStocks" in report
        assert "tomorrowStrategy" in report

    def test_report_caching(self, client, test_redis):
        """리포트 캐싱 확인"""
        response = client.get(
            "/api/v1/reports/morning",
            params={"date": "2025-11-06"}
        )

        assert response.status_code == 200

        # Redis 캐시 확인
        cache_key = "report:morning:2025-11-06"
        cached = test_redis.get(cache_key)
        assert cached is not None

        # TTL 확인 (12시간 = 43200초)
        ttl = test_redis.ttl(cache_key)
        assert 0 < ttl <= 43200
```

---

## ⏰ 배치 작업 테스트

### 1. 트리거 배치 작업

```python
# backend/tests/integration/test_trigger_batch.py

import pytest
from datetime import datetime
from app.scheduler.jobs import run_morning_triggers, run_afternoon_triggers

@pytest.mark.integration
@pytest.mark.asyncio
class TestTriggerBatch:
    """트리거 배치 작업 테스트"""

    async def test_morning_triggers_execution(self, test_db):
        """오전 트리거 실행"""
        # 배치 작업 실행
        results = await run_morning_triggers(datetime(2025, 11, 6, 9, 10))

        # 결과 검증
        assert results is not None
        assert len(results) > 0

        # DB 저장 확인
        from app.models.trigger import Trigger
        from sqlalchemy.orm import Session

        session = Session(bind=test_db)

        triggers = session.query(Trigger).filter(
            Trigger.date == datetime(2025, 11, 6).date(),
            Trigger.session == 'morning'
        ).all()

        assert len(triggers) > 0

        # 트리거 데이터 확인
        for trigger in triggers:
            assert trigger.ticker is not None
            assert trigger.trigger_type in [
                'volume_surge',
                'gap_up',
                'fund_inflow'
            ]
            assert 0 <= trigger.composite_score <= 1

    async def test_afternoon_triggers_execution(self, test_db):
        """오후 트리거 실행"""
        results = await run_afternoon_triggers(datetime(2025, 11, 6, 15, 30))

        assert results is not None

        # 트리거 타입 확인
        trigger_types = [r['trigger_type'] for r in results]
        valid_types = [
            'intraday_rise',
            'closing_strength',
            'sideways_volume'
        ]

        for trigger_type in trigger_types:
            assert trigger_type in valid_types

    async def test_trigger_deduplication(self, test_db):
        """중복 트리거 방지"""
        date = datetime(2025, 11, 6)

        # 첫 번째 실행
        await run_morning_triggers(date)

        # 두 번째 실행 (동일 날짜, 세션)
        await run_morning_triggers(date)

        # DB 확인
        from app.models.trigger import Trigger
        from sqlalchemy.orm import Session

        session = Session(bind=test_db)

        triggers = session.query(Trigger).filter(
            Trigger.date == date.date(),
            Trigger.session == 'morning'
        ).all()

        # 중복 제거 확인 (동일 종목은 1개만)
        tickers = [t.ticker for t in triggers]
        assert len(tickers) == len(set(tickers))
```

---

### 2. 리포트 배치 작업

```python
# backend/tests/integration/test_report_batch.py

@pytest.mark.integration
@pytest.mark.asyncio
class TestReportBatch:
    """리포트 배치 작업 테스트"""

    async def test_morning_report_generation(self, test_db, test_redis):
        """장 시작 리포트 생성"""
        from app.scheduler.jobs import generate_morning_report

        date = datetime(2025, 11, 6, 8, 30)

        # 리포트 생성
        report = await generate_morning_report(date)

        # 결과 검증
        assert report is not None
        assert report['report_type'] == 'morning'
        assert 'market_forecast' in report
        assert 'top_stocks' in report

        # DB 저장 확인
        from app.models.report import Report
        from sqlalchemy.orm import Session

        session = Session(bind=test_db)

        saved_report = session.query(Report).filter(
            Report.date == date.date(),
            Report.report_type == 'morning'
        ).first()

        assert saved_report is not None

        # Redis 캐싱 확인
        cache_key = f"report:morning:{date.date().isoformat()}"
        cached = test_redis.get(cache_key)
        assert cached is not None

    async def test_afternoon_report_generation(self, test_db):
        """장 마감 리포트 생성"""
        from app.scheduler.jobs import generate_afternoon_report

        date = datetime(2025, 11, 6, 15, 40)

        report = await generate_afternoon_report(date)

        assert report is not None
        assert report['report_type'] == 'afternoon'
        assert 'market_summary' in report
        assert 'surge_stocks' in report
```

---

## 💾 캐싱 테스트

```python
# backend/tests/integration/test_caching.py

@pytest.mark.integration
class TestCaching:
    """캐싱 통합 테스트"""

    def test_redis_connection(self, test_redis):
        """Redis 연결 확인"""
        # Ping 테스트
        assert test_redis.ping() is True

        # 쓰기/읽기 테스트
        test_redis.set("test_key", "test_value")
        assert test_redis.get("test_key") == "test_value"

        # 삭제
        test_redis.delete("test_key")
        assert test_redis.get("test_key") is None

    def test_cache_ttl(self, test_redis):
        """TTL 테스트"""
        import time

        # 2초 TTL로 설정
        test_redis.setex("ttl_test", 2, "value")

        # 즉시 조회
        assert test_redis.get("ttl_test") == "value"

        # TTL 확인
        ttl = test_redis.ttl("ttl_test")
        assert 0 < ttl <= 2

        # 2초 대기
        time.sleep(3)

        # 만료 확인
        assert test_redis.get("ttl_test") is None

    def test_analysis_cache_invalidation(self, client, test_redis):
        """분석 캐시 무효화"""
        ticker = "005930"

        # 분석 조회 (캐싱)
        response1 = client.get(f"/api/v1/analysis/{ticker}")
        assert response1.status_code == 200

        # 캐시 확인
        cache_key = f"analysis:{ticker}:{datetime.now().date().isoformat()}"
        assert test_redis.get(cache_key) is not None

        # 재분석 요청 (캐시 무효화)
        response2 = client.post(f"/api/v1/analysis/{ticker}/refresh")
        assert response2.status_code == 200

        # 캐시 삭제 확인
        assert test_redis.get(cache_key) is None

    def test_cache_fallback_to_db(self, client, test_redis):
        """캐시 미스 시 DB 조회"""
        # Redis 비활성화 (모킹)
        test_redis.flushdb()

        # API 호출 (DB에서 조회)
        response = client.get("/api/v1/triggers?session=morning&date=2025-11-06")

        # 정상 응답
        assert response.status_code == 200
```

---

## 🔄 전체 시스템 플로우 테스트

```python
# backend/tests/integration/test_end_to_end.py

@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEnd:
    """엔드투엔드 통합 테스트"""

    async def test_full_morning_workflow(self, client, test_db, test_redis):
        """오전 전체 워크플로우"""
        date = datetime(2025, 11, 6, 9, 10)

        # 1. 오전 트리거 실행
        from app.scheduler.jobs import run_morning_triggers
        triggers = await run_morning_triggers(date)

        assert len(triggers) > 0

        # 2. 장 시작 리포트 생성
        from app.scheduler.jobs import generate_morning_report
        report = await generate_morning_report(date)

        assert report is not None

        # 3. API를 통한 트리거 조회
        response = client.get(
            "/api/v1/triggers",
            params={"session": "morning", "date": date.date().isoformat()}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["triggers"]) > 0

        # 4. 리포트 조회
        response = client.get(
            "/api/v1/reports/morning",
            params={"date": date.date().isoformat()}
        )

        assert response.status_code == 200

    async def test_full_afternoon_workflow(self, client, test_db):
        """오후 전체 워크플로우"""
        date = datetime(2025, 11, 6, 15, 30)

        # 1. 오후 트리거 실행
        from app.scheduler.jobs import run_afternoon_triggers
        triggers = await run_afternoon_triggers(date)

        assert len(triggers) > 0

        # 2. 장 마감 리포트 생성
        from app.scheduler.jobs import generate_afternoon_report
        report = await generate_afternoon_report(date)

        assert report is not None

        # 3. API 조회
        response = client.get(
            "/api/v1/triggers",
            params={"session": "afternoon", "date": date.date().isoformat()}
        )

        assert response.status_code == 200

        # 4. 급등주 상세 분석
        trigger = triggers[0]
        response = client.get(f"/api/v1/analysis/{trigger['ticker']}")

        assert response.status_code == 200
```

---

## 🏃 테스트 실행

```bash
# 통합 테스트만 실행
pytest -m integration

# 특정 파일
pytest backend/tests/integration/test_triggers_api.py

# 병렬 실행 (빠른 실행)
pytest -m integration -n auto

# 상세 출력
pytest -m integration -v
```

---

## 📊 테스트 환경 분리

```bash
# .env.test

DATABASE_URL=postgresql://test:test@localhost/skku_insight_test
REDIS_URL=redis://localhost:6379/1

# LLM 비활성화 (통합 테스트에서는 모킹)
USE_LLM=false

# 로그 레벨
LOG_LEVEL=DEBUG
```

---

## 🐳 Docker Compose로 테스트 환경 구성

```yaml
# docker-compose.test.yml

version: '3.8'

services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: skku_insight_test
    ports:
      - "5433:5432"

  redis-test:
    image: redis:7
    ports:
      - "6380:6379"
```

```bash
# 테스트 환경 실행
docker-compose -f docker-compose.test.yml up -d

# 테스트 실행
pytest -m integration

# 환경 정리
docker-compose -f docker-compose.test.yml down -v
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
