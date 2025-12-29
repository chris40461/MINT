# 🐳 MINT Docker 실행 가이드

## 📋 목차
- [빠른 시작](#빠른-시작)
- [개발 모드](#개발-모드)
- [프로덕션 배포](#프로덕션-배포)
- [트러블슈팅](#트러블슈팅)

---

## 🚀 빠른 시작

### 1️⃣ 사전 준비

**Docker 설치 확인**:
```bash
docker --version  # Docker version 20.10+
docker-compose --version  # docker-compose version 1.29+
```

**환경 변수 설정**:
```bash
# .env 파일이 있는지 확인
cat .env

# API 키가 설정되어 있는지 확인
grep GEMINI_API_KEY .env
grep DART_API_KEY .env
```

---

### 2️⃣ Docker로 서버 실행

#### **방법 A: Docker Compose (권장)**

```bash
# 프로젝트 루트에서 실행
cd /home/chris40461/MINT

# 이미지 빌드 및 컨테이너 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f backend

# 서버 상태 확인
curl http://localhost:8000/health
```

#### **방법 B: Docker 직접 실행**

```bash
# 1. 이미지 빌드
docker build -t mint-backend .

# 2. 컨테이너 실행
docker run -d \
  --name mint \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  mint-backend

# 3. 로그 확인
docker logs -f mint
```

---

### 3️⃣ 서버 접속

브라우저에서 다음 URL 접속:

- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/health
- **리포트 조회**: http://localhost:8000/api/v1/reports/latest

---

## 🛠️ 개발 모드

### Hot Reload 활성화

`docker-compose.yml` 파일에서 주석 해제:

```yaml
services:
  backend:
    volumes:
      - ./data:/app/data
      - ./backend:/app/backend  # ← 주석 해제
    environment:
      - ENVIRONMENT=development  # ← development로 변경
      - DEBUG=true
```

재시작:
```bash
docker-compose down
docker-compose up -d
```

---

## 🎯 주요 명령어

### 컨테이너 관리

```bash
# 서버 시작
docker-compose up -d

# 서버 중지
docker-compose down

# 서버 재시작
docker-compose restart

# 로그 확인 (실시간)
docker-compose logs -f backend

# 컨테이너 접속 (디버깅)
docker-compose exec backend bash
```

### 이미지 관리

```bash
# 이미지 재빌드 (코드 변경 후)
docker-compose build --no-cache

# 이미지 재빌드 + 재시작
docker-compose up -d --build

# 이미지 삭제
docker rmi mint-backend
```

### 데이터 관리

```bash
# DB 백업
docker-compose exec backend cp /app/data/mint.db /app/data/backup_$(date +%Y%m%d).db

# 로그 확인
docker-compose exec backend tail -f /app/data/logs/app.log

# 데이터 볼륨 삭제 (주의!)
docker-compose down -v
```

---

## 🏭 프로덕션 배포

### 1️⃣ 환경 변수 설정

```bash
# .env 파일 수정
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true

# 보안 강화
SECRET_KEY=your-production-secret-key-here
ALLOWED_ORIGINS=https://yourdomain.com
```

### 2️⃣ PostgreSQL 사용 (선택)

`docker-compose.yml`에서 PostgreSQL 주석 해제:

```yaml
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://skku:changeme@postgres:5432/mint
    depends_on:
      - postgres

  postgres:
    # 주석 해제
```

### 3️⃣ Nginx 리버스 프록시 (선택)

```nginx
# /etc/nginx/sites-available/mint
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🐛 트러블슈팅

### 문제 1: 컨테이너가 시작되지 않음

```bash
# 로그 확인
docker-compose logs backend

# 일반적인 원인:
# - .env 파일 누락 → cp .env.example .env
# - 포트 충돌 (8000) → lsof -ti:8000 | xargs kill -9
# - 권한 문제 → sudo docker-compose up -d
```

### 문제 2: 빌드 실패 (gcc, lxml)

```bash
# Dockerfile에 이미 libxml2-dev, libxslt1-dev 포함됨
# 만약 실패 시 로그 확인
docker-compose build --no-cache --progress=plain
```

### 문제 3: API 키 오류

```bash
# .env 파일 확인
docker-compose exec backend cat .env | grep API_KEY

# 환경 변수 재설정
docker-compose down
docker-compose up -d
```

### 문제 4: DB 파일 권한 오류

```bash
# 권한 수정
chmod 666 data/mint.db

# 또는 컨테이너 재생성
docker-compose down
docker-compose up -d
```

### 문제 5: 메모리 부족 (sentence-transformers)

```bash
# Docker Desktop 메모리 증가 (최소 4GB 권장)
# Settings → Resources → Memory → 4GB 이상

# 또는 경량 모델 사용
# backend/app/services/llm_company_analysis.py
# model_name = "paraphrase-multilingual-MiniLM-L12-v2"
```

---

## 📊 모니터링

### 헬스 체크

```bash
# API 헬스 체크
curl http://localhost:8000/health

# Docker 헬스 상태
docker ps --filter "name=mint"

# 리소스 사용량
docker stats mint-backend
```

### 로그 분석

```bash
# 최근 100줄
docker-compose logs --tail=100 backend

# 에러만 필터링
docker-compose logs backend | grep ERROR

# 특정 시간대
docker-compose logs --since "2025-11-16T10:00:00" backend
```

---

## 🔒 보안 체크리스트

- [ ] `.env` 파일을 `.gitignore`에 추가
- [ ] 프로덕션 `SECRET_KEY` 변경
- [ ] `DEBUG=false` 설정
- [ ] CORS `ALLOWED_ORIGINS` 제한
- [ ] PostgreSQL 비밀번호 변경 (사용 시)
- [ ] HTTPS 설정 (Nginx + Let's Encrypt)

---

## 📦 패키지 버전 정보

이 프로젝트는 **Python 3.12**와 호환되는 최신 버전을 사용합니다:

| 패키지 | 버전 | 비고 |
|-------|------|------|
| FastAPI | 0.115.6 | |
| Pydantic | 2.10.6 | |
| Pandas | 2.2.3 | Python 3.12 호환 |
| NumPy | 1.26.4 | 안정 버전 (2.x는 breaking changes) |
| SQLAlchemy | 2.0.44 | |
| google-genai | 1.50.1 | ⚠️ google-generativeai는 2025년 8월 EOL |
| sentence-transformers | 3.3.1 | 뉴스 중복 제거용 |
| **PyTorch** | **2.6.0+cpu** | **CPU-only (CUDA 제외로 6GB 절감), sentence-transformers 호환** |

---

## 📚 참고 자료

- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 가이드](https://docs.docker.com/compose/)
- [FastAPI 프로덕션 배포](https://fastapi.tiangolo.com/deployment/docker/)

---

**문제가 발생하면 GitHub Issues에 리포트해주세요!**
