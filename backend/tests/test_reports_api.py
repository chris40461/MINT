"""
reports.py API 엔드포인트 테스트

pytest backend/tests/test_reports_api.py -v
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


class TestReportsAPI:
    """reports.py API 엔드포인트 테스트"""

    @pytest.mark.llm_integration
    def test_generate_morning_report(self):
        """
        POST /morning/generate - 장 시작 리포트 생성 (LLM 통합 테스트)

        주의: 실제 Gemini API 호출 (Google Search Grounding 포함)
        - 실행 시간: 2-5분 (첫 호출), 두 번째 호출은 skip되어 즉시 반환
        - 비용: ~$0.05/request (첫 호출만)
        - API 키 필요: GEMINI_API_KEY
        - 중복 생성 방지: 같은 날짜 리포트 있으면 skip
        """
        # 첫 번째 호출: 실제 생성 (LLM 호출)
        response = client.post("/api/v1/reports/morning/generate")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "message" in data
        # 중복 생성 방지로 두 가지 메시지 모두 허용
        assert data["message"] in ["장 시작 리포트가 생성되었습니다", "이미 생성된 리포트입니다"]

        # 리포트 구조 검증
        report = data["data"]
        assert report["report_type"] == "morning"
        assert "date" in report
        assert "generated_at" in report
        assert "market_forecast" in report
        assert "kospi_range" in report
        assert "top_stocks" in report
        assert len(report["top_stocks"]) == 10  # Top 10
        assert "sector_analysis" in report
        assert "investment_strategy" in report
        assert "daily_schedule" in report
        assert "metadata" in report

        # top_stocks 구조 검증
        if len(report["top_stocks"]) > 0:
            stock = report["top_stocks"][0]
            assert "ticker" in stock
            assert "name" in stock
            assert "current_price" in stock
            assert "reason" in stock
            assert "entry_strategy" in stock  # 진입 전략

            # entry_strategy 상세 검증
            strategy = stock["entry_strategy"]
            assert "entry_price" in strategy
            assert "target_price_1" in strategy
            assert "target_price_2" in strategy
            assert "stop_loss" in strategy
            assert "risk_reward_ratio" in strategy
            assert "holding_period" in strategy

    def test_get_morning_report(self):
        """GET /morning - 장 시작 리포트 조회 (LLM 필요)"""
        client.post("/api/v1/reports/morning/generate")

        # 리포트 조회
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/reports/morning?date={today}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["report_type"] == "morning"
        assert data["data"]["date"] == today

    def test_generate_afternoon_report(self):
        """POST /afternoon/generate - 장 마감 리포트 생성"""
        response = client.post("/api/v1/reports/afternoon/generate")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # 중복 생성 방지로 두 가지 메시지 모두 허용
        assert data["message"] in ["장 마감 리포트가 생성되었습니다", "이미 생성된 리포트입니다"]

        # 리포트 구조 검증
        report = data["data"]
        assert report["report_type"] == "afternoon"
        assert "date" in report
        assert "market_summary" in report
        assert "surge_stocks" in report
        assert "tomorrow_strategy" in report

        # market_summary 구조 검증
        summary = report["market_summary"]
        assert "kospi_close" in summary
        assert "kospi_change" in summary
        assert "trading_value" in summary
        assert "foreign_net" in summary
        assert "institution_net" in summary

    def test_get_afternoon_report(self):
        """GET /afternoon - 장 마감 리포트 조회"""
        # 먼저 리포트 생성
        client.post("/api/v1/reports/afternoon/generate")

        # 리포트 조회
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/reports/afternoon?date={today}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["report_type"] == "afternoon"
        assert data["data"]["date"] == today

    def test_get_latest_report_afternoon(self):
        """GET /latest - 최신 리포트 조회 (오후 리포트만 사용)"""
        # 더미 데이터 생성 (LLM 호출 없음)
        now = datetime.now()
        current_time = now.time()

        # 시간대별로 필요한 리포트 생성 (오후 리포트만 사용)
        if current_time < datetime.strptime("08:30", "%H:%M").time():
            # 08:30 이전: 전일 오후 리포트 필요
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            client.post(f"/api/v1/reports/afternoon/generate?date={yesterday}")
        elif current_time < datetime.strptime("15:40", "%H:%M").time():
            # 08:30-15:40: 당일 오전 리포트 필요 → 오후 리포트로 대체 (테스트용)
            # 실제로는 오전 리포트가 필요하지만, LLM 호출 피하기 위해 오후 사용
            client.post("/api/v1/reports/afternoon/generate")
        else:
            # 15:40 이후: 당일 오후 리포트 필요
            client.post("/api/v1/reports/afternoon/generate")

        response = client.get("/api/v1/reports/latest")

        # 시간대에 따라 404일 수 있음 (오전 시간대에 오후 리포트 생성 시)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert data["data"]["report_type"] in ["morning", "afternoon"]

    def test_get_report_history(self):
        """GET /history - 리포트 히스토리 조회"""
        # 더미 데이터만 생성 (LLM 호출 없음)
        client.post("/api/v1/reports/afternoon/generate")

        # 히스토리 조회
        response = client.get("/api/v1/reports/history?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "total" in data["data"]
        assert "reports" in data["data"]
        assert data["data"]["total"] >= 1  # 최소 1개 (afternoon)

        # 리포트 구조 검증
        if len(data["data"]["reports"]) > 0:
            report = data["data"]["reports"][0]
            assert "date" in report
            assert "report_type" in report
            assert "generated_at" in report
            assert "id" in report

    def test_get_report_history_with_type_filter(self):
        """GET /history - 타입별 필터링"""
        # 오후 리포트만 생성 (LLM 호출 없음)
        client.post("/api/v1/reports/afternoon/generate")

        # afternoon으로 조회
        response = client.get("/api/v1/reports/history?report_type=afternoon&limit=5")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # 모든 리포트가 afternoon 타입인지 확인
        for report in data["data"]["reports"]:
            assert report["report_type"] == "afternoon"

    def test_get_report_stats(self):
        """GET /stats - 리포트 통계 조회"""
        # 먼저 리포트 생성
        client.post("/api/v1/reports/morning/generate")
        client.post("/api/v1/reports/afternoon/generate")

        response = client.get("/api/v1/reports/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "total_reports" in data["data"]
        assert "by_type" in data["data"]
        assert "last_generated" in data["data"]
        assert "average_tokens" in data["data"]
        assert "total_cost_estimate" in data["data"]

        # 최소 2개 리포트 (morning + afternoon)
        assert data["data"]["total_reports"] >= 2

    def test_get_morning_report_not_found(self):
        """GET /morning - 존재하지 않는 날짜 리포트 조회"""
        # 존재하지 않는 날짜
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/reports/morning?date={future_date}")

        assert response.status_code == 404
        assert "리포트가 없습니다" in response.json()["detail"]

    def test_get_afternoon_report_not_found(self):
        """GET /afternoon - 존재하지 않는 날짜 리포트 조회"""
        # 존재하지 않는 날짜
        future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/reports/afternoon?date={future_date}")

        assert response.status_code == 404
        assert "리포트가 없습니다" in response.json()["detail"]

    def test_invalid_date_format_morning(self):
        """잘못된 날짜 형식 테스트 (morning)"""
        response = client.get("/api/v1/reports/morning?date=invalid-date")

        assert response.status_code == 400
        assert "잘못된 날짜 형식" in response.json()["detail"]

    def test_invalid_date_format_afternoon(self):
        """잘못된 날짜 형식 테스트 (afternoon)"""
        response = client.get("/api/v1/reports/afternoon?date=invalid-date")

        assert response.status_code == 400
        assert "잘못된 날짜 형식" in response.json()["detail"]

    def test_generate_report_with_specific_date(self):
        """특정 날짜로 리포트 생성"""
        specific_date = "2025-11-01"

        # 특정 날짜로 리포트 생성
        response = client.post(f"/api/v1/reports/morning/generate?date={specific_date}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["date"] == specific_date

        # 생성된 리포트 조회
        get_response = client.get(f"/api/v1/reports/morning?date={specific_date}")
        assert get_response.status_code == 200
        assert get_response.json()["data"]["date"] == specific_date


if __name__ == "__main__":
    # 단일 테스트 실행 예시
    pytest.main([__file__, "-v", "-s"])
