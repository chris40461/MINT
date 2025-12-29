"""
triggers.py API 엔드포인트 테스트

pytest backend/tests/test_triggers_api.py -v
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


class TestTriggersAPI:
    """triggers.py API 엔드포인트 테스트"""

    def test_run_trigger_morning(self):
        """POST /run/morning - 오전 트리거 수동 실행"""
        response = client.post("/api/v1/triggers/run/morning")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["session"] == "morning"
        assert "triggers_detected" in data["data"]
        assert "execution_time" in data["data"]
        assert "trigger_breakdown" in data["data"]

        # 오전 트리거는 3개 타입 (volume_surge, gap_up, fund_inflow)
        breakdown = data["data"]["trigger_breakdown"]
        expected_types = ["volume_surge", "gap_up", "fund_inflow"]
        for trigger_type in expected_types:
            assert trigger_type in breakdown

    def test_get_triggers_with_date(self):
        """GET / - 날짜별 트리거 조회"""
        # 먼저 오전 트리거 실행
        client.post("/api/v1/triggers/run/morning")

        # 오늘 날짜로 조회
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/triggers?date={today}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "triggers" in data["data"]
        assert "metadata" in data["data"]
        assert data["data"]["metadata"]["date"] == today

    def test_get_triggers_with_session_filter(self):
        """GET / - 세션 필터링 트리거 조회"""
        # 오전 트리거 실행
        client.post("/api/v1/triggers/run/morning")

        # 오전 세션으로 필터링
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/triggers?date={today}&session=morning")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["metadata"]["session"] == "morning"

        # 모든 트리거가 morning 세션인지 확인
        for trigger in data["data"]["triggers"]:
            assert trigger["session"] == "morning"

    def test_get_latest_triggers(self):
        """GET /latest - 최신 트리거 조회"""
        # 먼저 트리거 실행
        client.post("/api/v1/triggers/run/morning")

        response = client.get("/api/v1/triggers/latest")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "triggers" in data["data"]
        assert "metadata" in data["data"]

        # 메타데이터에 날짜와 세션 정보가 있어야 함
        assert "date" in data["data"]["metadata"]
        assert "session" in data["data"]["metadata"]
        assert "total" in data["data"]["metadata"]

    def test_get_triggers_by_type(self):
        """GET /types/{trigger_type} - 트리거 타입별 조회"""
        # 오전 트리거 실행
        client.post("/api/v1/triggers/run/morning")

        # volume_surge 타입만 조회
        today = datetime.now().strftime("%Y-%m-%d")
        response = client.get(f"/api/v1/triggers/types/volume_surge?date={today}&limit=3")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["trigger_type"] == "volume_surge"
        assert data["data"]["date"] == today
        assert len(data["data"]["triggers"]) <= 3

        # 모든 트리거가 volume_surge 타입인지 확인
        for trigger in data["data"]["triggers"]:
            assert trigger["trigger_type"] == "volume_surge"

    def test_get_trigger_history_for_stock(self):
        """GET /{ticker}/history - 종목별 트리거 히스토리"""
        # 오전 트리거 실행
        run_response = client.post("/api/v1/triggers/run/morning")
        run_data = run_response.json()

        # 첫 번째 종목의 ticker를 가져옴
        if run_data["data"]["triggers_detected"] > 0:
            # 오늘 날짜 트리거 조회
            today = datetime.now().strftime("%Y-%m-%d")
            triggers_response = client.get(f"/api/v1/triggers?date={today}")
            triggers_data = triggers_response.json()

            if len(triggers_data["data"]["triggers"]) > 0:
                test_ticker = triggers_data["data"]["triggers"][0]["ticker"]

                # 해당 종목의 히스토리 조회
                response = client.get(f"/api/v1/triggers/{test_ticker}/history?days=30")

                assert response.status_code == 200
                data = response.json()

                assert data["success"] is True
                assert data["data"]["ticker"] == test_ticker
                assert "period" in data["data"]
                assert "total_triggers" in data["data"]
                assert "trigger_breakdown" in data["data"]
                assert "triggers" in data["data"]

    def test_get_trigger_stats(self):
        """GET /stats - 트리거 통계 조회"""
        # 오전 트리거 실행
        client.post("/api/v1/triggers/run/morning")

        # 최근 30일 통계 조회
        response = client.get("/api/v1/triggers/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "period" in data["data"]
        assert "total_triggers" in data["data"]
        assert "daily_average" in data["data"]
        assert "by_type" in data["data"]
        assert "by_session" in data["data"]
        assert "top_frequent_stocks" in data["data"]

    def test_get_trigger_stats_with_date_range(self):
        """GET /stats - 날짜 범위 지정 통계 조회"""
        # 오전 트리거 실행
        client.post("/api/v1/triggers/run/morning")

        # 특정 기간 통계 조회
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        response = client.get(f"/api/v1/triggers/stats?start_date={start_date}&end_date={end_date}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["period"]["start"] == start_date
        assert data["data"]["period"]["end"] == end_date

    def test_run_trigger_afternoon(self):
        """POST /run/afternoon - 오후 트리거 수동 실행"""
        response = client.post("/api/v1/triggers/run/afternoon")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["session"] == "afternoon"

        # 오후 트리거는 3개 타입 (intraday_rise, closing_strength, sideways_volume)
        breakdown = data["data"]["trigger_breakdown"]
        expected_types = ["intraday_rise", "closing_strength", "sideways_volume"]
        for trigger_type in expected_types:
            assert trigger_type in breakdown

    def test_invalid_date_format(self):
        """잘못된 날짜 형식 테스트"""
        response = client.get("/api/v1/triggers?date=invalid-date")

        assert response.status_code == 400
        assert "잘못된 날짜 형식" in response.json()["detail"]


if __name__ == "__main__":
    # 단일 테스트 실행 예시
    pytest.main([__file__, "-v", "-s"])
