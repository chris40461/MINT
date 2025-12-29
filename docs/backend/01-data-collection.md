# 데이터 수집 (Data Collection)

## 📌 문서 목적

외부 데이터 소스로부터 주식 데이터를 수집하는 방법과 전략을 설명합니다.

---

## 🎯 데이터 소스

### 1. pykrx (주력)
- **제공**: OHLCV, 시가총액, 거래대금
- **장점**: 무료, 공식 데이터, 실시간
- **단점**: API 제약

### 2. DART API
- **제공**: 재무제표, 공시 정보
- **API 키**: 필요

### 3. 네이버 금융 (크롤링)
- **제공**: 뉴스, 토론실
- **주의**: robots.txt 준수

### 4. MCP 서버 (확장, Phase 2)
- **kospi_kosdaq**: KRX 데이터 대체
- **firecrawl**: 웹 크롤링 전문
- **perplexity**: 웹 검색

---

## 📊 pykrx 사용법

```python
from pykrx import stock
from datetime import datetime

# OHLCV 데이터
df = stock.get_market_ohlcv_by_ticker("20251106", market="ALL")

# 시가총액
cap_df = stock.get_market_cap_by_ticker("20251106", market="ALL")

# 외국인/기관 순매수
foreign_df = stock.get_market_net_purchases_of_equities_by_ticker(
    "20251101", "20251106", "005930", "FOREIGN"
)
```

---

## 🔄 재시도 로직

```python
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_market_snapshot(date: datetime) -> pd.DataFrame:
    """
    재시도 로직이 포함된 데이터 수집
    """
    try:
        df = stock.get_market_ohlcv_by_ticker(
            date.strftime("%Y%m%d"),
            market="ALL"
        )
        return df
    except Exception as e:
        logger.error(f"Data collection failed: {e}")
        raise
```

---

**마지막 업데이트**: 2025-11-06
