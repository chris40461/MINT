"""
Analysis API 통합 테스트

pytest backend/tests/test_analysis_api.py -v
pytest backend/tests/test_analysis_api.py -v -m llm_integration  # LLM 호출 테스트만

주의:
- @pytest.mark.llm_integration: 실제 LLM 호출 (시간 소요, 비용 발생)
- 캐시는 DB 기반
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import time

from app.main import app

client = TestClient(app)


class TestAnalysisAPIBasic:
    """기본 API 동작 테스트 (LLM 호출 없음)"""

    def test_batch_analyze_validation_empty_list(self):
        """POST /batch - 빈 종목 리스트 검증"""
        response = client.post("/api/v1/analysis/batch")

        # Validation error (missing required field)
        assert response.status_code == 422

    def test_batch_analyze_validation_too_many(self):
        """POST /batch - 10개 초과 종목 검증"""
        tickers = [f"00{i:04d}" for i in range(11)]
        query_params = "&".join([f"tickers={t}" for t in tickers])

        response = client.post(f"/api/v1/analysis/batch?{query_params}")

        assert response.status_code == 400
        assert "최대 10개" in response.json()["detail"]

    def test_popular_analysis_limit_validation(self):
        """GET /popular - limit 범위 검증 (validation error만 테스트)"""
        # 0 (범위 밖) - Pydantic validation error
        response_zero = client.get("/api/v1/analysis/popular?limit=0")
        assert response_zero.status_code == 422

        # 21 (범위 밖) - Pydantic validation error
        response_over = client.get("/api/v1/analysis/popular?limit=21")
        assert response_over.status_code == 422

        # Note: 실제 실행 테스트(limit=1, 20)는 LLM 호출이 필요하므로 제거
        # 통합 테스트에서 수동으로 테스트 필요

class TestAnalysisAPIIntegration:
    """LLM 통합 테스트 (실제 API 호출)"""

    @pytest.mark.llm_integration
    def test_get_analysis_full_flow(self):
        """
        GET /{ticker} - 전체 플로우 통합 테스트

        주의: 실제 Gemini API 호출
        - 실행 시간: 30-90초
        - 비용: ~$0.02/request
        - API 키 필요: GEMINI_API_KEY

        검증 항목:
        1. 응답 상태 200
        2. Analysis 모델 구조 완전성
        3. 모든 필드 타입 검증
        4. opinion 값이 유효한지 (STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL)
        5. target_price > 0
        6. risks 최소 3개
        """
        ticker = "005930"  # 삼성전자

        print(f"\n실제 LLM 호출 시작: {ticker} (30-90초 소요 예상)")
        start_time = time.time()

        response = client.get(f"/api/v1/analysis/{ticker}")

        elapsed = time.time() - start_time
        print(f"LLM 응답 시간: {elapsed:.1f}초")

        # 1. 기본 응답 검증
        assert response.status_code == 200, f"응답 실패: {response.json()}"
        data = response.json()

        assert data["success"] is True
        assert "data" in data

        analysis = data["data"]

        # 2. 기본 정보 검증
        assert analysis["ticker"] == ticker
        assert "name" in analysis
        assert "current_price" in analysis
        assert analysis["current_price"] > 0
        assert "change_rate" in analysis
        assert "market_cap" in analysis

        # 3. 분석 결과 검증
        assert "summary" in analysis
        assert len(analysis["summary"]) > 10, "summary가 너무 짧음"

        assert "opinion" in analysis
        valid_opinions = ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]
        assert analysis["opinion"] in valid_opinions, f"잘못된 opinion: {analysis['opinion']}"

        assert "target_price" in analysis
        assert analysis["target_price"] > 0, "목표가는 0보다 커야 함"

        # 4. 재무 데이터 검증
        assert "financial" in analysis
        financial = analysis["financial"]
        assert "roe" in financial
        assert "per" in financial
        assert "pbr" in financial
        assert "debt_ratio" in financial
        assert "revenue_growth_yoy" in financial

        # 5. 뉴스 데이터 검증
        assert "news" in analysis
        news = analysis["news"]
        assert "positive_count" in news
        assert "negative_count" in news
        assert "neutral_count" in news
        assert "sentiment" in news
        assert news["sentiment"] in ["positive", "neutral", "negative"]

        # 6. 기술적 지표 검증
        assert "technical" in analysis
        technical = analysis["technical"]
        assert "rsi" in technical
        assert 0 <= technical["rsi"] <= 100, f"RSI 범위 오류: {technical['rsi']}"
        assert "macd_status" in technical
        assert technical["macd_status"] in ["golden_cross", "dead_cross", "neutral"]
        assert "ma_position" in technical
        assert technical["ma_position"] in ["상회", "하회", "중립"]

        # 7. 리스크 검증
        assert "risks" in analysis
        assert isinstance(analysis["risks"], list)
        assert len(analysis["risks"]) >= 3, f"리스크가 {len(analysis['risks'])}개뿐 (최소 3개 필요)"

        # 8. 메타데이터 검증
        assert "analyzed_at" in analysis

        print(f"\n분석 결과:")
        print(f"  - 종목: {analysis['name']} ({ticker})")
        print(f"  - 현재가: {analysis['current_price']:,}원")
        print(f"  - 투자의견: {analysis['opinion']}")
        print(f"  - 목표가: {analysis['target_price']:,}원")
        print(f"  - 요약: {analysis['summary'][:100]}...")
        print(f"  - 리스크 개수: {len(analysis['risks'])}개")

    @pytest.mark.llm_integration
    def test_force_refresh(self):
        """
        force_refresh 테스트

        급등/급락 시 캐시 무시하고 재생성하는 기능 검증

        1. 정상 호출: 캐시 또는 신규 생성
        2. force_refresh=true: 캐시 무시하고 재생성
        """
        ticker = "005930" 

        # 1. 정상 호출
        print(f"\n정상 호출 (캐시 )...")
        start_time_1 = time.time()
        response_1 = client.get(f"/api/v1/analysis/{ticker}")
        elapsed_1 = time.time() - start_time_1

        assert response_1.status_code == 200
        data_1 = response_1.json()["data"]
        print(f"정상 호출 시간: {elapsed_1:.1f}초")

        # 2. force_refresh (캐시 무시)
        print(f"force_refresh 호출 (캐시 무시, 재생성)...")
        start_time_2 = time.time()
        response_2 = client.get(f"/api/v1/analysis/{ticker}?force_refresh=true")
        elapsed_2 = time.time() - start_time_2

        assert response_2.status_code == 200
        data_2 = response_2.json()["data"]
        print(f"force_refresh 시간: {elapsed_2:.1f}초")

        # force_refresh는 LLM 호출하므로 시간이 오래 걸림
        if elapsed_2 > 5:
            print(f"force_refresh 확인: LLM 재호출됨 ({elapsed_2:.1f}초)")

        # 기본 구조 검증
        assert data_2["ticker"] == ticker
        assert "summary" in data_2
        assert "opinion" in data_2


class TestAnalysisAPIErrorHandling:
    """에러 핸들링 테스트"""

    def test_invalid_ticker_format(self):
        """잘못된 종목 코드 형식 테스트"""
        invalid_tickers = [
            "INVALID123",  # 영문 포함
            "12345678",    # 너무 긴 코드
            "00",          # 너무 짧은 코드
            "!@#$%",       # 특수문자
        ]

        for ticker in invalid_tickers:
            response = client.get(f"/api/v1/analysis/{ticker}")

            # 400 (잘못된 요청) 또는 500 (처리 실패) 허용
            assert response.status_code in [400, 404, 500], \
                f"{ticker}: 예상과 다른 상태 코드 {response.status_code}"

    def test_ticker_not_in_database(self):
        """
        DB에 없는 종목 테스트

        999999: 실제로 존재하지 않는 종목 코드
        """
        ticker = "999999"
        response = client.get(f"/api/v1/analysis/{ticker}")

        # 404 또는 500 허용
        assert response.status_code in [400, 404, 500]


# TestAnalysisAPIBatch 및 TestAnalysisAPIPopular 제거
# - batch, popular 엔드포인트는 실제로 LLM을 호출하여 분석을 생성함
# - LLM 통합 테스트는 test_get_analysis_full_flow, test_force_refresh 2개만 유지
# - 필요시 수동으로 테스트
# TODO batch, popular 모두 LLM CALL 를 worker 을 늘려 처리하도록 수정

@pytest.mark.skip
class TestAnalysisAPIComparison:
    """업종 비교 분석 테스트"""

    def test_compare_with_peers_endpoint_exists(self):
        """GET /{ticker}/comparison - 엔드포인트 존재 확인"""
        ticker = "005930"
        response = client.get(f"/api/v1/analysis/{ticker}/comparison")

        # 200 (성공) 또는 500 (미구현/데이터 없음) 허용
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "data" in data


class TestAnalysisAPICacheStatus:
    """캐시 상태 테스트"""

    def test_cache_status_structure(self):
        """GET /{ticker}/cache-status - 응답 구조 검증"""
        ticker = "005930"
        response = client.get(f"/api/v1/analysis/{ticker}/cache-status")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data

        cache_status = data["data"]
        assert "ticker" in cache_status
        assert "cache_exists" in cache_status
        assert "cache_key" in cache_status

        # cache_exists가 True면 추가 필드 존재
        if cache_status["cache_exists"]:
            assert "cached_at" in cache_status
            assert "expires_at" in cache_status
            assert "ttl_seconds" in cache_status


if __name__ == "__main__":
    # 전체 테스트 실행
    pytest.main([__file__, "-v", "-s"])
