# MINT Backend Dockerfile
# Python 3.12 기반 경량 이미지

FROM python:3.12-slim

# 메타데이터
LABEL maintainer="Taewon"
LABEL description="MINT - 한국 주식 컨설팅 플랫폼 Backend"

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (C 컴파일러 등 - pandas, numpy, lxml 빌드용)
# Playwright 브라우저 실행을 위한 추가 패키지 포함
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    tzdata \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch==2.6.0+cpu torchvision==0.21.0+cpu torchaudio==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Playwright 브라우저 설치 (Chromium만 설치)
RUN playwright install chromium && \
    playwright install-deps chromium

# 애플리케이션 코드 복사
COPY app/ ./backend/app/
COPY scripts/ ./backend/scripts/
COPY .env .env

# 데이터 디렉토리 생성
RUN mkdir -p /app/data/logs

# 포트 노출
EXPOSE 8000

# 환경 변수 설정
ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Seoul

# 헬스체크 (httpx 사용)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import httpx; httpx.get('http://localhost:8000/health', timeout=5)" || exit 1

# 서버 실행
CMD ["python3", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio"]
