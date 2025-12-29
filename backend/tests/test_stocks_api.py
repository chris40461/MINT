"""
stocks.py API 엔드포인트 테스트

pytest backend/tests/test_stocks_api.py -v
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app

client = TestClient(app)


class TestStocksAPI:
    """stocks.py API 엔드포인트 테스트"""

    def test_get_stock_info(self):
        """GET /{ticker} - 종목 기본 정보 조회"""
        # 삼성전자 조회
        response = client.get("/api/v1/stocks/005930")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["ticker"] == "005930"
        assert "name" in data["data"]  # name이 ticker일 수도 있음 (DB 미조회 시)
        assert len(data["data"]["name"]) > 0
        assert data["data"]["market"] in ["KOSPI", "KOSDAQ"]
        # market_cap은 0일 수도 있음 (거래일이 아닐 때)
        assert data["data"]["market_cap"] >= 0

    def test_get_stock_info_not_found(self):
        """GET /{ticker} - 존재하지 않는 종목"""
        response = client.get("/api/v1/stocks/999999")

        assert response.status_code == 404

    def test_get_price_history_with_period(self):
        """GET /{ticker}/price - 가격 히스토리 (period 파라미터)"""
        response = client.get("/api/v1/stocks/005930/price?period=30")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["ticker"] == "005930"
        assert "period" in data["data"]
        assert "prices" in data["data"]
        assert len(data["data"]["prices"]) > 0

        # 첫 번째 가격 데이터 검증
        price = data["data"]["prices"][0]
        assert "date" in price
        assert "open" in price
        assert "high" in price
        assert "low" in price
        assert "close" in price
        assert "volume" in price
        assert "trading_value" in price

    def test_get_price_history_with_dates(self):
        """GET /{ticker}/price - 가격 히스토리 (start_date, end_date)"""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        response = client.get(
            f"/api/v1/stocks/005930/price?start_date={start_date}&end_date={end_date}"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["period"]["start"] == start_date
        assert data["data"]["period"]["end"] == end_date

    def test_get_current_price(self):
        """GET /{ticker}/current - 현재가 조회"""
        response = client.get("/api/v1/stocks/005930/current")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["ticker"] == "005930"
        assert data["data"]["name"] == "삼성전자"
        assert "current_price" in data["data"]
        assert "change_rate" in data["data"]
        assert "volume" in data["data"]
        assert "trading_value" in data["data"]
        assert "timestamp" in data["data"]

    def test_search_stocks_with_keyword(self):
        """GET / - 종목 검색 (키워드)"""
        response = client.get("/api/v1/stocks?keyword=삼성&limit=5")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "total" in data["data"]
        assert "stocks" in data["data"]
        assert len(data["data"]["stocks"]) <= 5

        # 모든 종목명에 "삼성" 포함 확인
        for stock in data["data"]["stocks"]:
            assert "삼성" in stock["name"] or "005930" in stock["ticker"]

    def test_search_stocks_with_market(self):
        """GET / - 종목 검색 (시장 필터)"""
        response = client.get("/api/v1/stocks?market=KOSPI&limit=10")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

        # 모든 종목이 KOSPI인지 확인
        for stock in data["data"]["stocks"]:
            assert stock["market"] == "KOSPI"

    def test_search_stocks_no_filter(self):
        """GET / - 종목 검색 (필터 없음)"""
        response = client.get("/api/v1/stocks?limit=20")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]["stocks"]) <= 20

    def test_get_technical_indicators(self):
        """GET /{ticker}/technical - 기술적 지표 조회"""
        response = client.get("/api/v1/stocks/005930/technical")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["ticker"] == "005930"
        assert "date" in data["data"]
        assert "rsi" in data["data"]
        assert "macd" in data["data"]
        assert "macd_signal" in data["data"]
        assert "macd_status" in data["data"]
        assert "ma5" in data["data"]
        assert "ma20" in data["data"]
        assert "ma60" in data["data"]
        assert "ma_position" in data["data"]

        # RSI는 0-100 범위
        assert 0 <= data["data"]["rsi"] <= 100

    def test_get_technical_indicators_with_date(self):
        """GET /{ticker}/technical - 기술적 지표 (특정 날짜)"""
        target_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

        response = client.get(f"/api/v1/stocks/005930/technical?date={target_date}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["date"] == target_date


if __name__ == "__main__":
    # 단일 테스트 실행 예시
    pytest.main([__file__, "-v", "-s"])
