# 참고: docs/database/01-schema-design.md

"""
데이터베이스 모델 정의
"""

from sqlalchemy import Column, String, Float, DateTime, Integer, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class FinancialData(Base):
    """재무 데이터 테이블 (DART API 캐싱용)"""
    __tablename__ = 'financial_data'

    ticker = Column(String(10), primary_key=True, index=True)
    name = Column(String(100), nullable=True)

    # 시장 정보 (pykrx)
    market = Column(String(10), nullable=True)  # KOSPI, KOSDAQ, KONEX, 기타

    # 재무 지표 (pykrx)
    bps = Column(Float, default=0.0)  # 주당순자산가치 (Book value Per Share)
    per = Column(Float, default=0.0)  # 주가수익비율 (Price Earnings Ratio)
    pbr = Column(Float, default=0.0)  # 주가순자산비율 (Price Book-value Ratio)
    eps = Column(Float, default=0.0)  # 주당순이익 (Earnings Per Share)
    div = Column(Float, default=0.0)  # 배당수익률 (Dividend yield %)
    dps = Column(Float, default=0.0)  # 주당배당금 (Dividend Per Share)

    # 계산된 지표
    roe = Column(Float, default=0.0)  # 자기자본이익률 (ROE %)

    # DART API 지표
    debt_ratio = Column(Float, default=0.0)  # 부채비율 (%)
    revenue_growth_yoy = Column(Float, default=0.0)  # 매출 성장률 (%)

    # 메타데이터
    market_cap = Column(Float, default=0.0)  # 시가총액 (억원)
    trading_value = Column(Float, default=0.0)  # 거래대금 (억원)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 필터 상태 추적
    filter_status = Column(String(20), default='unknown')  # 'pass', 'fail', 'unknown'
    last_filter_check_date = Column(DateTime, nullable=True)  # 마지막 필터 검증 날짜

    def __repr__(self):
        return f"<FinancialData(ticker={self.ticker}, roe={self.roe}, updated_at={self.updated_at})>"

    def to_dict(self):
        """딕셔너리 변환"""
        return {
            'ticker': self.ticker,
            'name': self.name,
            'market': self.market,
            'bps': self.bps,
            'per': self.per,
            'pbr': self.pbr,
            'eps': self.eps,
            'div': self.div,
            'dps': self.dps,
            'roe': self.roe,
            'debt_ratio': self.debt_ratio,
            'revenue_growth_yoy': self.revenue_growth_yoy,
            'market_cap': self.market_cap,
            'trading_value': self.trading_value,
            'filter_status': self.filter_status,
            'last_filter_check_date': self.last_filter_check_date.isoformat() if self.last_filter_check_date else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TriggerResult(Base):
    """급등주 트리거 결과 테이블"""
    __tablename__ = 'trigger_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    trigger_type = Column(String(20), nullable=False, index=True)
    session = Column(String(10), nullable=False, index=True)

    # 가격/거래 정보
    current_price = Column(Integer, nullable=False)
    change_rate = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    trading_value = Column(Integer, nullable=False)

    # 점수
    composite_score = Column(Float, nullable=False)

    # 메타데이터
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    detected_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_date_session', 'date', 'session'),
        Index('idx_ticker_date', 'ticker', 'date'),
    )

    def __repr__(self):
        return f"<TriggerResult(ticker={self.ticker}, type={self.trigger_type}, score={self.composite_score})>"

    def to_dict(self):
        return {
            'ticker': self.ticker,
            'name': self.name,
            'trigger_type': self.trigger_type,
            'session': self.session,
            'current_price': self.current_price,
            'change_rate': self.change_rate,
            'volume': self.volume,
            'trading_value': self.trading_value,
            'composite_score': self.composite_score,
            'date': self.date,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None
        }


class RealtimePrice(Base):
    """실시간 주가 테이블 (KIS REST API 폴링)"""
    __tablename__ = 'realtime_prices'

    # Primary key
    ticker = Column(String(10), primary_key=True, index=True)

    # 가격 데이터
    current_price = Column(Integer, nullable=False)
    change_rate = Column(Float, nullable=False)
    change_amount = Column(Integer, nullable=False)

    # 거래량 데이터
    volume = Column(Integer, nullable=False)

    # OHLC (장중)
    open_price = Column(Integer, nullable=True)
    high_price = Column(Integer, nullable=True)
    low_price = Column(Integer, nullable=True)

    # 거래 데이터
    trading_value = Column(Integer, default=0)

    # 메타데이터
    market_status = Column(String(20), default='open')  # open, closed, pre_market, after_hours
    data_source = Column(String(20), default='kis')

    # 타임스탬프
    updated_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_ticker_updated', 'ticker', 'updated_at'),
    )

    def __repr__(self):
        return f"<RealtimePrice(ticker={self.ticker}, price={self.current_price}, change={self.change_rate}%, updated={self.updated_at})>"

    def to_dict(self):
        return {
            'ticker': self.ticker,
            'current_price': self.current_price,
            'change_rate': self.change_rate,
            'change_amount': self.change_amount,
            'volume': self.volume,
            'open_price': self.open_price,
            'high_price': self.high_price,
            'low_price': self.low_price,
            'trading_value': self.trading_value,
            'market_status': self.market_status,
            'data_source': self.data_source,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AnalysisResult(Base):
    """기업 분석 결과 테이블 (Company Analysis 캐싱용)"""
    __tablename__ = 'analysis_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD

    # 분석 내용 (JSON으로 저장)
    content = Column(String, nullable=False)  # JSON string (Analysis 모델)

    # 메타데이터
    generated_at = Column(DateTime, nullable=False)
    model_name = Column(String(50), default="gemini-2.5-flash")
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_analysis_ticker_date', 'ticker', 'date', unique=True),
    )

    def __repr__(self):
        return f"<AnalysisResult(ticker={self.ticker}, date={self.date})>"

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'ticker': self.ticker,
            'date': self.date,
            'content': json.loads(self.content) if self.content else {},
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'model_name': self.model_name,
            'tokens_used': self.tokens_used
        }


class ReportResult(Base):
    """리포트 결과 테이블 (Morning/Afternoon Reports)"""
    __tablename__ = 'report_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(10), nullable=False, index=True)  # morning, afternoon
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD

    # 리포트 내용 (JSON으로 저장)
    content = Column(String, nullable=False)  # JSON string

    # 메타데이터
    generated_at = Column(DateTime, nullable=False)
    model_name = Column(String(50), default="gemini-2.5-flash")
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index('idx_type_date', 'report_type', 'date', unique=True),
    )

    def __repr__(self):
        return f"<ReportResult(type={self.report_type}, date={self.date})>"

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'report_type': self.report_type,
            'date': self.date,
            'content': json.loads(self.content) if self.content else {},
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'model_name': self.model_name,
            'tokens_used': self.tokens_used
        }
