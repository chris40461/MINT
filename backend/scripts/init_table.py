""" 
테이블 생성 스크립트

실행 방법:
    python backend/scripts/init_table.py
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import init_db

if __name__ == "__main__":
    print("🔧 테이블 생성 중...")
    init_db()
    print("✅ 완료!")
