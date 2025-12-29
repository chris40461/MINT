# 시스템 아키텍처 개요

## 📌 문서 목적

MINT의 전체 시스템 아키텍처를 이해하고, 각 레이어의 역할과 기술 스택 선정 이유를 설명합니다.

---

## 🏗️ 전체 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│                      (Web Browser / Mobile)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↕ HTTPS
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend Layer (React)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │   Analysis   │  │   Reports    │          │
│  │  Component   │  │  Component   │  │  Component   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           React Query (State Management)              │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              ↕ REST API
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Layer (FastAPI)                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                  API Gateway (v1)                     │       │
│  │  /triggers  /analysis  /reports  /evaluation         │       │
│  └──────────────────────────────────────────────────────┘       │
│                              ↕                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Trigger    │  │     LLM     │  │   Cache     │             │
│  │  Service    │  │   Service   │  │  Service    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Data      │  │  Analysis   │  │  Scheduler  │             │
│  │  Service    │  │   Service   │  │   Service   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌─────────────────────────────────────────────────────┐        │
│  │            Utils (Metrics, Filters, Scoring)         │        │
│  └─────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Redis     │  │  SQLite /   │  │   Gemini    │             │
│  │   (Cache)   │  │  Postgres   │  │  2.5 Pro    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   pykrx     │  │  DART API   │  │  Naver Fin  │             │
│  │  (KRX 데이터) │  │  (공시정보)  │  │ (뉴스/차트)  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  ┌──────────────────────────────────────────────┐               │
│  │  MCP 서버 (확장, Phase 2)                     │               │
│  │  - kospi_kosdaq (KRX)                        │               │
│  │  - firecrawl (웹 크롤링)                      │               │
│  │  - perplexity (웹 검색)                       │               │
│  │  - sqlite (내부 DB)                          │               │
│  │  - time (시간)                               │               │
│  └──────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 레이어별 역할

### 1. Client Layer
**역할**: 사용자 인터페이스 제공
- 웹 브라우저를 통한 접근
- 반응형 디자인 (데스크톱, 모바일)
- HTTPS 보안 통신

### 2. Frontend Layer (React + TypeScript)
**역할**: 사용자 경험 및 데이터 시각화

**주요 컴포넌트**:
- **Dashboard**: 급등주 목록, 실시간 업데이트
- **Analysis**: 기업 분석 결과 표시
- **Reports**: 장 시작/마감 리포트

**상태 관리**:
- React Query: 서버 상태 관리, 캐싱
- useState/useContext: 로컬 상태

**기술 스택**:
- React 18
- TypeScript
- TailwindCSS (스타일링)
- Recharts (차트)
- Axios (HTTP 클라이언트)

### 3. Backend Layer (FastAPI + Python)
**역할**: 비즈니스 로직 및 데이터 처리

**API Gateway**:
- REST API 엔드포인트 제공
- 요청 검증
- 에러 핸들링
- Rate Limiting

**핵심 서비스**:

#### Trigger Service (급등주 감지)
- 6개 트리거 알고리즘 실행
- Rule-based 필터링
- 복합 점수 계산
- Top N 선정

#### LLM Service (Gemini 통합)
- Gemini 2.5 Pro API 호출
- 프롬프트 관리
- 토큰 최적화
- Rate Limiting

#### Data Service (데이터 수집)
- pykrx를 통한 KRX 데이터 수집
- DART API 공시 정보
- 네이버 금융 크롤링
- 데이터 검증 및 정제

#### Analysis Service (기업 분석)
- 재무 데이터 분석
- 뉴스 센티먼트 분석
- 기술적 지표 계산
- LLM 기반 종합 분석

#### Cache Service (캐싱)
- Redis 캐시 관리
- 캐시 키 생성
- TTL 관리
- 캐시 무효화

#### Scheduler Service (배치 작업)
- APScheduler 관리
- 오전/오후 트리거 실행
- 장 시작/마감 리포트 생성
- 에러 복구

**기술 스택**:
- FastAPI
- Python 3.10+
- pykrx (주식 데이터)
- google-generativeai (Gemini)
- Redis (캐싱)
- APScheduler (배치)

### 4. Data Layer
**역할**: 데이터 저장 및 관리

#### Redis (캐시)
- 기업 분석 캐싱 (TTL: 24시간)
- 급등주 목록 캐싱 (TTL: 1시간)
- 장 리포트 캐싱 (TTL: 12시간)

#### SQLite / PostgreSQL (DB)
- 종목 기본 정보
- 급등주 히스토리
- 분석 결과 저장
- 평가 데이터
- 사용자 피드백

#### Gemini 2.5 Pro (LLM)
- 기업 분석 생성
- 장 리포트 생성
- 급등주 상세 분석

### 5. External Data Sources
**역할**: 외부 데이터 제공

#### pykrx (주력 데이터 소스)
- OHLCV 데이터
- 시가총액
- 거래대금
- 외국인/기관 순매수

#### DART API
- 재무제표
- 공시 정보
- 사업 보고서

#### 네이버 금융
- 실시간 뉴스
- 토론실
- 차트 데이터

#### MCP 서버 (Phase 2 확장)
- kospi_kosdaq: KRX 데이터 대체
- firecrawl: 웹 크롤링 전문
- perplexity: 웹 검색 전문
- sqlite: 내부 DB 관리
- time: 시간 관리

---

## 🔧 기술 스택 선정 이유

### Frontend: React + TypeScript

**선정 이유**:
1. **생태계**: 풍부한 라이브러리 (차트, UI 컴포넌트)
2. **타입 안정성**: TypeScript로 런타임 에러 방지
3. **개발 속도**: 컴포넌트 재사용성
4. **커뮤니티**: 활발한 커뮤니티, 레퍼런스 풍부

**대안 고려**:
- Vue.js: 학습 곡선 낮지만 생태계가 작음
- Svelte: 성능 좋지만 라이브러리 부족

### Backend: FastAPI

**선정 이유**:
1. **성능**: 비동기 처리 (async/await)로 높은 성능
2. **타입 힌트**: Pydantic으로 자동 검증
3. **문서화**: 자동 Swagger/OpenAPI 문서 생성
4. **생산성**: 간결한 코드, 빠른 개발
5. **Python 생태계**: pandas, numpy, pykrx 등 활용

**대안 고려**:
- Django: 무겁고 복잡함
- Flask: 비동기 지원 약함
- Node.js: Python 데이터 라이브러리 활용 불가

### LLM: Gemini 2.5 Pro

**선정 이유**:
1. **비용 효율**: GPT-4 대비 저렴 (약 50%)
2. **성능**: 금융 도메인 성능 우수
3. **컨텍스트**: 긴 문맥 처리 가능
4. **API**: 안정적인 API 제공

**대안 고려**:
- GPT-4: 비용 높음
- Claude: API 제약 많음
- Llama: 자체 호스팅 복잡

### 데이터: pykrx

**선정 이유**:
1. **무료**: API 키 불필요
2. **공식**: KRX 공식 데이터
3. **간편**: Python 라이브러리
4. **실시간**: 장 중 데이터 수집 가능

**대안 고려**:
- 한국투자증권 API: API 키 필요, 제약 많음
- FinanceDataReader: 데이터 지연

### 캐시: Redis

**선정 이유**:
1. **속도**: 인메모리 DB
2. **TTL**: 자동 만료 지원
3. **데이터 구조**: 다양한 자료구조 지원
4. **안정성**: 검증된 솔루션

**대안 고려**:
- Memcached: 데이터 구조 제한적
- 로컬 캐시: 다중 인스턴스 시 동기화 문제

### DB: SQLite → PostgreSQL

**Phase 1 (프로토타입)**: SQLite
- 설치 불필요
- 파일 기반
- 간단한 설정

**Phase 2 (프로덕션)**: PostgreSQL
- 동시 접속 지원
- 복잡한 쿼리 최적화
- 트랜잭션 안정성

---

## 🔄 데이터 흐름 요약

### 1. 급등주 감지 흐름
```
Scheduler (09:10)
  → Data Service (pykrx 데이터 수집)
  → Trigger Service (6개 트리거 실행)
  → 필터링 & 점수화
  → DB 저장
  → Redis 캐싱 (TTL: 1h)
  → Frontend 자동 업데이트
```

### 2. 기업 분석 흐름
```
User Request (GET /analysis/005930)
  → Cache Service (Redis 조회)
  → [HIT] 캐시 반환
  → [MISS] Analysis Service 실행
    → Data Service (재무, 뉴스 수집)
    → LLM Service (Gemini 분석)
    → DB 저장
    → Redis 캐싱 (TTL: 24h)
  → Frontend 표시
```

### 3. 장 리포트 흐름
```
Scheduler (08:30 / 15:40)
  → Data Service (시장 데이터 수집)
  → Analysis Service (주목 종목 선정)
  → LLM Service (리포트 생성)
  → DB 저장
  → Redis 캐싱 (TTL: 12h)
  → Frontend 알림
```

---

## 📊 확장성 고려사항

### 수평 확장 (Horizontal Scaling)
- **Frontend**: CDN 배포 (Cloudflare, AWS CloudFront)
- **Backend**: 로드 밸런서 + 다중 인스턴스
- **Redis**: Redis Cluster
- **DB**: Read Replica

### 수직 확장 (Vertical Scaling)
- **Phase 1**: 단일 서버 (CPU 4코어, RAM 8GB)
- **Phase 2**: 서버 증설 (CPU 8코어, RAM 16GB)

### 캐싱 전략
- **L1**: 브라우저 캐시 (정적 리소스)
- **L2**: Redis 캐시 (API 응답)
- **L3**: DB 인덱스 (쿼리 최적화)

### 비용 최적화
- **LLM**: 캐싱으로 80% 절감
- **데이터**: 무료 pykrx 사용
- **인프라**: 초기 단일 서버

---

## 🔐 보안 고려사항

### API 보안
- **HTTPS**: TLS 1.3
- **CORS**: 허용 도메인 제한
- **Rate Limiting**: IP별 제한 (100 req/min)

### 데이터 보안
- **환경 변수**: API 키 .env 관리
- **DB**: SQL Injection 방지 (ORM 사용)
- **Redis**: 비밀번호 설정

### 법적 책임
- **면책 조항**: 투자 참고 자료일 뿐
- **데이터 저작권**: robots.txt 준수
- **개인정보**: 수집 최소화

---

## 📈 모니터링 및 로깅

### 로깅 전략
```python
# 로그 레벨
ERROR: 시스템 에러 (데이터 수집 실패, LLM API 실패)
WARNING: 경고 (캐시 미스, 느린 쿼리)
INFO: 정보 (트리거 실행, 리포트 생성)
DEBUG: 디버그 (상세 실행 로그)
```

### 모니터링 지표
- **시스템**: CPU, RAM, Disk 사용률
- **API**: 응답 시간, 에러율, 요청 수
- **LLM**: 토큰 사용량, 비용
- **캐시**: Hit Rate, 메모리 사용량

---

## 🚀 배포 전략

### Phase 1: 로컬 개발
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm start
```

### Phase 2: Docker 컨테이너
```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Phase 3: 클라우드 배포
- **Backend**: AWS EC2 / GCP Compute Engine
- **Frontend**: Vercel / Netlify
- **Redis**: AWS ElastiCache / GCP Memorystore
- **DB**: AWS RDS / GCP Cloud SQL

---

## 📚 참고 자료

### 공식 문서
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Gemini API](https://ai.google.dev/docs)
- [pykrx](https://github.com/sharebook-kr/pykrx)
- [Redis](https://redis.io/docs/)

### 아키텍처 패턴
- [12 Factor App](https://12factor.net/)
- [Microservices Pattern](https://microservices.io/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
