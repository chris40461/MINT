# Redis 캐싱 전략

## 📌 문서 목적

SKKU-INSIGHT의 Redis 캐싱 전략을 정의하고, 캐시 키 설계, TTL 정책, 무효화 전략, 메모리 관리 방법을 설명합니다.

---

## 🎯 캐싱 목적

### 1. 성능 향상
- **API 응답 시간 단축**: DB 쿼리 → Redis 조회 (10ms 이내)
- **LLM 비용 절감**: 동일 요청 캐시 반환 (80% 절감)

### 2. 부하 감소
- **DB 부하 감소**: 반복 쿼리 제거
- **외부 API 호출 최소화**: pykrx, Gemini API

### 3. 사용자 경험
- **즉시 응답**: 캐시 히트 시 즉각 반환
- **실시간 업데이트**: TTL 관리로 최신 데이터 보장

---

## 🗂️ Redis 데이터 구조

### 선택한 데이터 타입

| 데이터 | Redis 타입 | 이유 |
|--------|-----------|------|
| 급등주 목록 | String (JSON) | 전체 조회 |
| 기업 분석 | String (JSON) | 복잡한 중첩 구조 |
| 종목 기본 정보 | Hash | 필드별 조회 가능 |
| Rate Limiting | String (Counter) | 간단한 증감 |
| 세션 데이터 | Hash | 사용자별 상태 |

---

## 🔑 캐시 키 설계

### 네이밍 규칙
```
{service}:{resource}:{identifier}:{sub_identifier}
```

### 키 목록

#### 1. 급등주 트리거
```python
# 전체 세션
"triggers:morning:2025-11-06"
"triggers:afternoon:2025-11-06"

# 특정 트리거 타입
"triggers:morning:2025-11-06:volume_surge"
"triggers:afternoon:2025-11-06:closing_strength"

# 종목별 히스토리
"triggers:history:005930"  # List 타입
```

**데이터 구조**:
```json
{
  "session": "morning",
  "date": "2025-11-06",
  "generated_at": "2025-11-06T09:15:23",
  "triggers": [
    {
      "type": "volume_surge",
      "stocks": [...]
    }
  ]
}
```

**TTL**: 1시간 (3600초)

#### 2. 기업 분석
```python
# 기업 분석 결과
"analysis:005930:2025-11-06"

# 간단 요약 (빠른 조회용)
"analysis:summary:005930:2025-11-06"
```

**데이터 구조**:
```json
{
  "ticker": "005930",
  "date": "2025-11-06",
  "investment_opinion": "BUY",
  "target_price": 85000,
  "current_price": 75000,
  "upside_potential": 13.33,
  "analysis": {...},  // 전체 분석 내용
  "metadata": {
    "generated_at": "2025-11-06T10:30:15",
    "model": "gemini-2.5-flash",
    "tokens_used": 1850
  }
}
```

**TTL**: 24시간 (86400초)

#### 3. 장 리포트
```python
"report:morning:2025-11-06"
"report:afternoon:2025-11-06"
```

**TTL**: 12시간 (43200초)

#### 4. 종목 기본 정보
```python
# Hash 타입
"stock:info:005930"
```

**데이터 구조** (Hash):
```
HSET stock:info:005930 ticker "005930"
HSET stock:info:005930 name "삼성전자"
HSET stock:info:005930 market "KOSPI"
HSET stock:info:005930 sector "IT/반도체"
```

**TTL**: 7일 (604800초)

#### 5. 가격 데이터
```python
# 최근 30일 가격 (List 타입)
"price:history:005930"
```

**데이터 구조** (List of JSON):
```json
[
  {"date": "2025-11-06", "open": 73500, "high": 76000, "low": 73000, "close": 75000},
  {"date": "2025-11-05", "open": 72000, "high": 74000, "low": 71500, "close": 73000}
]
```

**TTL**: 1시간 (3600초)

#### 6. Rate Limiting
```python
# IP 기반 제한
"rate_limit:ip:192.168.1.1:2025-11-06:14:30"  # 분 단위
"rate_limit:api:analysis:192.168.1.1:2025-11-06:14"  # 시간 단위
```

**데이터 구조**: 숫자 (Counter)
```
SET rate_limit:ip:192.168.1.1:2025-11-06:14:30 1
INCR rate_limit:ip:192.168.1.1:2025-11-06:14:30
```

**TTL**: 60초 (분 단위) / 3600초 (시간 단위)

#### 7. LLM 요청 추적
```python
"llm:requests:2025-11-06"  # Hash 타입
```

**데이터 구조**:
```
HSET llm:requests:2025-11-06 count 150
HSET llm:requests:2025-11-06 tokens 280000
HSET llm:requests:2025-11-06 cost 2.8
```

**TTL**: 30일 (2592000초)

---

## ⏱️ TTL 정책

### TTL 결정 기준

| 데이터 | TTL | 이유 |
|--------|-----|------|
| 급등주 트리거 | 1시간 | 장 중 변동성 |
| 기업 분석 | 24시간 | 일일 업데이트 충분 |
| 장 리포트 | 12시간 | 하루 2회 생성 |
| 종목 정보 | 7일 | 거의 변경 없음 |
| 가격 히스토리 | 1시간 | 실시간 반영 |
| Rate Limit | 60초 | 분당 제한 |

### TTL 구현

```python
import redis
from datetime import timedelta

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

    def set_triggers(self, session: str, date: str, data: dict):
        """급등주 캐싱 (TTL: 1시간)"""
        key = f"triggers:{session}:{date}"
        self.redis.setex(
            key,
            timedelta(hours=1),
            json.dumps(data, ensure_ascii=False)
        )

    def set_analysis(self, ticker: str, date: str, data: dict):
        """기업 분석 캐싱 (TTL: 24시간)"""
        key = f"analysis:{ticker}:{date}"
        self.redis.setex(
            key,
            timedelta(days=1),
            json.dumps(data, ensure_ascii=False)
        )

    def set_report(self, report_type: str, date: str, data: dict):
        """장 리포트 캐싱 (TTL: 12시간)"""
        key = f"report:{report_type}:{date}"
        self.redis.setex(
            key,
            timedelta(hours=12),
            json.dumps(data, ensure_ascii=False)
        )
```

### TTL 연장 전략

```python
def extend_ttl_if_popular(key: str):
    """
    인기 있는 종목은 TTL 연장
    (조회 횟수가 임계값 이상일 때)
    """
    views_key = f"{key}:views"
    views = int(redis.get(views_key) or 0)

    if views > 100:  # 100회 이상 조회
        # TTL을 2배로 연장
        current_ttl = redis.ttl(key)
        if current_ttl > 0:
            redis.expire(key, current_ttl * 2)
```

---

## 🔄 캐시 무효화 전략

### 1. TTL 기반 자동 만료
가장 간단하고 안전한 방법

```python
# 자동으로 만료됨
redis.setex("analysis:005930:2025-11-06", 86400, data)
```

### 2. 이벤트 기반 무효화

#### 중요 공시 발생 시
```python
def invalidate_on_disclosure(ticker: str):
    """
    DART API 웹훅으로 중요 공시 감지 시
    해당 종목의 분석 캐시 삭제
    """
    pattern = f"analysis:{ticker}:*"
    keys = redis.keys(pattern)
    if keys:
        redis.delete(*keys)
        logger.info(f"Invalidated {len(keys)} cache keys for {ticker}")
```

#### 급등/급락 발생 시
```python
def invalidate_on_price_change(ticker: str, change_rate: float):
    """
    10% 이상 급등/급락 시 캐시 무효화
    """
    if abs(change_rate) >= 10:
        redis.delete(f"analysis:{ticker}:*")
        logger.warning(f"Price shock detected for {ticker}: {change_rate}%")
```

#### 시간 기반 무효화
```python
from apscheduler.schedulers.background import BackgroundScheduler

def scheduled_invalidation():
    """
    매일 자정: 만료된 캐시 정리
    매주 일요일: 전체 캐시 갱신
    """
    scheduler = BackgroundScheduler()

    # 매일 자정 실행
    scheduler.add_job(
        cleanup_expired_cache,
        trigger="cron",
        hour=0,
        minute=0
    )

    # 매주 일요일 자정
    scheduler.add_job(
        refresh_all_cache,
        trigger="cron",
        day_of_week="sun",
        hour=0
    )

    scheduler.start()
```

### 3. 버전 기반 무효화

```python
# 캐시 키에 버전 포함
CACHE_VERSION = "v2"

def get_versioned_key(base_key: str) -> str:
    return f"{base_key}:{CACHE_VERSION}"

# 버전 변경 시 자동으로 이전 캐시 무효화
key = get_versioned_key("analysis:005930:2025-11-06")
```

### 4. Tag 기반 무효화

```python
def tag_cache(key: str, tags: list):
    """
    캐시에 태그 추가 (집합 사용)
    """
    for tag in tags:
        redis.sadd(f"tag:{tag}", key)

def invalidate_by_tag(tag: str):
    """
    특정 태그의 모든 캐시 삭제
    """
    keys = redis.smembers(f"tag:{tag}")
    if keys:
        redis.delete(*keys)
        redis.delete(f"tag:{tag}")

# 사용 예시
tag_cache("analysis:005930:2025-11-06", ["sector:IT", "market:KOSPI"])
invalidate_by_tag("sector:IT")  # IT 섹터 전체 무효화
```

---

## 💾 메모리 관리

### 1. 최대 메모리 설정

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU 정책
```

### 2. 메모리 정책

| 정책 | 설명 | 적합성 |
|------|------|--------|
| noeviction | 메모리 부족 시 에러 | ❌ 서비스 중단 |
| allkeys-lru | 모든 키에서 LRU 제거 | ✅ 추천 |
| volatile-lru | TTL 있는 키에서 LRU | ⚠️ TTL 없으면 문제 |
| allkeys-random | 랜덤 제거 | ❌ 비효율적 |

**선택**: `allkeys-lru` (가장 오래 사용하지 않은 키 제거)

### 3. 메모리 모니터링

```python
def check_memory_usage():
    """Redis 메모리 사용량 체크"""
    info = redis.info('memory')

    used_memory_mb = info['used_memory'] / (1024 * 1024)
    max_memory_mb = info['maxmemory'] / (1024 * 1024)
    usage_percent = (used_memory_mb / max_memory_mb) * 100

    logger.info(f"Redis Memory: {used_memory_mb:.2f}MB / {max_memory_mb:.2f}MB ({usage_percent:.1f}%)")

    # 80% 이상 사용 시 경고
    if usage_percent >= 80:
        logger.warning("Redis memory usage is high!")
        # 수동 정리 트리거
        cleanup_old_cache()

    return {
        "used_mb": used_memory_mb,
        "max_mb": max_memory_mb,
        "usage_percent": usage_percent
    }
```

### 4. 캐시 압축

```python
import gzip
import json

def compress_cache(data: dict) -> bytes:
    """큰 데이터는 압축하여 저장"""
    json_str = json.dumps(data, ensure_ascii=False)
    compressed = gzip.compress(json_str.encode('utf-8'))
    return compressed

def decompress_cache(compressed: bytes) -> dict:
    """압축 해제"""
    decompressed = gzip.decompress(compressed)
    return json.loads(decompressed.decode('utf-8'))

# 사용 예시
def set_large_data(key: str, data: dict):
    if len(json.dumps(data)) > 100 * 1024:  # 100KB 이상
        compressed = compress_cache(data)
        redis.setex(f"{key}:compressed", 86400, compressed)
    else:
        redis.setex(key, 86400, json.dumps(data))
```

---

## 📊 캐시 성능 측정

### 1. Hit Rate 계산

```python
class CacheMetrics:
    def __init__(self):
        self.hits = 0
        self.misses = 0

    def record_hit(self):
        self.hits += 1

    def record_miss(self):
        self.misses += 1

    def get_hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def reset(self):
        self.hits = 0
        self.misses = 0

# 전역 metrics 객체
cache_metrics = CacheMetrics()

# 사용 예시
def get_cached_analysis(ticker: str, date: str) -> dict:
    key = f"analysis:{ticker}:{date}"
    cached = redis.get(key)

    if cached:
        cache_metrics.record_hit()
        return json.loads(cached)
    else:
        cache_metrics.record_miss()
        return None
```

### 2. 응답 시간 측정

```python
import time

def measure_cache_performance():
    """캐시 vs DB 성능 비교"""

    # 캐시 조회
    start = time.time()
    cached = redis.get("analysis:005930:2025-11-06")
    cache_time = (time.time() - start) * 1000  # ms

    # DB 조회
    start = time.time()
    db_result = db.query("SELECT * FROM analysis WHERE ticker='005930'")
    db_time = (time.time() - start) * 1000

    logger.info(f"Cache: {cache_time:.2f}ms, DB: {db_time:.2f}ms")
    logger.info(f"Speedup: {db_time / cache_time:.1f}x")
```

---

## 🔐 캐시 보안

### 1. 민감 데이터 암호화

```python
from cryptography.fernet import Fernet

class SecureCache:
    def __init__(self, encryption_key: bytes):
        self.fernet = Fernet(encryption_key)

    def set_secure(self, key: str, data: dict, ttl: int):
        """민감한 데이터 암호화 저장"""
        json_str = json.dumps(data)
        encrypted = self.fernet.encrypt(json_str.encode())
        redis.setex(f"secure:{key}", ttl, encrypted)

    def get_secure(self, key: str) -> dict:
        """복호화 조회"""
        encrypted = redis.get(f"secure:{key}")
        if encrypted:
            decrypted = self.fernet.decrypt(encrypted)
            return json.loads(decrypted.decode())
        return None
```

### 2. Redis 인증

```conf
# redis.conf
requirepass your_strong_password_here
```

```python
redis = Redis(
    host='localhost',
    port=6379,
    password=os.getenv('REDIS_PASSWORD')
)
```

---

## 🚀 고급 캐싱 전략

### 1. Cache Warming (사전 캐싱)

```python
async def warm_cache_before_market_open():
    """
    장 시작 30분 전 (08:30)
    인기 종목 사전 캐싱
    """
    popular_tickers = ["005930", "000660", "035420", "005380", "051910"]

    tasks = []
    for ticker in popular_tickers:
        task = analyze_and_cache(ticker)
        tasks.append(task)

    await asyncio.gather(*tasks)
    logger.info(f"Warmed cache for {len(popular_tickers)} stocks")
```

### 2. Cache Aside Pattern

```python
async def get_analysis_with_cache_aside(ticker: str, date: str) -> dict:
    """
    1. 캐시 조회
    2. 없으면 DB 조회
    3. DB에도 없으면 LLM 생성
    4. 결과를 캐시 및 DB에 저장
    """
    # 1. 캐시 조회
    cache_key = f"analysis:{ticker}:{date}"
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. DB 조회
    db_result = db.query(
        "SELECT * FROM analysis WHERE ticker=? AND date=?",
        (ticker, date)
    )
    if db_result:
        # DB 결과를 캐시에 저장
        redis.setex(cache_key, 86400, json.dumps(db_result))
        return db_result

    # 3. LLM 생성
    analysis = await generate_analysis_with_llm(ticker)

    # 4. 캐시 및 DB 저장
    redis.setex(cache_key, 86400, json.dumps(analysis))
    db.insert("analysis", analysis)

    return analysis
```

### 3. Write-Through Cache

```python
def save_analysis_with_write_through(ticker: str, date: str, analysis: dict):
    """
    DB 저장과 동시에 캐시 업데이트
    """
    # 1. DB 저장
    db.insert("analysis", analysis)

    # 2. 캐시 업데이트
    cache_key = f"analysis:{ticker}:{date}"
    redis.setex(cache_key, 86400, json.dumps(analysis))

    logger.info(f"Saved analysis for {ticker} to DB and cache")
```

### 4. Lazy Loading

```python
def get_stock_info(ticker: str) -> dict:
    """
    요청 시점에 캐시 생성 (Lazy)
    """
    cache_key = f"stock:info:{ticker}"
    cached = redis.get(cache_key)

    if cached:
        return json.loads(cached)

    # 캐시 미스 → DB 조회
    stock_info = db.query("SELECT * FROM stocks WHERE ticker=?", (ticker,))

    if stock_info:
        # 캐시 저장 (Lazy)
        redis.setex(cache_key, 604800, json.dumps(stock_info))

    return stock_info
```

---

## 🧪 캐시 테스트

### 1. 단위 테스트

```python
import pytest

class TestCacheService:
    def test_set_and_get_triggers(self):
        """트리거 캐싱 테스트"""
        data = {"session": "morning", "triggers": [...]}
        cache.set_triggers("morning", "2025-11-06", data)

        retrieved = cache.get_triggers("morning", "2025-11-06")
        assert retrieved == data

    def test_ttl_expiration(self):
        """TTL 만료 테스트"""
        cache.set_triggers("morning", "2025-11-06", {"test": "data"})

        # 1시간 후 시뮬레이션 (freezegun 사용)
        with freeze_time("2025-11-06 10:15:00"):
            result = cache.get_triggers("morning", "2025-11-06")
            assert result is None  # 만료됨

    def test_cache_invalidation(self):
        """캐시 무효화 테스트"""
        cache.set_analysis("005930", "2025-11-06", {"test": "data"})
        cache.invalidate_analysis("005930")

        result = cache.get_analysis("005930", "2025-11-06")
        assert result is None
```

### 2. 부하 테스트

```python
import asyncio
import time

async def load_test_cache():
    """
    1000개 동시 요청으로 캐시 성능 테스트
    """
    async def single_request():
        start = time.time()
        result = cache.get_analysis("005930", "2025-11-06")
        elapsed = (time.time() - start) * 1000
        return elapsed

    # 1000개 동시 요청
    tasks = [single_request() for _ in range(1000)]
    response_times = await asyncio.gather(*tasks)

    # 통계
    avg_time = sum(response_times) / len(response_times)
    max_time = max(response_times)
    min_time = min(response_times)

    logger.info(f"Avg: {avg_time:.2f}ms, Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
```

---

## 📈 모니터링 대시보드

### Prometheus + Grafana

```python
from prometheus_client import Counter, Histogram, Gauge

# 메트릭 정의
cache_hits = Counter('cache_hits_total', 'Total cache hits')
cache_misses = Counter('cache_misses_total', 'Total cache misses')
cache_latency = Histogram('cache_latency_seconds', 'Cache access latency')
cache_memory = Gauge('cache_memory_bytes', 'Current cache memory usage')

# 사용 예시
def get_with_metrics(key: str):
    with cache_latency.time():
        result = redis.get(key)

        if result:
            cache_hits.inc()
        else:
            cache_misses.inc()

        return result
```

---

## 📚 참고 자료

- [Redis Documentation](https://redis.io/docs/)
- [Caching Strategies](https://docs.aws.amazon.com/AmazonElastiCache/latest/mem-ug/Strategies.html)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
