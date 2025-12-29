"""
AnalysisService 테스트 - 실제 데이터 (11월 14일)

batch_analyze, invalidate_cache, check_analysis_trigger 등 헬퍼 메서드 테스트
"""

import sys
from pathlib import Path

# backend 디렉토리를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.analysis_service import AnalysisService
from app.services.data_service import DataService
from app.models.analysis import Analysis, FinancialData, NewsData, TechnicalData

# 테스트 기준일: 11월 14일 (11월 15일은 휴장일)
TEST_DATE = datetime(2025, 11, 14)


@pytest.fixture
def real_data_service():
    """실제 DataService (pykrx + DB)"""
    return DataService()


@pytest.fixture
def mock_llm_service():
    """LLMCompanyAnalysis 모킹 (API 호출 방지)"""
    service = MagicMock()

    # analyze_news_sentiment
    service.analyze_news_sentiment = AsyncMock(return_value={
        'positive_count': 5,
        'negative_count': 1,
        'neutral_count': 2,
        'sentiment': 'positive',
        'adjustment': 0.05
    })

    # analyze_company
    service.analyze_company = AsyncMock(return_value={
        'summary': '실제 데이터 기반 종합 분석 결과',
        'opinion': 'BUY',
        'target_price': 100000,
        'risks': ['시장 변동성', '경기 둔화', '환율 리스크']
    })

    return service


@pytest.fixture
def analysis_service(real_data_service, mock_llm_service):
    """AnalysisService 인스턴스 (실제 데이터 사용, DB 캐싱)"""
    return AnalysisService(
        data_service=real_data_service,
        llm_service=mock_llm_service
    )


# ============= batch_analyze 테스트 (실제 데이터) =============

@pytest.mark.asyncio
async def test_batch_analyze_success(analysis_service):
    """
    batch_analyze: 실제 데이터로 여러 종목 분석 (11월 14일)

    검증 사항:
    - 모든 종목이 성공적으로 분석됨
    - Analysis 객체가 올바르게 생성됨
    - 실제 재무 데이터가 포함됨
    """
    # 실제 DB에 있는 종목들
    tickers = ['005930', '000660', '005380']  # 삼성전자, SK하이닉스, 현대차

    results = await analysis_service.batch_analyze(tickers)

    # 검증
    assert len(results) == 3
    assert '005930' in results
    assert '000660' in results
    assert '005380' in results

    # 삼성전자 분석 결과 상세 검증
    samsung = results['005930']
    assert isinstance(samsung, Analysis)
    assert samsung.ticker == '005930'
    assert samsung.name == '삼성전자'  # DB의 실제 이름
    assert samsung.current_price > 0
    assert samsung.market_cap > 0

    # 재무 데이터 검증 (Pydantic 모델)
    assert isinstance(samsung.financial, FinancialData)
    assert samsung.financial.per >= 0
    assert samsung.financial.pbr >= 0

    # 뉴스 데이터 검증
    assert isinstance(samsung.news, NewsData)

    # 기술적 지표 검증
    assert isinstance(samsung.technical, TechnicalData)

    print(f"\n✅ batch_analyze 성공:")
    print(f"   - 삼성전자 (005930): 시가총액 {samsung.market_cap:,.0f}억, 현재가 {samsung.current_price:,}원")
    print(f"   - PER: {samsung.financial.per:.2f}, PBR: {samsung.financial.pbr:.2f}")
    print(f"   - 뉴스 센티먼트: {samsung.news.sentiment} ({samsung.news.positive_count}긍정/{samsung.news.negative_count}부정)")
    print(f"   - 기술적: RSI {samsung.technical.rsi:.1f}, MACD {samsung.technical.macd_status}")


@pytest.mark.asyncio
async def test_batch_analyze_with_invalid_ticker(analysis_service):
    """
    batch_analyze: 잘못된 종목 포함 (실패 처리)

    검증 사항:
    - 유효한 종목은 성공
    - 무효한 종목은 자동으로 제외
    - 전체 프로세스는 계속 진행
    """
    tickers = ['005930', 'INVALID', '000660']

    results = await analysis_service.batch_analyze(tickers)

    # 검증: 유효한 종목만 결과에 포함
    assert len(results) >= 1  # 최소 1개 이상 성공
    assert '005930' in results or '000660' in results
    assert 'INVALID' not in results  # 무효 종목 제외

    print(f"\n✅ batch_analyze 무효 종목 처리: {len(results)}/{len(tickers)} 성공")


# ============= invalidate_cache 테스트 =============

@pytest.mark.asyncio
async def test_invalidate_cache_success(analysis_service):
    """
    invalidate_cache: 성공 케이스 (DB에서 캐시 삭제)
    """
    ticker = '005930'

    # invalidate_cache는 DB에서 해당 ticker의 분석 결과를 삭제
    # 예외가 발생하지 않으면 성공
    await analysis_service.invalidate_cache(ticker)

    print("\n✅ invalidate_cache 성공 케이스 통과 (DB 삭제)")


@pytest.mark.asyncio
async def test_invalidate_cache_failure(analysis_service):
    """
    invalidate_cache: 실패 케이스 (DB 오류)
    """
    # DB 오류를 시뮬레이션하기 위해 get_db를 패치
    from app.db.database import get_db

    with patch('app.services.analysis_service.get_db') as mock_db:
        # DB 세션에서 오류 발생
        mock_session = MagicMock()
        mock_session.__enter__.return_value.query.side_effect = Exception("Database error")
        mock_db.return_value = mock_session

        ticker = '005930'

        # 예외가 발생해야 함
        with pytest.raises(Exception, match="Database error"):
            await analysis_service.invalidate_cache(ticker)

    print("\n✅ invalidate_cache 실패 케이스 통과 (DB 오류 처리)")


# ============= check_analysis_trigger 테스트 =============

@pytest.mark.asyncio
async def test_check_analysis_trigger_surge(analysis_service):
    """
    check_analysis_trigger: 급등 케이스 (10% 이상)
    """
    ticker = '005930'
    current_price = 80000
    change_rate = 12.5  # 10% 이상 급등

    should_refresh = await analysis_service.check_analysis_trigger(
        ticker, current_price, change_rate
    )

    # 재분석 필요
    assert should_refresh is True

    print("\n✅ check_analysis_trigger 급등 케이스 통과")


@pytest.mark.asyncio
async def test_check_analysis_trigger_plunge(analysis_service):
    """
    check_analysis_trigger: 급락 케이스 (-10% 이하)
    """
    ticker = '005930'
    current_price = 60000
    change_rate = -11.3  # 10% 이상 급락

    should_refresh = await analysis_service.check_analysis_trigger(
        ticker, current_price, change_rate
    )

    # 재분석 필요
    assert should_refresh is True

    print("\n✅ check_analysis_trigger 급락 케이스 통과")


@pytest.mark.asyncio
async def test_check_analysis_trigger_normal(analysis_service):
    """
    check_analysis_trigger: 정상 등락 케이스 (10% 미만)
    """
    ticker = '005930'
    current_price = 72000
    change_rate = 5.2  # 10% 미만

    should_refresh = await analysis_service.check_analysis_trigger(
        ticker, current_price, change_rate
    )

    # 재분석 불필요
    assert should_refresh is False

    print("\n✅ check_analysis_trigger 정상 등락 케이스 통과")


# ============= get_popular_stocks_analysis 테스트 (실제 데이터) =============

@pytest.mark.asyncio
async def test_get_popular_stocks_analysis(analysis_service):
    """
    get_popular_stocks_analysis: 실제 거래대금 상위 종목 분석 (11월 14일)

    검증 사항:
    - 실제 시장 데이터에서 거래대금 상위 종목 선정
    - 각 종목에 대해 Analysis 객체 생성
    - 실제 재무 데이터 포함 확인
    """
    limit = 5  # 상위 5개만 테스트 (시간 절약)

    analyses = await analysis_service.get_popular_stocks_analysis(TEST_DATE, limit=limit)

    # 검증
    assert len(analyses) <= limit
    assert len(analyses) > 0  # 최소 1개 이상
    assert all(isinstance(a, Analysis) for a in analyses)

    # 첫 번째 종목 상세 검증
    top_stock = analyses[0]
    assert top_stock.ticker is not None
    assert top_stock.current_price > 0
    assert top_stock.market_cap > 0

    print(f"\n✅ get_popular_stocks_analysis 성공:")
    print(f"   - 분석된 종목 수: {len(analyses)}/{limit}")
    for i, stock in enumerate(analyses, 1):
        print(f"   - {i}위: {stock.ticker} (시총 {stock.market_cap:,.0f}억, {stock.opinion})")
    print()


# ============= 실행 =============

if __name__ == "__main__":
    print("=" * 80)
    print("AnalysisService 테스트 - 실제 데이터 (11월 14일)")
    print("=" * 80)
    print()

    # Fixture 생성
    data_svc = DataService()
    llm_svc = MagicMock()
    llm_svc.analyze_news_sentiment = AsyncMock(return_value={
        'positive_count': 5,
        'negative_count': 1,
        'neutral_count': 2,
        'sentiment': 'positive',
        'adjustment': 0.05
    })
    llm_svc.analyze_company = AsyncMock(return_value={
        'summary': '실제 데이터 기반 종합 분석 결과',
        'opinion': 'BUY',
        'target_price': 100000,
        'risks': ['시장 변동성', '경기 둔화', '환율 리스크']
    })

    svc = AnalysisService(
        data_service=data_svc,
        llm_service=llm_svc
    )

    # 테스트 실행
    print("테스트 1: batch_analyze (삼성전자, SK하이닉스, 현대차)")
    print("-" * 80)
    asyncio.run(test_batch_analyze_success(svc))

    print("\n테스트 2: get_popular_stocks_analysis (상위 5개)")
    print("-" * 80)
    asyncio.run(test_get_popular_stocks_analysis(svc))

    print("\n테스트 3: invalidate_cache")
    print("-" * 80)
    asyncio.run(test_invalidate_cache_success(svc))

    print("\n테스트 4: check_analysis_trigger (급등)")
    print("-" * 80)
    asyncio.run(test_check_analysis_trigger_surge(svc))

    print("\n테스트 5: check_analysis_trigger (급락)")
    print("-" * 80)
    asyncio.run(test_check_analysis_trigger_plunge(svc))

    print("\n" + "=" * 80)
    print("모든 테스트 완료! ✅")
    print("=" * 80)
