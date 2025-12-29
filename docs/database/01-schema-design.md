# 데이터베이스 스키마 설계

## 📌 문서 목적

SKKU-INSIGHT의 전체 데이터베이스 스키마를 정의하고, 테이블 구조, 관계, 인덱스 전략, 마이그레이션 계획을 설명합니다.

---

## 🗄️ 데이터베이스 선택

### Phase 1: SQLite
**사용 이유**:
- 설치 불필요 (파일 기반)
- 설정 간단
- 로컬 프로토타입에 적합
- 마이그레이션 용이

### Phase 2: PostgreSQL
**전환 이유**:
- 동시 접속 지원
- 트랜잭션 성능
- 복잡한 쿼리 최적화
- JSON 지원

---

## 📊 ER Diagram (개체-관계도)

```
┌─────────────┐
│   stocks    │ (종목 기본 정보)
└──────┬──────┘
       │ 1
       │
       │ N
  ┌────┴────┬────────┬────────┬────────┐
  │         │        │        │        │
  ↓ N       ↓ N      ↓ N      ↓ N      ↓ N
┌──────┐ ┌──────┐ ┌───────┐ ┌───────┐ ┌───────┐
│price │ │trig  │ │analys │ │recom  │ │feedbk │
│histo │ │gers  │ │is     │ │mendtn │ │       │
└──────┘ └──────┘ └───────┘ └───────┘ └───────┘
```

---

## 📋 테이블 상세 스키마

## 1. stocks (종목 기본 정보)

**목적**: 종목 마스터 데이터

```sql
CREATE TABLE stocks (
    -- Primary Key
    ticker VARCHAR(6) PRIMARY KEY,  -- 종목 코드 (6자리)

    -- 기본 정보
    name VARCHAR(100) NOT NULL,  -- 종목명
    name_en VARCHAR(100),  -- 영문명
    market VARCHAR(10) NOT NULL,  -- KOSPI / KOSDAQ
    sector VARCHAR(50),  -- 섹터 (IT/반도체, 자동차 등)
    industry VARCHAR(100),  -- 세부 업종

    -- 상장 정보
    listed_date DATE,  -- 상장일
    listing_shares BIGINT,  -- 상장 주식 수
    description TEXT,  -- 기업 설명
    website VARCHAR(255),  -- 웹사이트
    ceo VARCHAR(100),  -- 대표이사

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,  -- 상장폐지 여부

    -- 인덱스
    INDEX idx_name (name),
    INDEX idx_market (market),
    INDEX idx_sector (sector),
    INDEX idx_active (is_active)
);
```

**예시 데이터**:
```sql
INSERT INTO stocks VALUES (
    '005930',
    '삼성전자',
    'Samsung Electronics',
    'KOSPI',
    'IT/반도체',
    '메모리 반도체',
    '1975-06-11',
    5969782550,
    '세계 1위 메모리 반도체 제조사',
    'https://www.samsung.com',
    '한종희',
    NOW(),
    NOW(),
    TRUE
);
```

---

## 2. price_history (가격 히스토리)

**목적**: OHLCV 데이터 저장

```sql
CREATE TABLE price_history (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Foreign Key
    ticker VARCHAR(6) NOT NULL,
    date DATE NOT NULL,

    -- OHLCV
    open DECIMAL(10, 2) NOT NULL,
    high DECIMAL(10, 2) NOT NULL,
    low DECIMAL(10, 2) NOT NULL,
    close DECIMAL(10, 2) NOT NULL,
    volume BIGINT NOT NULL,

    -- 파생 데이터
    trading_value BIGINT,  -- 거래대금 (close * volume)
    market_cap BIGINT,  -- 시가총액
    change_rate DECIMAL(5, 2),  -- 등락률 (%)
    change_amount DECIMAL(10, 2),  -- 등락폭

    -- 외국인/기관 데이터
    foreign_net BIGINT,  -- 외국인 순매수
    institution_net BIGINT,  -- 기관 순매수

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 외래 키
    FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE,

    -- 인덱스
    UNIQUE INDEX idx_ticker_date (ticker, date),
    INDEX idx_date (date),
    INDEX idx_ticker (ticker)
);
```

**쿼리 예시**:
```sql
-- 최근 30일 가격 조회
SELECT * FROM price_history
WHERE ticker = '005930'
  AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY date DESC;

-- 특정일 거래대금 Top 10
SELECT ticker, trading_value
FROM price_history
WHERE date = '2025-11-06'
ORDER BY trading_value DESC
LIMIT 10;
```

---

## 3. triggers (급등주 트리거)

**목적**: 급등주 감지 결과 저장

```sql
CREATE TABLE triggers (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- 트리거 정보
    date DATE NOT NULL,
    session VARCHAR(10) NOT NULL,  -- morning / afternoon
    trigger_type VARCHAR(30) NOT NULL,  -- volume_surge, gap_up, etc.

    -- Foreign Key
    ticker VARCHAR(6) NOT NULL,

    -- 트리거 데이터
    rank INT NOT NULL,  -- 순위 (1-3)
    composite_score DECIMAL(5, 4) NOT NULL,  -- 복합 점수 (0-1)

    -- 가격 정보 (트리거 시점)
    price_at_trigger DECIMAL(10, 2) NOT NULL,
    change_rate DECIMAL(5, 2),
    volume BIGINT,
    volume_increase_rate DECIMAL(5, 2),
    trading_value BIGINT,

    -- 지표 (JSON)
    indicators JSON,  -- {"volume_increase_norm": 0.95, "volume_norm": 0.88}

    -- 성과 추적 (나중에 업데이트)
    d_plus_1_return DECIMAL(5, 2),  -- D+1 수익률
    d_plus_7_return DECIMAL(5, 2),  -- D+7 수익률

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP,  -- 평가 완료 시각

    -- 외래 키
    FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE,

    -- 인덱스
    INDEX idx_date_session (date, session),
    INDEX idx_ticker (ticker),
    INDEX idx_trigger_type (trigger_type),
    INDEX idx_date_ticker (date, ticker)
);
```

**예시 데이터**:
```sql
INSERT INTO triggers VALUES (
    NULL,
    '2025-11-06',
    'morning',
    'volume_surge',
    '005930',
    1,
    0.92,
    75000,
    3.45,
    15000000,
    45.2,
    1125000000000,
    '{"volume_increase_norm": 0.95, "volume_norm": 0.88}',
    NULL,  -- 아직 평가 안됨
    NULL,
    NOW(),
    NULL
);
```

**쿼리 예시**:
```sql
-- 오늘 오전 트리거 Top 3 조회
SELECT * FROM triggers
WHERE date = CURDATE()
  AND session = 'morning'
  AND trigger_type = 'volume_surge'
ORDER BY rank ASC;

-- 특정 종목의 트리거 히스토리
SELECT date, session, trigger_type, rank, composite_score, d_plus_1_return
FROM triggers
WHERE ticker = '005930'
  AND date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
ORDER BY date DESC;

-- 평균 승률 계산
SELECT
    trigger_type,
    COUNT(*) as total,
    AVG(CASE WHEN d_plus_1_return > 0 THEN 1 ELSE 0 END) as win_rate
FROM triggers
WHERE evaluated_at IS NOT NULL
GROUP BY trigger_type;
```

---

## 4. analysis (기업 분석)

**목적**: LLM 기업 분석 결과 저장

```sql
CREATE TABLE analysis (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- Foreign Key
    ticker VARCHAR(6) NOT NULL,
    date DATE NOT NULL,

    -- 분석 결과
    investment_opinion VARCHAR(20) NOT NULL,  -- STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    target_price DECIMAL(10, 2),
    current_price DECIMAL(10, 2),
    upside_potential DECIMAL(5, 2),  -- 상승 여력 (%)
    confidence_score DECIMAL(3, 2),  -- 신뢰도 (0-1)

    -- 주요 인사이트 (JSON Array)
    key_insights JSON,
    -- ["반도체 슈퍼 사이클 진입", "HBM3 시장 점유율 확대"]

    -- 상세 분석 (TEXT)
    financial_analysis TEXT,
    industry_analysis TEXT,
    news_analysis TEXT,
    technical_analysis TEXT,
    risk_factors TEXT,
    investment_strategy TEXT,

    -- 재무 지표 (JSON)
    financial_metrics JSON,
    -- {
    --   "per": 12.5,
    --   "pbr": 1.8,
    --   "roe": 14.2,
    --   "revenue": 300000000000000,
    --   "debt_ratio": 45.3
    -- }

    -- 기술적 지표 (JSON)
    technical_indicators JSON,
    -- {
    --   "rsi": 62.3,
    --   "macd": {"value": 120, "signal": 115},
    --   "ma_5": 74500
    -- }

    -- 뉴스 센티먼트 (JSON)
    news_sentiment JSON,
    -- {
    --   "positive": 28,
    --   "neutral": 10,
    --   "negative": 4,
    --   "overall_score": 0.75
    -- }

    -- LLM 메타데이터
    model VARCHAR(50),  -- gemini-2.5-flash
    tokens_used INT,
    processing_time_ms INT,

    -- 메타데이터
    source VARCHAR(20),  -- llm / cache
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- TTL (24시간 후)

    -- 외래 키
    FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE,

    -- 인덱스
    UNIQUE INDEX idx_ticker_date (ticker, date),
    INDEX idx_date (date),
    INDEX idx_opinion (investment_opinion),
    INDEX idx_expires_at (expires_at)
);
```

**쿼리 예시**:
```sql
-- 최신 분석 조회
SELECT * FROM analysis
WHERE ticker = '005930'
ORDER BY date DESC
LIMIT 1;

-- 매수 의견 종목 조회
SELECT ticker, investment_opinion, target_price, upside_potential
FROM analysis
WHERE date = CURDATE()
  AND investment_opinion IN ('STRONG_BUY', 'BUY')
ORDER BY upside_potential DESC;

-- 만료된 분석 삭제
DELETE FROM analysis
WHERE expires_at < NOW();
```

---

## 5. reports (장 리포트)

**목적**: 장 시작/마감 리포트 저장

```sql
CREATE TABLE reports (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- 리포트 정보
    date DATE NOT NULL,
    report_type VARCHAR(10) NOT NULL,  -- morning / afternoon

    -- 시장 개요 (JSON)
    market_overview JSON,
    -- {
    --   "kospi": {"close": 2500.5, "change_rate": -0.45},
    --   "us_market": {"sp500": 1.2},
    --   "exchange_rate": {"usd_krw": 1320}
    -- }

    -- 시장 전망
    market_forecast TEXT,
    expected_direction VARCHAR(10),  -- 상승 / 하락 / 횡보
    confidence DECIMAL(3, 2),

    -- 주목 종목 (JSON Array)
    top_stocks JSON,
    -- [
    --   {"ticker": "005930", "rank": 1, "score": 0.88, "rationale": "..."},
    --   ...
    -- ]

    -- 섹터 분석 (JSON)
    sector_analysis JSON,

    -- 투자 전략
    investment_strategy TEXT,

    -- 주요 이벤트 (JSON Array)
    key_events JSON,

    -- LLM 메타데이터
    model VARCHAR(50),
    tokens_used INT,
    processing_time_ms INT,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,

    -- 인덱스
    UNIQUE INDEX idx_date_type (date, report_type),
    INDEX idx_date (date)
);
```

**쿼리 예시**:
```sql
-- 오늘 장 시작 리포트
SELECT * FROM reports
WHERE date = CURDATE()
  AND report_type = 'morning';

-- 최근 7일 리포트
SELECT date, report_type, expected_direction, confidence
FROM reports
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
ORDER BY date DESC, report_type ASC;
```

---

## 6. recommendations (추천 종목 추적)

**목적**: 예측 정확도 평가를 위한 추천 기록

```sql
CREATE TABLE recommendations (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- 추천 정보
    ticker VARCHAR(6) NOT NULL,
    date DATE NOT NULL,
    source VARCHAR(20) NOT NULL,  -- analysis / morning_report / afternoon_report

    -- 추천 내용
    opinion VARCHAR(20) NOT NULL,  -- BUY, SELL, HOLD
    target_price DECIMAL(10, 2),
    stop_loss DECIMAL(10, 2),
    entry_price DECIMAL(10, 2),  -- 추천 시점 가격

    -- 성과 추적
    actual_price_d1 DECIMAL(10, 2),  -- D+1 종가
    actual_price_d7 DECIMAL(10, 2),  -- D+7 종가
    actual_return_d1 DECIMAL(5, 2),  -- D+1 수익률
    actual_return_d7 DECIMAL(5, 2),  -- D+7 수익률

    -- 평가 결과
    hit BOOLEAN,  -- 예측 성공 여부
    target_achieved BOOLEAN,  -- 목표가 달성 여부
    days_to_achieve INT,  -- 목표가 도달 일수

    -- 메타데이터
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evaluated_at TIMESTAMP,

    -- 외래 키
    FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE,

    -- 인덱스
    INDEX idx_date (date),
    INDEX idx_ticker (ticker),
    INDEX idx_source (source),
    INDEX idx_evaluated (evaluated_at)
);
```

**쿼리 예시**:
```sql
-- 평가 대기 중인 추천 (D+1 평가)
SELECT * FROM recommendations
WHERE evaluated_at IS NULL
  AND date = DATE_SUB(CURDATE(), INTERVAL 1 DAY);

-- 승률 계산
SELECT
    source,
    COUNT(*) as total,
    SUM(CASE WHEN hit = TRUE THEN 1 ELSE 0 END) as hits,
    AVG(CASE WHEN hit = TRUE THEN 1.0 ELSE 0.0 END) as win_rate,
    AVG(actual_return_d1) as avg_return
FROM recommendations
WHERE evaluated_at IS NOT NULL
GROUP BY source;

-- 목표가 달성률
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN target_achieved = TRUE THEN 1 ELSE 0 END) as achieved,
    AVG(CASE WHEN target_achieved = TRUE THEN 1.0 ELSE 0.0 END) as achievement_rate,
    AVG(days_to_achieve) as avg_days
FROM recommendations
WHERE target_price IS NOT NULL
  AND evaluated_at IS NOT NULL;
```

---

## 7. user_feedback (사용자 피드백)

**목적**: 사용자 만족도 및 피드백 수집

```sql
CREATE TABLE user_feedback (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- 피드백 대상
    feedback_type VARCHAR(20) NOT NULL,  -- analysis / morning_report / afternoon_report / trigger
    reference_id BIGINT,  -- analysis.id / reports.id / triggers.id
    ticker VARCHAR(6),
    date DATE,

    -- 피드백 내용
    rating INT,  -- 1-5 점수
    helpful BOOLEAN,  -- 도움이 되었는지
    comment TEXT,  -- 자유 의견

    -- 메타데이터
    ip_address VARCHAR(45),  -- 익명 추적 (IPv6 지원)
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 외래 키
    FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE SET NULL,

    -- 인덱스
    INDEX idx_type (feedback_type),
    INDEX idx_date (date),
    INDEX idx_rating (rating)
);
```

**쿼리 예시**:
```sql
-- 평균 평점 조회
SELECT
    feedback_type,
    AVG(rating) as avg_rating,
    COUNT(*) as total_feedback
FROM user_feedback
WHERE date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY feedback_type;

-- 부정적 피드백 분석
SELECT ticker, comment
FROM user_feedback
WHERE rating <= 2
  AND comment IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

---

## 8. system_logs (시스템 로그)

**목적**: 시스템 이벤트 및 에러 로깅

```sql
CREATE TABLE system_logs (
    -- Primary Key
    id BIGINT AUTO_INCREMENT PRIMARY KEY,

    -- 로그 정보
    log_level VARCHAR(10) NOT NULL,  -- DEBUG / INFO / WARNING / ERROR
    module VARCHAR(50) NOT NULL,  -- trigger_service / llm_service / data_service
    message TEXT NOT NULL,

    -- 상세 정보 (JSON)
    details JSON,
    -- {
    --   "ticker": "005930",
    --   "error": "LLM API timeout",
    --   "retry_count": 3
    -- }

    -- 메타데이터
    request_id VARCHAR(50),  -- X-Request-ID
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 인덱스
    INDEX idx_level (log_level),
    INDEX idx_module (module),
    INDEX idx_created_at (created_at),
    INDEX idx_request_id (request_id)
);
```

**쿼리 예시**:
```sql
-- 최근 에러 조회
SELECT * FROM system_logs
WHERE log_level = 'ERROR'
  AND created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
ORDER BY created_at DESC;

-- 모듈별 에러 빈도
SELECT
    module,
    COUNT(*) as error_count
FROM system_logs
WHERE log_level = 'ERROR'
  AND created_at >= DATE_SUB(NOW(), INTERVAL 1 DAY)
GROUP BY module
ORDER BY error_count DESC;
```

---

## 🔗 관계 정리

```
stocks (1) ─── (N) price_history
stocks (1) ─── (N) triggers
stocks (1) ─── (N) analysis
stocks (1) ─── (N) recommendations
stocks (1) ─── (N) user_feedback
```

---

## 📈 인덱스 전략

### 1. Primary Key 인덱스
모든 테이블의 id 컬럼은 자동으로 클러스터드 인덱스 생성

### 2. Foreign Key 인덱스
외래 키 컬럼에 자동으로 인덱스 생성

### 3. 복합 인덱스

**자주 함께 조회되는 컬럼**:
```sql
-- triggers 테이블
CREATE INDEX idx_date_session_type ON triggers(date, session, trigger_type);

-- price_history 테이블
CREATE INDEX idx_ticker_date_desc ON price_history(ticker, date DESC);

-- analysis 테이블
CREATE INDEX idx_date_opinion ON analysis(date, investment_opinion);
```

### 4. 커버링 인덱스

**전체 스캔 방지**:
```sql
-- 트리거 목록 조회 최적화
CREATE INDEX idx_trigger_covering ON triggers(
    date, session, trigger_type,
    ticker, rank, composite_score, price_at_trigger
);
```

---

## 🔄 마이그레이션 계획

### Phase 1: 초기 스키마 생성
```bash
# Alembic 초기화
alembic init alembic

# 초기 마이그레이션 생성
alembic revision -m "Initial schema"

# 마이그레이션 적용
alembic upgrade head
```

### Phase 2: 스키마 변경
```python
# alembic/versions/001_add_user_table.py

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger, primary_key=True),
        sa.Column('email', sa.String(255), unique=True),
        sa.Column('created_at', sa.DateTime, default=datetime.now)
    )

def downgrade():
    op.drop_table('users')
```

### Phase 3: 데이터 마이그레이션
```python
# 기존 데이터 변환
def upgrade():
    # 예: 투자 의견 코드 변경
    op.execute("""
        UPDATE analysis
        SET investment_opinion = 'STRONG_BUY'
        WHERE investment_opinion = 'VERY_POSITIVE'
    """)
```

---

## 🗑️ 데이터 보관 정책

### 삭제 정책
```sql
-- 3개월 이상 된 가격 데이터는 월별로 압축
-- 1년 이상 된 트리거 데이터는 아카이브
-- 만료된 분석 자동 삭제 (TTL)
```

### 아카이브 전략
```python
# 매월 1일 실행
def archive_old_data():
    # 1년 이상 된 데이터 → archive_db로 이동
    cutoff_date = datetime.now() - timedelta(days=365)

    # triggers 아카이브
    archived = db.execute("""
        INSERT INTO archive_db.triggers
        SELECT * FROM triggers
        WHERE date < :cutoff_date
    """, {"cutoff_date": cutoff_date})

    # 원본 삭제
    db.execute("""
        DELETE FROM triggers
        WHERE date < :cutoff_date
    """, {"cutoff_date": cutoff_date})
```

---

## 📊 성능 최적화

### 1. 파티셔닝
```sql
-- 날짜별 파티션 (PostgreSQL)
CREATE TABLE price_history (
    ...
) PARTITION BY RANGE (date);

CREATE TABLE price_history_2025_11 PARTITION OF price_history
FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### 2. 뷰 (View)
```sql
-- 자주 사용하는 쿼리를 뷰로 생성
CREATE VIEW v_latest_analysis AS
SELECT
    a.ticker,
    s.name,
    a.investment_opinion,
    a.target_price,
    a.current_price,
    a.upside_potential,
    a.created_at
FROM analysis a
JOIN stocks s ON a.ticker = s.ticker
WHERE a.date = (
    SELECT MAX(date)
    FROM analysis
    WHERE ticker = a.ticker
);
```

### 3. 쿼리 최적화
```sql
-- EXPLAIN ANALYZE로 쿼리 계획 확인
EXPLAIN ANALYZE
SELECT * FROM triggers
WHERE date = '2025-11-06'
  AND session = 'morning';

-- 결과:
-- Index Scan on idx_date_session (cost=0.42..8.44 rows=1)
```

---

## 🔒 보안

### 1. SQL Injection 방지
```python
# ❌ 나쁜 예
query = f"SELECT * FROM stocks WHERE ticker = '{ticker}'"

# ✅ 좋은 예 (Parameterized Query)
query = "SELECT * FROM stocks WHERE ticker = ?"
db.execute(query, (ticker,))
```

### 2. 민감 데이터 암호화
```python
# 사용자 정보는 암호화 저장 (Phase 2)
from cryptography.fernet import Fernet

def encrypt_email(email: str) -> bytes:
    key = os.getenv("ENCRYPTION_KEY")
    f = Fernet(key)
    return f.encrypt(email.encode())
```

---

## 📚 참고 자료

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Database Indexing Strategies](https://use-the-index-luke.com/)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
