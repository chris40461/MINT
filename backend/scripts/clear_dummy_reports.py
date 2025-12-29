#!/usr/bin/env python3
"""
DB에서 더미 리포트 삭제 스크립트

model_name='dummy'인 리포트를 모두 삭제합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import get_db
from app.db.models import ReportResult


def clear_dummy_reports():
    """더미 리포트 삭제"""
    with get_db() as db:
        # 더미 리포트 조회
        dummy_reports = db.query(ReportResult).filter(
            ReportResult.model_name == "dummy"
        ).all()

        if not dummy_reports:
            print("삭제할 더미 리포트가 없습니다.")
            return

        print(f"\n삭제할 더미 리포트: {len(dummy_reports)}개")
        for report in dummy_reports:
            print(f"  - {report.report_type} / {report.date} / {report.model_name}")

        # 삭제
        deleted_count = db.query(ReportResult).filter(
            ReportResult.model_name == "dummy"
        ).delete()

        print(f"\n{deleted_count}개 더미 리포트 삭제 완료")


if __name__ == "__main__":
    clear_dummy_reports()
