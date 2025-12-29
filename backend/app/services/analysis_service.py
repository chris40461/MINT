# 참고: docs/backend/06-company-analysis.md
# 참고: docs/database/02-cache-strategy.md

"""
기업 분석 서비스

기업 분석 오케스트레이션 및 캐싱 관리 (DB 기반)
"""

from datetime import datetime
from typing import Dict, Optional
import logging
import json
import asyncio
import pandas as pd

# Note: Analysis, AnalysisResponse 모델은 더 이상 사용하지 않음
# 프론트엔드 CompanyAnalysis 타입과 호환되는 딕셔너리를 직접 반환
from app.services.data_service import DataService
from app.services.llm_company_analysis import LLMCompanyAnalysis
from app.db.models import AnalysisResult
from app.db.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)


class AnalysisService:
    """기업 분석 서비스 (DB 캐싱)"""

    def __init__(
        self,
        data_service: DataService,
        llm_service: LLMCompanyAnalysis
    ):
        """
        서비스 초기화

        Args:
            data_service: 데이터 수집 서비스
            llm_service: LLM 서비스
        """
        self.data_service = data_service
        self.llm_service = llm_service

    async def get_analysis(
        self,
        ticker: str,
        force_refresh: bool = False
    ) -> Dict:
        """
        기업 분석 조회 (캐싱 포함)

        캐싱 전략:
        - DB 테이블: analysis_results
        - 캐시 키: ticker + date (unique index)
        - TTL: 24시간 (날짜 기준)
        - 재생성 조건: 캐시 만료, 중요 공시, 급등/급락 (10% 이상)

        Args:
            ticker: 종목 코드
            force_refresh: 강제 재생성 (기본값: False)

        Returns:
            프론트엔드 CompanyAnalysis 타입과 호환되는 딕셔너리
            {
                ticker, date, summary, financial_analysis, industry_analysis,
                technical_analysis, news_analysis, risk_factors, investment_strategy,
                generated_at, model_name, tokens_used
            }

        Raises:
            ValueError: 종목 코드가 유효하지 않을 때
            Exception: 분석 생성 실패 시

        Example:
            >>> analysis = await service.get_analysis('005930')
            >>> print(analysis['summary']['opinion'])  # 'strong_buy'
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # DB 캐시 조회
        if not force_refresh:
            with get_db() as db:
                cached = db.query(AnalysisResult).filter(
                    AnalysisResult.ticker == ticker,
                    AnalysisResult.date == today
                ).first()

                if cached:
                    logger.info(f"DB 캐시 히트: {ticker}")
                    content = json.loads(cached.content)
                    return content

        # 분석 생성
        logger.info(f"분석 생성 시작: {ticker}")
        analysis_result = await self._generate_analysis(ticker)

        # DB 저장 (캐시)
        with get_db() as db:
            # 기존 분석 삭제 (같은 ticker + date)
            db.query(AnalysisResult).filter(
                AnalysisResult.ticker == ticker,
                AnalysisResult.date == today
            ).delete()

            # 새 분석 저장
            db_result = AnalysisResult(
                ticker=ticker,
                date=today,
                content=json.dumps(analysis_result, ensure_ascii=False, default=str),
                generated_at=datetime.now(),
                model_name=settings.GEMINI_MODEL,
                tokens_used=analysis_result.get('tokens_used', 0)
            )
            db.add(db_result)
            db.commit()

        logger.info(f"분석 저장 완료: {ticker}")
        return analysis_result

    async def _generate_analysis(self, ticker: str) -> Dict:
        """
        기업 분석 생성 (실제 로직)

        Args:
            ticker: 종목 코드

        Returns:
            프론트엔드 CompanyAnalysis 타입과 호환되는 딕셔너리
        """
        # 1. 기본 정보 조회
        stock_info = await self.data_service.get_stock_info(ticker)

        # 2. 현재 가격 조회
        today = datetime.now()
        snapshot = await self.data_service.get_market_snapshot(today)

        # snapshot은 reset_index()되어 ticker가 컬럼임
        current_data_df = snapshot[snapshot['ticker'] == ticker]
        if current_data_df.empty:
            raise ValueError(f"{ticker}: 현재가 데이터 없음")
        current_data = current_data_df.iloc[0]

        # 3. 재무 데이터 조회
        financial = await self.data_service.get_financial_data(ticker)

        # 4. 뉴스 데이터 조회
        news_list = await self.data_service.get_news_data(ticker, days=7)

        # 5. 기술적 지표 계산
        technical = await self.data_service.get_technical_indicators(ticker, today)

        # 6. 종합 분석 (LLM) - 프론트엔드 형식으로 반환
        company_data = {
            'name': stock_info['name'],
            'current_price': int(current_data['종가']),
            'market_cap': stock_info['market_cap'],
            'financial': financial,
            'news': news_list,
            'technical': technical
        }

        llm_result = await self.llm_service.analyze_company(ticker, company_data)

        # 7. 프론트엔드 CompanyAnalysis 타입에 맞게 변환
        current_price = int(current_data['종가'])
        target_price = llm_result.get('target_price', current_price)
        upside = ((target_price - current_price) / current_price * 100) if current_price > 0 else 0

        # opinion을 소문자로 변환 (STRONG_BUY -> strong_buy)
        opinion_raw = llm_result.get('opinion', 'HOLD')
        opinion = opinion_raw.lower() if isinstance(opinion_raw, str) else 'hold'

        # summary 구조체 생성 (프론트엔드 기대 형식)
        summary_text = llm_result.get('summary', '')
        summary_obj = {
            'opinion': opinion,
            'target_price': target_price,
            'current_price': current_price,
            'upside': round(upside, 1),
            'key_points': llm_result.get('key_points', [summary_text]) if summary_text else []
        }

        # news_analysis 변환 (프론트엔드 기대 형식)
        news_analysis_raw = llm_result.get('news_analysis', {})
        if isinstance(news_analysis_raw, dict):
            news_analysis = {
                'sentiment': news_analysis_raw.get('sentiment', 'neutral'),
                'key_news': news_analysis_raw.get('key_news', []),
                'impact': news_analysis_raw.get('impact', '')
            }
        else:
            news_analysis = {
                'sentiment': 'neutral',
                'key_news': [],
                'impact': str(news_analysis_raw) if news_analysis_raw else ''
            }

        # 헬퍼 함수: LLM 응답이 문자열인 경우 기본 객체로 변환
        def ensure_dict(value, default_dict: dict) -> dict:
            """문자열 응답을 객체로 변환 (폴백 처리)"""
            if isinstance(value, dict):
                # 객체인 경우: 누락된 키에 대해 기본값 적용
                result = default_dict.copy()
                result.update(value)
                return result
            elif isinstance(value, str) and value:
                # 문자열인 경우: 첫 번째 필드에 전체 텍스트 저장
                first_key = list(default_dict.keys())[0]
                result = default_dict.copy()
                result[first_key] = value
                return result
            else:
                return default_dict

        # 재무 분석 변환
        financial_default = {
            'profitability': '',
            'growth': '',
            'stability': '',
            'valuation': ''
        }
        financial_analysis = ensure_dict(
            llm_result.get('financial_analysis'),
            financial_default
        )

        # 산업 분석 변환
        industry_default = {
            'industry_trend': '',
            'competitive_advantage': '',
            'market_position': ''
        }
        industry_analysis = ensure_dict(
            llm_result.get('industry_analysis'),
            industry_default
        )

        # 기술적 분석 변환
        technical_default = {
            'trend': '',
            'support_resistance': '',
            'indicators': ''
        }
        technical_analysis = ensure_dict(
            llm_result.get('technical_analysis'),
            technical_default
        )

        # 투자 전략 변환
        strategy_default = {
            'short_term': '',
            'mid_term': '',
            'long_term': ''
        }
        investment_strategy = ensure_dict(
            llm_result.get('investment_strategy'),
            strategy_default
        )

        # 최종 결과 조합
        analysis_result = {
            'ticker': ticker,
            'date': today.strftime("%Y-%m-%d"),
            # 요약 (프론트엔드 summary 객체 형식)
            'summary': summary_obj,
            # 재무 분석
            'financial_analysis': financial_analysis,
            # 산업 분석
            'industry_analysis': industry_analysis,
            # 기술적 분석
            'technical_analysis': technical_analysis,
            # 뉴스 분석
            'news_analysis': news_analysis,
            # 리스크 요인
            'risk_factors': llm_result.get('risks', []),
            # 투자 전략
            'investment_strategy': investment_strategy,
            # 메타데이터
            'generated_at': today.isoformat(),
            'model_name': settings.GEMINI_MODEL,
            'tokens_used': llm_result.get('tokens_used', 0)
        }

        logger.info(f"분석 완료: {ticker} - {opinion}")
        return analysis_result

    async def batch_analyze(
        self,
        tickers: list[str]
    ) -> Dict[str, Dict]:
        """
        여러 종목 일괄 분석

        Args:
            tickers: 종목 코드 리스트

        Returns:
            {ticker: 분석 결과 딕셔너리}

        Example:
            >>> results = await service.batch_analyze(['005930', '000660'])
        """
        logger.info(f"배치 분석 시작: {len(tickers)}개 종목")

        # 비동기 병렬 처리 (return_exceptions=True: 일부 실패해도 계속 진행)
        tasks = [self.get_analysis(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 성공한 결과만 필터링
        analysis_dict = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.error(f"분석 실패 ({ticker}): {result}")
            else:
                analysis_dict[ticker] = result
                logger.info(f"분석 성공: {ticker}")

        logger.info(f"배치 분석 완료: {len(analysis_dict)}/{len(tickers)} 성공")
        return analysis_dict

    async def invalidate_cache(self, ticker: str) -> None:
        """
        특정 종목의 캐시 무효화 (DB에서 삭제)

        중요 공시, 급등/급락 발생 시 호출

        Args:
            ticker: 종목 코드

        Example:
            >>> await service.invalidate_cache('005930')
        """
        today = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"캐시 무효화 시도: {ticker} (날짜: {today})")

        # DB에서 삭제
        try:
            with get_db() as db:
                deleted = db.query(AnalysisResult).filter(
                    AnalysisResult.ticker == ticker,
                    AnalysisResult.date == today
                ).delete()

                db.commit()

                if deleted > 0:
                    logger.info(f"캐시 무효화 완료: {ticker} ({deleted}건 삭제)")
                else:
                    logger.info(f"캐시 없음: {ticker}")

        except Exception as e:
            logger.error(f"캐시 무효화 실패 ({ticker}): {e}")
            raise

    async def check_analysis_trigger(
        self,
        ticker: str,
        current_price: int,
        change_rate: float
    ) -> bool:
        """
        분석 재생성 트리거 체크

        조건:
        1. 급등/급락 (10% 이상)
        2. 중요 공시 발생 (별도 구현 필요)

        Args:
            ticker: 종목 코드
            current_price: 현재가
            change_rate: 등락률

        Returns:
            True: 재분석 필요, False: 캐시 유지

        Example:
            >>> should_refresh = await service.check_analysis_trigger(
            ...     '005930',
            ...     72000,
            ...     12.5
            ... )
            >>> if should_refresh:
            ...     await service.invalidate_cache('005930')
        """
        logger.info(f"재분석 트리거 체크 시작: {ticker} (등락률: {change_rate:+.1f}%)")

        # 조건 1: 급등/급락 체크 (10% 이상)
        abs_change = abs(change_rate)
        if abs_change >= 10.0:
            logger.warning(f"급등/급락 감지 ({ticker}): {change_rate:+.1f}% - 재분석 필요")
            return True

        # 조건 2: 중요 공시 체크 (DART API)
        # TODO: DART API 연동
        # - 당일 공시 조회
        # - 중요 공시 필터링 (실적 발표, 배당, 합병, 유상증자 등)
        # - 중요 공시 발견 시 True 반환

        logger.info(f"재분석 불필요 ({ticker}): 트리거 조건 미달")
        return False

    async def get_popular_stocks_analysis(
        self,
        date: datetime,
        limit: int = 10
    ) -> list[Dict]:
        """
        주요 종목 자동 분석 (배치용)

        장 마감 후 Top 10 종목 자동 분석

        Args:
            date: 날짜
            limit: 분석할 종목 수 (기본값: 10)

        Returns:
            분석 결과 딕셔너리 리스트

        Example:
            >>> analyses = await service.get_popular_stocks_analysis(
            ...     datetime(2025, 11, 6),
            ...     limit=10
            ... )
        """
        logger.info(f"주요 종목 자동 분석 시작 ({date.strftime('%Y-%m-%d')}): Top {limit}")

        # Step 1: 거래대금 Top N 종목 조회
        market_data = await self.data_service.get_market_snapshot(date)

        # 거래대금 기준 정렬
        top_stocks = market_data.nlargest(limit, '거래대금')

        # 종목 코드 추출 (ticker 컬럼에서 가져옴)
        tickers = top_stocks['ticker'].tolist()

        logger.info(f"거래대금 Top {limit} 종목 선정: {tickers}")

        # Step 2: 배치 분석
        analysis_dict = await self.batch_analyze(tickers)

        # Step 3: 결과 변환 (Dict → List, ticker 순서 유지)
        analyses = []
        for ticker in tickers:
            if ticker in analysis_dict:
                analyses.append(analysis_dict[ticker])
            else:
                logger.warning(f"분석 실패로 제외: {ticker}")

        logger.info(f"주요 종목 분석 완료: {len(analyses)}/{limit} 성공")
        return analyses

    # Note: calculate_metric_score() 삭제됨
    # - 이미 select_top_stocks_for_morning()에서 동일 로직 구현
    # - 중복 방지를 위해 삭제
