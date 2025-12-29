# 🚀 SKKU-INSIGHT - 한국 주식 컨설팅 플랫폼

## 📌 프로젝트 개요

AI 기반 한국 주식 투자 컨설팅 플랫폼 (자동매매 X, 투자 의사결정 지원 O)

### 핵심 기능
- **급등주 포착**: Rule-based 6개 트리거 (오전 3개, 오후 3개)
- **장 시작/마감 리포트**: Gemini 2.5 기반 LLM 분석
- **기업 분석**: 재무/기술/뉴스 통합 분석

### 기술 스택
- **Backend**: FastAPI, Python 3.12, SQLite
- **Frontend**: React, TypeScript (구현 예정)
- **LLM**: Google Gemini 2.5 Flash
- **Data**: pykrx, DART API, Naver Finance

---

## 🛠️ 로컬 개발 환경 설정

### 1. Python 가상환경 (권장)

```bash
# 프로젝트 루트로 이동
cd /home/chris40461/SKKU-insight

# 의존성 설치
pip3 install -r backend/requirements.txt

# 환경 변수 설정
cp backend/.env.example backend/.env
# .env 파일 편집 (GEMINI_API_KEY, DART_API_KEY 설정)

# 서버 실행
python3 -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Docker (권장 - 프로덕션)

```bash
# Docker Compose 실행
docker-compose up -d --build

# 로그 확인
docker-compose logs -f backend

# 서버 중지
docker-compose down
```

자세한 내용은 [README-DOCKER.md](README-DOCKER.md) 참조

---

## 🎯 API 엔드포인트

- **API 문서**: http://localhost:8000/docs
- **헬스 체크**: http://localhost:8000/health
- **장 시작 리포트**: http://localhost:8000/api/v1/reports/morning
- **장 마감 리포트**: http://localhost:8000/api/v1/reports/afternoon
- **최신 리포트**: http://localhost:8000/api/v1/reports/latest

---

## 📁 디렉토리 구조

```
SKKU-insight/
├── backend/                # FastAPI 백엔드
│   ├── app/               # 애플리케이션 코드
│   ├── tests/             # 테스트
│   ├── requirements.txt   # Python 의존성
│   ├── .env               # 환경 변수 (gitignore)
│   ├── .env.example       # 환경 변수 템플릿
│   └── Dockerfile         # Docker 이미지
│
├── frontend/              # React 프론트엔드 (구현 예정)
│
├── data/                  # 데이터 저장
│   ├── skku_insight.db   # SQLite 데이터베이스
│   └── logs/             # 로그 파일
│
├── docs/                  # 문서
├── docker-compose.yml     # Docker Compose 설정
└── README-DOCKER.md       # Docker 가이드
```

---

## 🧪 테스트

```bash
cd backend
pytest tests/ -v
```

---

## 📚 문서

- [CLAUDE.md](.claude/CLAUDE.md): 전체 프로젝트 설계 문서
- [README-DOCKER.md](README-DOCKER.md): Docker 사용 가이드
- [docs/](docs/): 아키텍처 및 API 문서

---

## ⚠️ 주의사항

- 본 플랫폼은 **투자 참고 자료**일 뿐, 투자 권유가 아닙니다
- 모든 투자 결정은 사용자 본인의 책임입니다

---

**문의**: GitHub Issues
