# MCP 서버 통합 (MCP Integration)

## 📌 문서 목적

MCP (Model Context Protocol) 서버를 활용한 데이터 소스 확장 및 통합 방법을 설명합니다.

**참고**: MCP 통합은 **Phase 2 확장 기능**으로, 프로토타입에서는 선택사항입니다.

---

## 🔌 사용 가능한 MCP 서버

### 1. kospi_kosdaq (KRX 데이터)

**용도**: pykrx 대체, 한국거래소 데이터 제공

**제공 기능**:
- KOSPI/KOSDAQ 시세 조회
- OHLCV 데이터
- 시가총액, 거래대금
- 외국인/기관 매매 동향

**설정**:
```json
// .claude/mcp_servers.json
{
  "kospi_kosdaq": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-kospi-kosdaq"]
  }
}
```

**사용 예시**:
```python
# MCP를 통한 시세 조회
from mcp_client import MCPClient

async def fetch_price_from_mcp(ticker: str) -> float:
    """
    MCP 서버를 통한 주가 조회
    """
    client = MCPClient("kospi_kosdaq")

    result = await client.call_tool(
        "get_stock_price",
        {"ticker": ticker}
    )

    return result['price']
```

---

### 2. firecrawl (웹 크롤링 전문)

**용도**: 뉴스, 증권사 리서치, 토론실 크롤링

**제공 기능**:
- JavaScript 렌더링
- 동적 페이지 크롤링
- HTML to Markdown 변환
- 스크린샷 캡처

**설정**:
```json
{
  "firecrawl": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-firecrawl"],
    "env": {
      "FIRECRAWL_API_KEY": "your_api_key_here"
    }
  }
}
```

**사용 예시**:
```python
async def crawl_naver_news(ticker: str) -> List[Dict]:
    """
    네이버 금융 뉴스 크롤링 (MCP firecrawl 사용)
    """
    client = MCPClient("firecrawl")

    url = f"https://finance.naver.com/item/news.naver?code={ticker}"

    result = await client.call_tool(
        "crawl_page",
        {
            "url": url,
            "selector": ".news_list",
            "format": "markdown"
        }
    )

    return parse_news_markdown(result['content'])
```

---

### 3. perplexity (웹 검색 전문)

**용도**: 실시간 뉴스 검색, 최신 정보 조회

**제공 기능**:
- 웹 검색 + LLM 요약
- 실시간 뉴스 검색
- 출처 제공

**설정**:
```json
{
  "perplexity": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-perplexity"],
    "env": {
      "PERPLEXITY_API_KEY": "your_api_key_here"
    }
  }
}
```

**사용 예시**:
```python
async def search_latest_news(company_name: str) -> str:
    """
    Perplexity를 통한 최신 뉴스 검색
    """
    client = MCPClient("perplexity")

    result = await client.call_tool(
        "search",
        {
            "query": f"{company_name} 최근 뉴스",
            "max_results": 10
        }
    )

    return result['summary']
```

---

### 4. sqlite (내부 DB)

**용도**: 매매 시뮬레이션 내역, 평가 데이터 저장

**제공 기능**:
- SQL 쿼리 실행
- 트랜잭션 관리
- 백업/복원

**설정**:
```json
{
  "sqlite": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-sqlite", "./data/simulation.db"]
  }
}
```

**사용 예시**:
```python
async def save_backtest_result(result: Dict):
    """
    백테스트 결과 저장
    """
    client = MCPClient("sqlite")

    await client.call_tool(
        "execute",
        {
            "query": """
                INSERT INTO backtest_results (
                    strategy, ticker, entry_price, exit_price, profit
                ) VALUES (?, ?, ?, ?, ?)
            """,
            "params": [
                result['strategy'],
                result['ticker'],
                result['entry_price'],
                result['exit_price'],
                result['profit']
            ]
        }
    )
```

---

### 5. time (시간 관리)

**용도**: 시간대 변환, 영업일 계산

**제공 기능**:
- 현재 시간 조회
- 시간대 변환
- 영업일 계산 (휴장일 제외)

**설정**:
```json
{
  "time": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-time"]
  }
}
```

**사용 예시**:
```python
async def get_previous_trading_day() -> datetime:
    """
    전일 영업일 조회 (휴장일 제외)
    """
    client = MCPClient("time")

    result = await client.call_tool(
        "get_previous_business_day",
        {
            "timezone": "Asia/Seoul",
            "market": "KRX"
        }
    )

    return datetime.fromisoformat(result['date'])
```

---

## 🔧 MCP 클라이언트 구현

### 1. 기본 클라이언트

```python
# backend/app/services/mcp_client.py

import httpx
import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP 서버 통합 클라이언트
    """

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.base_url = self._get_server_url(server_name)

    def _get_server_url(self, server_name: str) -> str:
        """
        MCP 서버 URL 조회
        """
        # .claude/mcp_servers.json에서 읽기
        import json

        with open(".claude/mcp_servers.json", "r") as f:
            config = json.load(f)

        # 로컬 MCP 서버는 기본적으로 http://localhost:3000
        return f"http://localhost:3000/{server_name}"

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        MCP 도구 호출

        Args:
            tool_name: 도구 이름
            params: 파라미터

        Returns:
            도구 실행 결과
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/tools/{tool_name}",
                    json=params,
                    timeout=30.0
                )

                response.raise_for_status()

                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"MCP tool call failed: {e}")
                raise

            except Exception as e:
                logger.error(f"Unexpected MCP error: {e}")
                raise
```

### 2. Fallback 통합

```python
# backend/app/services/data_service.py

class DataService:
    """
    데이터 수집 서비스 (MCP Fallback 포함)
    """

    def __init__(self, use_mcp: bool = False):
        self.use_mcp = use_mcp
        self.mcp_client = MCPClient("kospi_kosdaq") if use_mcp else None

    async def get_stock_price(self, ticker: str) -> float:
        """
        주가 조회 (pykrx 우선, 실패 시 MCP)
        """
        # 1차: pykrx
        try:
            from pykrx import stock
            from datetime import datetime

            today = datetime.now().strftime("%Y%m%d")
            df = stock.get_market_ohlcv_by_ticker(today)

            if ticker in df.index:
                return df.loc[ticker, '종가']

        except Exception as e:
            logger.warning(f"pykrx failed: {e}")

        # 2차: MCP 서버 (설정된 경우)
        if self.use_mcp and self.mcp_client:
            try:
                result = await self.mcp_client.call_tool(
                    "get_stock_price",
                    {"ticker": ticker}
                )
                return result['price']

            except Exception as e:
                logger.error(f"MCP also failed: {e}")

        raise DataCollectionError(f"Unable to fetch price for {ticker}")
```

---

## 📊 통합 예시

### 1. 뉴스 수집 통합

```python
async def collect_news(ticker: str, use_mcp: bool = False) -> List[Dict]:
    """
    뉴스 수집 (크롤링 vs MCP)
    """
    if use_mcp:
        # MCP firecrawl 사용
        client = MCPClient("firecrawl")
        result = await client.call_tool(
            "crawl_page",
            {
                "url": f"https://finance.naver.com/item/news.naver?code={ticker}",
                "selector": ".news_list"
            }
        )
        return parse_news(result['content'])
    else:
        # 직접 크롤링 (BeautifulSoup)
        return await crawl_naver_news_direct(ticker)
```

### 2. 리서치 보고서 수집

```python
async def collect_analyst_reports(ticker: str) -> List[Dict]:
    """
    증권사 리서치 보고서 수집 (MCP 활용)
    """
    client = MCPClient("firecrawl")

    # 여러 증권사 리서치 사이트 크롤링
    sources = [
        f"https://securities.nhqv.com/research/{ticker}",
        f"https://www.truefriend.com/main/research/{ticker}",
        # ...
    ]

    reports = []

    for url in sources:
        try:
            result = await client.call_tool(
                "crawl_page",
                {
                    "url": url,
                    "format": "markdown",
                    "wait_for": ".report-content"
                }
            )

            reports.append({
                "source": url,
                "content": result['content'],
                "date": result['metadata']['date']
            })

        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")
            continue

    return reports
```

### 3. 실시간 검색 통합

```python
async def analyze_company_with_mcp(ticker: str) -> Dict:
    """
    MCP 서버를 활용한 기업 분석
    """
    # 1. Perplexity로 최신 뉴스 검색
    search_client = MCPClient("perplexity")
    news_summary = await search_client.call_tool(
        "search",
        {
            "query": f"{ticker} 최근 이슈",
            "max_results": 10
        }
    )

    # 2. Firecrawl로 재무제표 크롤링
    crawl_client = MCPClient("firecrawl")
    financial_data = await crawl_client.call_tool(
        "crawl_page",
        {
            "url": f"https://finance.naver.com/item/main.naver?code={ticker}",
            "selector": ".corp_group1"
        }
    )

    # 3. LLM으로 종합 분석
    analysis = await llm_service.analyze_company({
        "ticker": ticker,
        "news": news_summary['summary'],
        "financial": financial_data['content']
    })

    return analysis
```

---

## ⚙️ 설정 및 초기화

### 1. 환경 변수

```bash
# .env

# MCP 서버 활성화 여부
USE_MCP=false

# MCP API 키
FIRECRAWL_API_KEY=your_firecrawl_key
PERPLEXITY_API_KEY=your_perplexity_key

# MCP 서버 URL (커스텀 호스팅 시)
MCP_KOSPI_URL=http://localhost:3000/kospi_kosdaq
MCP_FIRECRAWL_URL=http://localhost:3001/firecrawl
```

### 2. 서비스 초기화

```python
# backend/app/main.py

from app.services.mcp_client import MCPClient
from app.core.config import settings

async def init_mcp_services():
    """
    MCP 서버 초기화
    """
    if settings.USE_MCP:
        logger.info("Initializing MCP services...")

        # 서버 연결 확인
        try:
            client = MCPClient("kospi_kosdaq")
            await client.call_tool("ping", {})
            logger.info("MCP kospi_kosdaq server connected")
        except Exception as e:
            logger.warning(f"MCP kospi_kosdaq server not available: {e}")

        # 다른 서버들도 체크...
```

---

## 🔍 장단점 비교

### pykrx vs MCP kospi_kosdaq

| 구분 | pykrx | MCP |
|-----|-------|-----|
| **비용** | 무료 | 무료 |
| **데이터 범위** | OHLCV, 시가총액, 거래량 | 동일 + 추가 데이터 |
| **안정성** | 높음 (공식 KRX 데이터) | 중간 (서버 의존) |
| **속도** | 빠름 (직접 호출) | 중간 (HTTP 오버헤드) |
| **설정 복잡도** | 낮음 | 중간 |

**결론**: **프로토타입에서는 pykrx 사용 권장**, Phase 2에서 MCP 추가

### 직접 크롤링 vs MCP firecrawl

| 구분 | 직접 크롤링 (BeautifulSoup) | MCP firecrawl |
|-----|---------------------------|---------------|
| **비용** | 무료 | 유료 (API 키 필요) |
| **JavaScript 렌더링** | 불가능 (Selenium 필요) | 가능 |
| **복잡도** | 높음 (파싱 로직 직접 작성) | 낮음 (자동 변환) |
| **유지보수** | 높음 (사이트 구조 변경 시) | 낮음 |

**결론**: **간단한 정적 페이지는 직접 크롤링**, 복잡한 동적 페이지는 firecrawl

---

## ⚠️ 주의사항

### 1. API 비용

MCP 서버 중 일부는 유료 API를 사용합니다:
- **firecrawl**: 월 $X (트래픽 기준)
- **perplexity**: 쿼리당 $X

**대안**: 프로토타입에서는 무료 도구(pykrx, BeautifulSoup) 사용

### 2. 서버 관리

MCP 서버는 별도 프로세스로 실행되므로:
- 서버 다운 시 Fallback 로직 필수
- 헬스 체크 주기적 실행
- 에러 처리 철저히

### 3. 데이터 일관성

여러 소스에서 데이터 수집 시 일관성 주의:
- pykrx와 MCP 데이터 형식 차이
- 시간대 불일치 (UTC vs KST)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
