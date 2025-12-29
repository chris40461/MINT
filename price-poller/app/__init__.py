"""
Price Poller Service

KIS REST API를 사용하여 필터 통과 종목의 준실시간 가격을 폴링하고
realtime_prices 테이블에 업데이트하는 마이크로서비스입니다.

Architecture:
- KIS REST API 멀티종목 시세조회 (최대 30개/호출)
- 30개씩 배치
- 0.5초 간격 폴링 (API 제한 준수: 초당 2건)
"""

__version__ = "1.0.0"
