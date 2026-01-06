# 참고: docs/backend/01-data-collection.md
# 참고: docs/architecture/02-data-flow.md

"""
데이터 수집 서비스

pykrx, DART API 등을 통해 주식 데이터를 수집합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import time
import asyncio
from functools import lru_cache
from app.utils.krx_data_client import stock

try:
    import OpenDartReader
except ImportError:
    OpenDartReader = None

logger = logging.getLogger(__name__)


class DataService:
    """주식 데이터 수집 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.retry_attempts = 3
        self.retry_delay = 2  # 초

        # DART API 초기화
        from app.core.config import settings
        self.dart_api_key = settings.DART_API_KEY

        if self.dart_api_key and OpenDartReader:
            try:
                self.dart = OpenDartReader(self.dart_api_key)
                logger.info("DataService 초기화 완료 (pykrx + DART API 연동)")
            except Exception as e:
                logger.error(f"DART API 초기화 실패: {e}")
                self.dart = None
        else:
            self.dart = None
            if not self.dart_api_key:
                logger.warning("DART API 키가 설정되지 않았습니다. 재무 데이터 조회가 제한됩니다.")
            if not OpenDartReader:
                logger.warning("OpenDartReader가 설치되지 않았습니다. 재무 데이터 조회가 제한됩니다.")

    async def get_market_snapshot(self, date: datetime, max_retries: int = 10) -> pd.DataFrame:
        """
        전체 시장 OHLCV 스냅샷 조회

        Args:
            date: 조회할 날짜
            max_retries: 최대 재귀 깊이 (기본값: 10, 연속 휴장일 대비)

        Returns:
            DataFrame with columns:
            - ticker: 종목 코드 (인덱스)
            - 시가, 고가, 저가, 종가: 가격 정보
            - 거래량: 거래량
            - 거래대금: 거래대금
            - 시가총액: 시가총액

        Raises:
            ValueError: 데이터 조회 실패 시 또는 최대 재시도 횟수 초과

        Example:
            >>> service = DataService()
            >>> df = await service.get_market_snapshot(datetime(2025, 11, 6))
            >>> print(df.head())
        """
        # 무한 재귀 방지
        if max_retries <= 0:
            raise ValueError(f"최대 재시도 횟수 초과: {date.strftime('%Y%m%d')}부터 10일 연속 휴장일")

        date_str = date.strftime("%Y%m%d")
        logger.info(f"시장 스냅샷 조회: {date_str} (재시도 남음: {max_retries})")

        try:
            # 1. OHLCV + 거래대금 + 시가총액 데이터 조회 (전체 시장)
            # 주의: pykrx의 get_market_ohlcv_by_ticker는 거래대금, 등락률, 시가총액도 포함
            df = self._retry_request(
                lambda: stock.get_market_ohlcv_by_ticker(date_str, market="ALL")
            )

            if df.empty:
                logger.warning(f"{date_str} 데이터 없음 (휴장일), 이전 거래일 조회")
                prev_date = await self.get_previous_trading_day(date)
                return await self.get_market_snapshot(prev_date, max_retries - 1)

            # 데이터 품질 체크: 주말/휴장일에는 pykrx가 빈 문자열을 0으로 replace
            # 종가가 0인 종목이 90% 이상이면 잘못된 데이터로 판단
            zero_count = (df['종가'] == 0).sum()
            total_count = len(df)

            if total_count > 0 and zero_count / total_count > 0.9:
                logger.warning(f"{date_str} 데이터 품질 낮음 ({zero_count}/{total_count} 종목이 0원), 이전 거래일 조회")
                prev_date = await self.get_previous_trading_day(date)
                return await self.get_market_snapshot(prev_date, max_retries - 1)

            # 2. 시가총액 + 상장주식수 추가
            try:
                cap = self._retry_request(
                    lambda: stock.get_market_cap_by_ticker(date_str, market="ALL")
                )
                # 시가총액 + 상장주식수 추가
                df['시가총액'] = cap['시가총액']
                df['상장주식수'] = cap['상장주식수']
            except Exception as e:
                logger.warning(f"시가총액/상장주식수 조회 실패: {e}")
                df['시가총액'] = 0
                df['상장주식수'] = 0

            # 3. 인덱스를 'ticker' 컬럼으로 변환
            df = df.reset_index()
            df = df.rename(columns={'티커': 'ticker'})

            # ticker를 문자열로 변환 (6자리 0 패딩)
            df['ticker'] = df['ticker'].astype(str).str.zfill(6)

            logger.info(f"조회 완료: {len(df)}개 종목 (pykrx 스냅샷)")

            return df

        except Exception as e:
            logger.error(f"시장 데이터 조회 실패: {e}")
            raise ValueError(f"시장 데이터 조회 실패: {e}")

    async def get_realtime_price(self, ticker: str) -> Optional[Dict]:
        """
        KIS 실시간 가격 조회 (realtime_prices 테이블)

        Args:
            ticker: 종목 코드 (예: '005930')

        Returns:
            {
                'ticker': str,
                'current_price': int,
                'change_rate': float,
                'change_amount': int,
                'volume': int,
                'open_price': int,
                'high_price': int,
                'low_price': int,
                'trading_value': int,
                'market_status': str,
                'data_source': str,
                'updated_at': datetime
            }
            or None if not available or stale (> 24시간)

        Example:
            >>> realtime = await service.get_realtime_price('005930')
            >>> print(realtime['current_price'])  # 70000
        """
        try:
            from app.db.database import get_db
            from app.db.models import RealtimePrice

            with get_db() as db:
                realtime = db.query(RealtimePrice).filter_by(ticker=ticker).first()

                if not realtime:
                    logger.debug(f"{ticker}: 실시간 가격 없음")
                    return None

                # Staleness 체크 (24시간 = 86400초)
                age_seconds = (datetime.now() - realtime.updated_at).total_seconds()
                if age_seconds > 86400:
                    logger.warning(f"{ticker}: 실시간 가격 오래됨 ({age_seconds/3600:.1f}시간)")
                    return None

                return realtime.to_dict()

        except Exception as e:
            logger.error(f"{ticker}: 실시간 가격 조회 실패 - {e}")
            return None

    async def get_current_price(self, ticker: str) -> int:
        """
        현재가 조회 (KIS → pykrx 폴백)

        Args:
            ticker: 종목 코드 (예: '005930')

        Returns:
            현재가 (원)

        Raises:
            ValueError: 가격 조회 실패

        Example:
            >>> price = await service.get_current_price('005930')
            >>> print(price)  # 70000
        """
        # KIS 실시간 우선
        realtime = await self.get_realtime_price(ticker)
        if realtime:
            logger.debug(f"{ticker}: KIS 실시간 가격 사용 ({realtime['current_price']})")
            return realtime['current_price']

        # pykrx 폴백
        logger.debug(f"{ticker}: pykrx 폴백")

        try:
            today = datetime.now()
            for i in range(10):
                check_date = today - timedelta(days=i)
                date_str = check_date.strftime("%Y%m%d")

                try:
                    df = await asyncio.to_thread(
                        stock.get_market_ohlcv_by_date,
                        date_str,
                        date_str,
                        ticker
                    )

                    if not df.empty:
                        price = int(df.iloc[-1]['Close'])
                        logger.debug(f"{ticker}: pykrx 가격 ({price}) from {date_str}")
                        return price

                except Exception:
                    continue

            raise ValueError(f"{ticker}: 최근 10일 가격 없음")

        except Exception as e:
            logger.error(f"{ticker}: 가격 조회 실패 - {e}")
            raise ValueError(f"{ticker}: 현재가 조회 실패")

    async def get_realtime_prices_bulk(
        self,
        tickers: List[str],
        staleness_threshold: int = 86400
    ) -> Dict[str, Dict]:
        """
        여러 종목의 실시간 가격을 한 번에 조회

        Args:
            tickers: 종목 코드 리스트
            staleness_threshold: 데이터 신선도 기준 (초, 기본 24시간)

        Returns:
            {
                '005930': {
                    'current_price': 70000,
                    'change_rate': 2.5,
                    'volume': 1000000,
                    'updated_at': datetime(...),
                    'data_source': 'kis'
                },
                '000660': { ... }
            }

        Note:
            - realtime_prices에 없거나 stale한 종목은 결과에서 제외됨
            - 호출자가 폴백 처리 필요

        Example:
            >>> prices = await service.get_realtime_prices_bulk(['005930', '000660'])
            >>> print(len(prices))  # 2
        """
        try:
            from app.db.database import get_db
            from app.db.models import RealtimePrice

            with get_db() as db:
                # 신선도 기준 시간 계산
                threshold_time = datetime.now() - timedelta(seconds=staleness_threshold)

                # 배치 쿼리 (IN 절 사용)
                realtime_prices = db.query(RealtimePrice).filter(
                    RealtimePrice.ticker.in_(tickers),
                    RealtimePrice.updated_at > threshold_time
                ).all()

                # Dict로 변환
                result = {}
                for rt in realtime_prices:
                    result[rt.ticker] = rt.to_dict()

                logger.info(
                    f"✅ 실시간 가격 조회: {len(result)}/{len(tickers)}개 "
                    f"(신선도 기준: {staleness_threshold/3600:.1f}시간)"
                )
                return result

        except Exception as e:
            logger.error(f"❌ 실시간 가격 배치 조회 실패: {e}")
            return {}

    async def get_stock_info(self, ticker: str) -> Dict:
        """
        종목 기본 정보 조회

        Args:
            ticker: 종목 코드 (예: '005930')

        Returns:
            {
                'ticker': str,
                'name': str,
                'market': str,  # 'KOSPI' or 'KOSDAQ'
                'market_cap': int
            }

        Example:
            >>> info = await service.get_stock_info('005930')
            >>> print(info['name'])  # '삼성전자'
        """
        # ticker를 문자열로 변환 (숫자로 들어오는 경우 대비)
        ticker = str(ticker).zfill(6)  # 6자리 0 패딩
        logger.info(f"종목 정보 조회: {ticker}")

        # 1. DB에서 먼저 조회 (FinancialData 테이블)
        try:
            from app.db.database import get_db
            from app.db.models import FinancialData

            with get_db() as db:
                financial_data = db.query(FinancialData).filter_by(ticker=ticker).first()

                if financial_data:
                    logger.info(f"{ticker}: DB 조회 성공 (시총 {financial_data.market_cap:,.0f}억)")
                    return {
                        'ticker': ticker,
                        'name': financial_data.name or ticker,
                        'market': 'KOSPI',  # TODO: DB에 market 컬럼 추가 시 변경
                        'market_cap': int(financial_data.market_cap) if financial_data.market_cap else 0
                    }

        except Exception as e:
            logger.debug(f"{ticker}: DB 조회 실패 ({e}), API 조회 시도")

        # 2. API로 조회 (DB에 없을 때)
        try:
            # 종목명 조회
            name = self._retry_request(
                lambda: stock.get_market_ticker_name(ticker)
            )

            if not name:
                raise ValueError(f"종목 코드 {ticker}를 찾을 수 없습니다")

            # 시장 구분 확인 (KOSPI/KOSDAQ)
            market = self._get_market_type(ticker)

            # 시가총액 조회 (최근 거래일 찾기)
            today = datetime.now()

            # 최근 10일 내 거래일 찾기
            for i in range(10):
                try_date = today - timedelta(days=i)
                date_str = try_date.strftime("%Y%m%d")

                try:
                    cap_data = self._retry_request(
                        lambda: stock.get_market_cap_by_ticker(date_str, market=market)
                    )

                    if not cap_data.empty and ticker in cap_data.index:
                        market_cap = int(cap_data.loc[ticker, '시가총액'])
                        logger.info(f"{ticker}: 시가총액 조회 성공 ({date_str})")
                        return {
                            'ticker': ticker,
                            'name': name,
                            'market': market,
                            'market_cap': market_cap
                        }
                except Exception as e:
                    logger.debug(f"{ticker}: {date_str} 조회 실패 - {e}")
                    continue

            # 10일 내 거래일 없음
            logger.warning(f"{ticker}: 최근 거래일 시가총액 조회 실패")
            return {
                'ticker': ticker,
                'name': name,
                'market': market,
                'market_cap': 0
            }

        except Exception as e:
            logger.error(f"종목 정보 조회 실패 ({ticker}): {e}")
            raise ValueError(f"종목 정보 조회 실패: {e}")

    async def get_price_history(
        self,
        ticker: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        종목 가격 히스토리 조회

        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일 (기본값: 오늘)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume

        Example:
            >>> history = await service.get_price_history(
            ...     '005930',
            ...     datetime(2025, 10, 1)
            ... )
        """
        if end_date is None:
            end_date = datetime.now()

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        logger.info(f"가격 히스토리 조회: {ticker} ({start_str} ~ {end_str})")

        try:
            # pykrx로 OHLCV 조회
            df = self._retry_request(
                lambda: stock.get_market_ohlcv_by_date(start_str, end_str, ticker)
            )

            if df.empty:
                logger.warning(f"{ticker}의 가격 데이터가 없습니다")
                return pd.DataFrame()

            # 인덱스(날짜)를 컬럼으로 변환
            df = df.reset_index()
            df = df.rename(columns={'날짜': 'date'})

            logger.info(f"조회 완료: {len(df)}일치 데이터")
            return df

        except Exception as e:
            logger.error(f"가격 히스토리 조회 실패 ({ticker}): {e}")
            raise ValueError(f"가격 히스토리 조회 실패: {e}")

    async def get_financial_data(self, ticker: str) -> Dict:
        """
        재무 데이터 조회 (pykrx + DART API 통합)

        Args:
            ticker: 종목 코드

        Returns:
            {
                'bps': float,  # 주당순자산가치
                'per': float,  # PER
                'pbr': float,  # PBR
                'eps': float,  # 주당순이익
                'div': float,  # 배당수익률
                'dps': float,  # 주당배당금
                'roe': float,  # ROE (%)
                'debt_ratio': float,  # 부채비율 (%)
                'revenue_growth_yoy': float  # 매출 성장률 (%)
            }

        Example:
            >>> financial = await service.get_financial_data('005930')
            >>> print(financial['per'], financial['pbr'])
        """
        # 1. DB에서 먼저 조회
        try:
            from app.db.database import get_db
            from app.db.models import FinancialData

            with get_db() as db:
                financial_data = db.query(FinancialData).filter_by(ticker=ticker).first()

                if financial_data:
                    return {
                        'bps': financial_data.bps,
                        'per': financial_data.per,
                        'pbr': financial_data.pbr,
                        'eps': financial_data.eps,
                        'div': financial_data.div,
                        'dps': financial_data.dps,
                        'roe': financial_data.roe,
                        'debt_ratio': financial_data.debt_ratio,
                        'revenue_growth_yoy': financial_data.revenue_growth_yoy
                    }

        except Exception as e:
            logger.debug(f"{ticker}: DB 조회 실패 ({e}), API 조회 시도")

        # 2. pykrx로 기본 재무 데이터 조회
        pykrx_data = await self._get_pykrx_financial_data(ticker)

        # 3. DART API로 부채비율, 매출성장률 조회
        dart_data = await self._get_dart_financial_ratios(ticker)

        # 4. 결과 병합
        result = {**pykrx_data, **dart_data}

        logger.info(f"{ticker}: 재무 데이터 조회 완료 - PER: {result['per']}, PBR: {result['pbr']}, ROE: {result['roe']}%")
        return result

    async def _get_pykrx_financial_data(self, ticker: str) -> Dict:
        """pykrx로 BPS, PER, PBR, EPS, DIV, DPS 조회"""
        try:
            # 주말/휴장일 대비 이전 거래일 조회
            current_date = datetime.now()

            for attempt in range(10):  # 최대 10일 전까지
                check_date = current_date - timedelta(days=attempt)

                # 주말 건너뛰기
                if check_date.weekday() >= 5:
                    continue

                date_str = check_date.strftime("%Y%m%d")

                try:
                    # pykrx get_market_fundamental: BPS, PER, PBR, EPS, DIV, DPS
                    df = await asyncio.to_thread(
                        stock.get_market_fundamental,
                        date_str,
                        date_str,
                        ticker
                    )

                    if df is None or df.empty:
                        continue

                    # 데이터 추출 (소수점 둘째자리까지)
                    row = df.iloc[0]
                    bps = round(float(row['BPS']), 2) if pd.notna(row['BPS']) else 0.0
                    per = round(float(row['PER']), 2) if pd.notna(row['PER']) else 0.0
                    pbr = round(float(row['PBR']), 2) if pd.notna(row['PBR']) else 0.0
                    eps = round(float(row['EPS']), 2) if pd.notna(row['EPS']) else 0.0
                    div = round(float(row['DIV']), 2) if pd.notna(row['DIV']) else 0.0
                    dps = round(float(row['DPS']), 2) if pd.notna(row['DPS']) else 0.0

                    # PER, PBR이 0이 아니면 성공
                    if per > 0 or pbr > 0 or bps > 0:
                        # ROE = EPS / BPS * 100
                        roe = round((eps / bps * 100), 2) if bps > 0 and eps > 0 else 0.0

                        logger.debug(f"{ticker}: pykrx 조회 성공 ({date_str})")
                        return {
                            'bps': bps,
                            'per': per,
                            'pbr': pbr,
                            'eps': eps,
                            'div': div,
                            'dps': dps,
                            'roe': roe
                        }
                except Exception as e:
                    logger.debug(f"{ticker}: {date_str} pykrx 조회 실패 - {e}")
                    continue

            logger.warning(f"{ticker}: pykrx 조회 실패 (10일 내 거래일 없음)")
            return {
                'bps': 0.0, 'per': 0.0, 'pbr': 0.0,
                'eps': 0.0, 'div': 0.0, 'dps': 0.0, 'roe': 0.0
            }

        except Exception as e:
            logger.error(f"{ticker}: pykrx 조회 실패 - {e}")
            return {
                'bps': 0.0, 'per': 0.0, 'pbr': 0.0,
                'eps': 0.0, 'div': 0.0, 'dps': 0.0, 'roe': 0.0
            }

    async def _get_dart_financial_ratios(self, ticker: str) -> Dict:
        """DART API로 부채비율, 매출성장률 조회"""
        if not self.dart:
            return {'debt_ratio': 0.0, 'revenue_growth_yoy': 0.0}

        try:
            # 사업보고서는 3월 말에 제출됨
            # year-1 먼저 시도, 없으면 year-2로 fallback
            current_year = datetime.now().year
            years_to_try = [current_year - 1, current_year - 2]

            df = None
            for year in years_to_try:
                df = await asyncio.to_thread(
                    self.dart.finstate,
                    ticker,
                    year,
                    reprt_code='11011'  # 사업보고서
                )
                if df is not None and not df.empty:
                    break

            if df is None or df.empty:
                return {'debt_ratio': 0.0, 'revenue_growth_yoy': 0.0}

            # 재무 계정 추출
            financial_accounts = self._extract_financial_accounts(df)

            # 지표 계산
            total_equity = financial_accounts.get('total_equity', 0)
            total_liabilities = financial_accounts.get('total_liabilities', 0)
            revenue = financial_accounts.get('revenue', 0)
            revenue_prev = financial_accounts.get('revenue_prev', 0)

            # 부채비율 = (부채총계 / 자본총계) × 100
            debt_ratio = round((total_liabilities / total_equity * 100), 2) if total_equity > 0 else 0.0

            # 매출 성장률 = ((당기 - 전기) / 전기) × 100
            revenue_growth_yoy = round(((revenue - revenue_prev) / revenue_prev * 100), 2) if revenue_prev > 0 else 0.0

            logger.debug(f"{ticker}: DART 조회 성공 - 부채비율: {debt_ratio}%, 매출성장: {revenue_growth_yoy}%")
            return {
                'debt_ratio': debt_ratio,
                'revenue_growth_yoy': revenue_growth_yoy
            }

        except Exception as e:
            logger.debug(f"{ticker}: DART 조회 실패 - {e}")
            return {'debt_ratio': 0.0, 'revenue_growth_yoy': 0.0}

    def _get_default_financial_data(self) -> Dict:
        """기본 재무 데이터 반환"""
        return {
            'bps': 0.0,
            'per': 0.0,
            'pbr': 0.0,
            'eps': 0.0,
            'div': 0.0,
            'dps': 0.0,
            'roe': 0.0,
            'debt_ratio': 0.0,
            'revenue_growth_yoy': 0.0
        }

    def _extract_financial_accounts(self, df: pd.DataFrame) -> Dict:
        """
        DART DataFrame에서 재무 계정 추출

        Args:
            df: DART API finstate() 결과

        Returns:
            {
                'total_equity': int,      # 자본총계
                'net_income': int,        # 당기순이익
                'total_liabilities': int, # 부채총계
                'revenue': int,           # 매출액 (당기)
                'revenue_prev': int       # 매출액 (전기)
            }
        """
        try:
            # None 체크 및 필수 컬럼 확인
            if df is None or df.empty or 'fs_div' not in df.columns:
                logger.warning("재무제표 데이터가 없거나 형식이 잘못되었습니다")
                return self._get_default_accounts()

            # 연결재무제표 우선, 없으면 별도재무제표 사용
            df_cfs = df[df['fs_div'] == 'CFS']  # Consolidated Financial Statements
            if df_cfs.empty:
                df_cfs = df[df['fs_div'] == 'OFS']  # Separate Financial Statements

            if df_cfs.empty:
                logger.warning("재무제표 데이터가 없습니다")
                return self._get_default_accounts()

            # 계정명 -> 당기금액 매핑
            accounts = {}
            for _, row in df_cfs.iterrows():
                account_name = row['account_nm']
                try:
                    # 쉼표 제거 후 int 변환
                    thstrm_str = str(row['thstrm_amount']).replace(',', '') if pd.notna(row['thstrm_amount']) else '0'
                    frmtrm_str = str(row['frmtrm_amount']).replace(',', '') if pd.notna(row['frmtrm_amount']) else '0'
                    amount = int(thstrm_str)
                    prev_amount = int(frmtrm_str)
                except (ValueError, TypeError):
                    amount = 0
                    prev_amount = 0

                accounts[account_name] = {
                    'current': amount,
                    'previous': prev_amount
                }

            # 필요한 계정 추출 (계정명은 정확히 매칭되어야 함)
            result = {
                'total_equity': accounts.get('자본총계', {}).get('current', 0),
                'net_income': accounts.get('당기순이익(손실)', {}).get('current', 0),
                'total_liabilities': accounts.get('부채총계', {}).get('current', 0),
                'revenue': accounts.get('매출액', {}).get('current', 0),
                'revenue_prev': accounts.get('매출액', {}).get('previous', 0)
            }

            logger.debug(f"재무 계정 추출 완료: {result}")
            return result

        except Exception as e:
            logger.error(f"재무 계정 추출 실패: {e}")
            return self._get_default_accounts()

    def _get_default_accounts(self) -> Dict:
        """기본 재무 계정 반환"""
        return {
            'total_equity': 0,
            'net_income': 0,
            'total_liabilities': 0,
            'revenue': 0,
            'revenue_prev': 0
        }

    async def get_news_data(self, ticker: str, days: int = 7) -> List[Dict]:
        """
        종목 관련 뉴스 조회 (네이버 금융 + Google News RSS)
        중복 제거는 외부 SentenceTransformer 파이프라인에서 수행

        네이버 금융 크롤링 시 주의사항:
        1. 메인 페이지를 먼저 방문해서 쿠키 획득
        2. Referer 헤더 설정 필수
        3. 상세한 브라우저 헤더 사용
        """
        import httpx
        from bs4 import BeautifulSoup
        from datetime import datetime, timedelta
        import feedparser
        from app.utils.krx_data_client import stock as pykrx_stock

        news_list = []

        # =====================================================================
        # 1) 네이버 금융 뉴스 크롤링
        # =====================================================================

        # 브라우저와 동일한 헤더 (중요!)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': f'https://finance.naver.com/item/main.nhn?code={ticker}',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'iframe',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0'
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # STEP 1: 메인 페이지 방문해서 쿠키 획득 (중요!)
                main_url = f'https://finance.naver.com/item/main.nhn?code={ticker}'
                await client.get(main_url, headers=headers)

                # STEP 2: 뉴스 페이지 크롤링 (1~10페이지)
                for page_num in range(1, 11):
                    url = f"https://finance.naver.com/item/news_news.nhn?code={ticker}&page={page_num}&sm=title_entity_id.basic&clusterId="

                    response = await client.get(url, headers=headers)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.content, 'html.parser')

                    # td.title 찾기
                    title_tds = soup.find_all('td', {'class': 'title'})

                    for td in title_tds:
                        link = td.find('a')
                        if not link:
                            continue

                        title = link.get_text(strip=True)
                        href = link.get('href', '')

                        # 부모 tr에서 날짜와 출처 찾기
                        parent_tr = td.find_parent('tr')
                        if not parent_tr:
                            continue

                        date_td = parent_tr.find('td', {'class': 'date'})
                        info_td = parent_tr.find('td', {'class': 'info'})

                        # 날짜 파싱
                        if date_td:
                            date_str = date_td.get_text(strip=True)
                            try:
                                published_at = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
                            except ValueError:
                                published_at = datetime.now()
                        else:
                            published_at = datetime.now()

                        source = info_td.get_text(strip=True) if info_td else '네이버 금융'

                        news_list.append({
                            'title': title,
                            'content': title,  # 제목을 content로도 사용
                            'published_at': published_at,
                            'source': source,
                            'url': f"https://finance.naver.com{href}" if href.startswith('/') else href
                        })

        except Exception as e:
            logger.error(f"[NAVER] 뉴스 크롤링 오류: {e}")

        # =====================================================================
        # 2) Google News RSS 파싱 추가
        # =====================================================================

        try:
            # 종목명 조회 (더 정확한 검색을 위해)
            try:
                stock_name = pykrx_stock.get_market_ticker_name(ticker)
            except:
                stock_name = ticker

            # Google RSS는 검색 기반으로 가져온다 (종목명 + 주식)
            rss_url = f"https://news.google.com/rss/search?q={stock_name}&hl=ko&gl=KR&ceid=KR:ko"

            feed = feedparser.parse(rss_url)

            for entry in feed.entries:
                title = entry.title
                url = entry.link
                published_at = datetime(*entry.published_parsed[:6]) if 'published_parsed' in entry else datetime.now()

                # 최근 days 이내 기사만 사용
                if published_at < datetime.now() - timedelta(days=days):
                    continue

                news_list.append({
                    'title': title,
                    'content': entry.get("summary", title),
                    'published_at': published_at,
                    'source': entry.get("source", {}).get("title", "Google News"),
                    'url': url
                })

        except Exception as e:
            logger.error(f"[GOOGLE RSS] 뉴스 파싱 오류: {e}")

        news_list.sort(key=lambda x: x['published_at'], reverse=True)

        logger.info(f"뉴스 수집 완료: 네이버 금융 + Google News, 총 {len(news_list)}개")

        return news_list

    async def get_technical_indicators(
        self,
        ticker: str,
        date: datetime
    ) -> Dict:
        """
        기술적 지표 계산

        Args:
            ticker: 종목 코드
            date: 기준일

        Returns:
            {
                'rsi': float,  # RSI (0-100)
                'macd': float,
                'macd_signal': float,
                'macd_status': str,  # 'golden_cross', 'dead_cross', 'neutral'
                'ma5': float,  # 5일 이동평균
                'ma20': float,  # 20일 이동평균
                'ma60': float,  # 60일 이동평균
                'ma_position': str  # '상회', '하회', '중립'
            }

        Example:
            >>> indicators = await service.get_technical_indicators(
            ...     '005930',
            ...     datetime(2025, 11, 6)
            ... )
        """
        from app.utils.metrics import MetricsCalculator
        from datetime import timedelta

        try:
            # 60개 거래일 확보를 위해 100일치 조회 (주말/휴일 고려)
            start_date = date - timedelta(days=100)
            prices_df = await self.get_price_history(ticker, start_date)

            if prices_df.empty or len(prices_df) < 14:
                logger.warning(f"{ticker}: 기술적 지표 계산을 위한 데이터 부족 (len={len(prices_df)})")
                return self._get_default_technical_indicators()

            # 종가 Series 추출 (krx_data_client는 영문 컬럼 반환)
            prices = prices_df['Close']
            current_price = float(prices.iloc[-1])

            # RSI 계산
            rsi = MetricsCalculator.calculate_rsi(prices, period=14)

            # MACD 계산
            macd_result = MetricsCalculator.calculate_macd(prices)

            # 이동평균 계산
            moving_averages = MetricsCalculator.calculate_moving_averages(
                prices,
                periods=[5, 20, 60]
            )

            # MA 위치 판단 (현재가 vs MA20)
            ma20 = moving_averages[20]
            if current_price > ma20 * 1.02:
                ma_position = '상회'
            elif current_price < ma20 * 0.98:
                ma_position = '하회'
            else:
                ma_position = '중립'

            result = {
                'rsi': round(rsi, 2),
                'macd': round(macd_result['macd'], 4),
                'macd_signal': round(macd_result['signal'], 4),
                'macd_status': macd_result['status'],
                'ma5': round(moving_averages[5], 2),
                'ma20': round(moving_averages[20], 2),
                'ma60': round(moving_averages[60], 2),
                'ma_position': ma_position
            }

            logger.info(f"{ticker}: 기술적 지표 계산 완료 - RSI={rsi:.1f}, MACD={macd_result['status']}")
            return result

        except Exception as e:
            logger.error(f"{ticker}: 기술적 지표 계산 중 오류 - {e}")
            return self._get_default_technical_indicators()

    def _get_default_technical_indicators(self) -> Dict:
        """기술적 지표 기본값 반환"""
        return {
            'rsi': 50.0,
            'macd': 0.0,
            'macd_signal': 0.0,
            'macd_status': 'neutral',
            'ma5': 0.0,
            'ma20': 0.0,
            'ma60': 0.0,
            'ma_position': '중립'
        }

    async def get_technical_indicators_batch(
        self,
        tickers: List[str],
        date: datetime,
        batch_size: int = 50
    ) -> pd.DataFrame:
        """
        배치 기술적 지표 계산 (700개 종목을 50개씩 병렬 처리)

        Args:
            tickers: 종목 코드 리스트
            date: 기준일
            batch_size: 배치 크기 (기본값: 50)

        Returns:
            DataFrame with columns:
            - ticker: 종목 코드 (인덱스)
            - rsi: RSI (0-100)
            - macd: MACD
            - macd_signal: MACD Signal
            - macd_status: 'golden_cross', 'dead_cross', 'neutral'
            - ma5, ma20, ma60: 이동평균
            - ma_position: '상회', '하회', '중립'

        Example:
            >>> service = DataService()
            >>> tech_df = await service.get_technical_indicators_batch(
            ...     ['005930', '000660', ...],
            ...     datetime(2025, 11, 6)
            ... )
        """
        logger.info(f"배치 기술적 지표 계산 시작: {len(tickers)}개 종목")

        # 배치로 나눠서 처리
        results = []
        total_batches = (len(tickers) + batch_size - 1) // batch_size

        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            batch_num = i // batch_size + 1
            logger.info(f"배치 {batch_num}/{total_batches} 처리 중 ({len(batch)}개 종목)...")

            # 병렬 처리
            tasks = [self.get_technical_indicators(ticker, date) for ticker in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 수집
            for ticker, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning(f"{ticker}: 기술적 지표 계산 실패 - {result}, 기본값 사용")
                    result = self._get_default_technical_indicators()

                results.append({
                    'ticker': ticker,
                    **result
                })

        # DataFrame 변환
        df = pd.DataFrame(results)
        df.set_index('ticker', inplace=True)

        logger.info(f"배치 기술적 지표 계산 완료: {len(df)}개 종목")
        return df

    async def get_market_index(self, date: datetime) -> Dict:
        """
        시장 지수 조회 (KOSPI + KOSDAQ + 개인수급 + 시장폭)

        Args:
            date: 조회일

        Returns:
            {
                # KOSPI
                'kospi_close': float,           # KOSPI 종가
                'kospi_change': float,          # KOSPI 등락률 (%)
                'kospi_point_change': float,    # KOSPI 포인트 변동

                # KOSDAQ
                'kosdaq_close': float,          # KOSDAQ 종가
                'kosdaq_change': float,         # KOSDAQ 등락률 (%)
                'kosdaq_point_change': float,   # KOSDAQ 포인트 변동

                # 거래대금
                'trading_value': int,           # 전체 거래대금 (원)
                'trading_value_kospi': int,     # KOSPI 거래대금 (원)
                'trading_value_kosdaq': int,    # KOSDAQ 거래대금 (원)

                # 수급 - KOSPI
                'foreign_net_kospi': int,       # 외국인 순매수 (KOSPI)
                'institution_net_kospi': int,   # 기관 순매수 (KOSPI)
                'individual_net_kospi': int,    # 개인 순매수 (KOSPI)

                # 수급 - KOSDAQ
                'foreign_net_kosdaq': int,      # 외국인 순매수 (KOSDAQ)
                'institution_net_kosdaq': int,  # 기관 순매수 (KOSDAQ)
                'individual_net_kosdaq': int,   # 개인 순매수 (KOSDAQ)

                # 시장 폭 (Market Breadth)
                'advance_count': int,           # 상승 종목 수
                'decline_count': int,           # 하락 종목 수
                'unchanged_count': int,         # 보합 종목 수

                # 호환성 (레거시)
                'foreign_net': int,             # 외국인 순매수 합계
                'institution_net': int          # 기관 순매수 합계
            }

        Example:
            >>> index = await service.get_market_index(datetime(2025, 11, 6))
        """
        try:
            date_str = date.strftime("%Y%m%d")
            prev_date = await self.get_previous_trading_day(date)
            prev_date_str = prev_date.strftime("%Y%m%d")

            result = self._get_default_market_index()

            # ==================== KOSPI 지수 ====================
            try:
                kospi_df = await asyncio.to_thread(
                    stock.get_index_ohlcv_by_date,
                    prev_date_str,
                    date_str,
                    "1001"  # KOSPI 코드
                )

                if not kospi_df.empty and len(kospi_df) > 0:
                    current = kospi_df.iloc[-1]
                    kospi_close = float(current['종가'])
                    result['kospi_close'] = round(kospi_close, 2)
                    result['trading_value_kospi'] = int(current['거래대금'])

                    if len(kospi_df) >= 2:
                        prev_close = float(kospi_df.iloc[-2]['종가'])
                        result['kospi_change'] = round(((kospi_close / prev_close) - 1) * 100, 2)
                        result['kospi_point_change'] = round(kospi_close - prev_close, 2)
            except Exception as e:
                logger.warning(f"KOSPI 지수 조회 실패: {e}")

            # ==================== KOSDAQ 지수 ====================
            try:
                kosdaq_df = await asyncio.to_thread(
                    stock.get_index_ohlcv_by_date,
                    prev_date_str,
                    date_str,
                    "2001"  # KOSDAQ 코드
                )

                if not kosdaq_df.empty and len(kosdaq_df) > 0:
                    current = kosdaq_df.iloc[-1]
                    kosdaq_close = float(current['종가'])
                    result['kosdaq_close'] = round(kosdaq_close, 2)
                    result['trading_value_kosdaq'] = int(current['거래대금'])

                    if len(kosdaq_df) >= 2:
                        prev_close = float(kosdaq_df.iloc[-2]['종가'])
                        result['kosdaq_change'] = round(((kosdaq_close / prev_close) - 1) * 100, 2)
                        result['kosdaq_point_change'] = round(kosdaq_close - prev_close, 2)
            except Exception as e:
                logger.warning(f"KOSDAQ 지수 조회 실패: {e}")

            # 전체 거래대금
            result['trading_value'] = result['trading_value_kospi'] + result['trading_value_kosdaq']

            # ==================== 수급 - KOSPI ====================
            try:
                kospi_trading_df = await asyncio.to_thread(
                    stock.get_market_trading_value_by_investor,
                    date_str,
                    date_str,
                    "KOSPI"
                )

                if not kospi_trading_df.empty:
                    if '외국인' in kospi_trading_df.index:
                        result['foreign_net_kospi'] = int(kospi_trading_df.loc['외국인', '순매수'])
                    if '기관합계' in kospi_trading_df.index:
                        result['institution_net_kospi'] = int(kospi_trading_df.loc['기관합계', '순매수'])
                    if '개인' in kospi_trading_df.index:
                        result['individual_net_kospi'] = int(kospi_trading_df.loc['개인', '순매수'])
            except Exception as e:
                logger.warning(f"KOSPI 수급 조회 실패: {e}")

            # ==================== 수급 - KOSDAQ ====================
            try:
                kosdaq_trading_df = await asyncio.to_thread(
                    stock.get_market_trading_value_by_investor,
                    date_str,
                    date_str,
                    "KOSDAQ"
                )

                if not kosdaq_trading_df.empty:
                    if '외국인' in kosdaq_trading_df.index:
                        result['foreign_net_kosdaq'] = int(kosdaq_trading_df.loc['외국인', '순매수'])
                    if '기관합계' in kosdaq_trading_df.index:
                        result['institution_net_kosdaq'] = int(kosdaq_trading_df.loc['기관합계', '순매수'])
                    if '개인' in kosdaq_trading_df.index:
                        result['individual_net_kosdaq'] = int(kosdaq_trading_df.loc['개인', '순매수'])
            except Exception as e:
                logger.warning(f"KOSDAQ 수급 조회 실패: {e}")

            # 호환성: 합계 계산 (레거시 코드 지원)
            result['foreign_net'] = result['foreign_net_kospi'] + result['foreign_net_kosdaq']
            result['institution_net'] = result['institution_net_kospi'] + result['institution_net_kosdaq']

            # ==================== 시장 폭 (Market Breadth) ====================
            try:
                # 전체 시장 OHLCV 조회
                ohlcv_df = await asyncio.to_thread(
                    stock.get_market_ohlcv_by_ticker,
                    date_str,
                    market="ALL"
                )

                if not ohlcv_df.empty:
                    # 등락률 기준으로 상승/하락/보합 분류
                    if '등락률' in ohlcv_df.columns:
                        result['advance_count'] = int((ohlcv_df['등락률'] > 0).sum())
                        result['decline_count'] = int((ohlcv_df['등락률'] < 0).sum())
                        result['unchanged_count'] = int((ohlcv_df['등락률'] == 0).sum())
                    else:
                        # 등락률 컬럼이 없으면 시가/종가로 계산
                        changes = ohlcv_df['종가'] - ohlcv_df['시가']
                        result['advance_count'] = int((changes > 0).sum())
                        result['decline_count'] = int((changes < 0).sum())
                        result['unchanged_count'] = int((changes == 0).sum())
            except Exception as e:
                logger.warning(f"시장 폭 조회 실패: {e}")

            logger.info(f"{date_str}: 시장 지수 조회 완료 - "
                       f"KOSPI {result['kospi_close']:.2f} ({result['kospi_change']:+.2f}%), "
                       f"KOSDAQ {result['kosdaq_close']:.2f} ({result['kosdaq_change']:+.2f}%)")
            return result

        except Exception as e:
            logger.error(f"시장 지수 조회 중 오류: {e}")
            return self._get_default_market_index()

    def _get_default_market_index(self) -> Dict:
        """시장 지수 기본값 반환"""
        return {
            # KOSPI
            'kospi_close': 0.0,
            'kospi_change': 0.0,
            'kospi_point_change': 0.0,
            # KOSDAQ
            'kosdaq_close': 0.0,
            'kosdaq_change': 0.0,
            'kosdaq_point_change': 0.0,
            # 거래대금
            'trading_value': 0,
            'trading_value_kospi': 0,
            'trading_value_kosdaq': 0,
            # 수급 - KOSPI
            'foreign_net_kospi': 0,
            'institution_net_kospi': 0,
            'individual_net_kospi': 0,
            # 수급 - KOSDAQ
            'foreign_net_kosdaq': 0,
            'institution_net_kosdaq': 0,
            'individual_net_kosdaq': 0,
            # 시장 폭
            'advance_count': 0,
            'decline_count': 0,
            'unchanged_count': 0,
            # 호환성 (레거시)
            'foreign_net': 0,
            'institution_net': 0
        }

    # ==================== 헬퍼 함수 ====================

    def _retry_request(self, func, attempts: int = None):
        """
        재시도 로직 (pykrx 웹 스크래핑 안정성 향상)

        Args:
            func: 실행할 함수
            attempts: 재시도 횟수 (기본값: self.retry_attempts)

        Returns:
            함수 실행 결과

        Raises:
            마지막 시도에서 발생한 예외
        """
        attempts = attempts or self.retry_attempts

        for i in range(attempts):
            try:
                return func()
            except Exception as e:
                if i == attempts - 1:
                    # 마지막 시도 실패
                    raise
                logger.warning(f"재시도 {i + 1}/{attempts}: {e}")
                time.sleep(self.retry_delay)

    @lru_cache(maxsize=100)
    def _get_market_type(self, ticker: str) -> str:
        """
        종목의 시장 구분 확인 (KOSPI/KOSDAQ)

        Args:
            ticker: 종목 코드

        Returns:
            'KOSPI' or 'KOSDAQ'
        """
        # 최근 10일 내 거래일에서 확인
        today = datetime.now()

        for i in range(10):
            try_date = (today - timedelta(days=i)).strftime("%Y%m%d")

            try:
                # KOSPI 확인
                kospi_tickers = stock.get_market_ticker_list(try_date, market="KOSPI")
                if len(kospi_tickers) > 0:  # 휴장일이 아님
                    if ticker in list(kospi_tickers):  # 리스트로 변환
                        return "KOSPI"

                    # KOSDAQ 확인
                    kosdaq_tickers = stock.get_market_ticker_list(try_date, market="KOSDAQ")
                    if ticker in list(kosdaq_tickers):  # 리스트로 변환
                        return "KOSDAQ"

                    # 찾았지만 둘 다 아님 - 기본값 반환
                    logger.warning(f"{ticker}의 시장 구분을 찾을 수 없습니다 ({try_date}). 기본값 KOSPI")
                    return "KOSPI"

            except Exception as e:
                logger.debug(f"{try_date} 시장 구분 확인 실패: {e}")
                continue

        # 10일 내 거래일 없음
        logger.warning(f"{ticker}: 시장 구분 확인 실패 (거래일 없음). 기본값 KOSPI")
        return "KOSPI"

    async def get_previous_trading_day(self, date: datetime, max_days: int = 10) -> datetime:
        """
        전 거래일 찾기 (주말, 휴장일 건너뛰기)

        Args:
            date: 기준일
            max_days: 최대 탐색 일수 (기본값: 10일)

        Returns:
            전 거래일

        Raises:
            ValueError: 전 거래일을 찾을 수 없는 경우

        Example:
            월요일(11/10) → 금요일(11/08) 반환
            화요일(11/11) → 월요일(11/10) 반환
        """
        for i in range(1, max_days + 1):
            prev_date = date - timedelta(days=i)

            # 1차 필터: 주말 체크 (토요일=5, 일요일=6)
            if prev_date.weekday() >= 5:
                logger.debug(f"{prev_date.strftime('%Y-%m-%d')} - 주말, 건너뜀")
                continue

            date_str = prev_date.strftime("%Y%m%d")

            try:
                # 2차 필터: pykrx로 데이터 조회
                data = stock.get_market_ohlcv_by_ticker(date_str, market="KOSPI")

                # 3차 필터: DataFrame이 비어있는지
                if data.empty:
                    logger.debug(f"{date_str} - 데이터 없음, 건너뜀")
                    continue

                # 4차 필터: 실제 거래가 있었는지 확인 (모든 값이 0이면 휴장일)
                # 종가 합계가 0보다 크고, 거래량 합계가 0보다 크면 거래일
                if data['종가'].sum() > 0 and data['거래량'].sum() > 0:
                    logger.info(f"전 거래일 찾음: {date_str} ({prev_date.strftime('%A')})")
                    return prev_date
                else:
                    logger.debug(f"{date_str} - 거래 없음 (휴장일), 건너뜀")
                    continue

            except Exception as e:
                logger.warning(f"{date_str} - 조회 실패: {e}")
                continue

        raise ValueError(f"{date.strftime('%Y-%m-%d')} 이전 {max_days}일 내에 거래일을 찾을 수 없습니다")

    # ==================== ATR 계산 ====================

    async def calculate_atr(
        self,
        ticker: str,
        date: datetime,
        period: int = 14
    ) -> Optional[float]:
        """
        Average True Range (ATR) 계산

        ATR은 변동성 지표로, 목표가/손절가 설정에 사용됩니다.
        TR = max(High - Low, |High - Prev Close|, |Low - Prev Close|)
        ATR = SMA(TR, period)

        Args:
            ticker: 종목 코드
            date: 기준 날짜
            period: ATR 계산 기간 (기본 14일)

        Returns:
            ATR 값 (원 단위) or None if calculation failed

        Example:
            >>> atr = await service.calculate_atr('005930', datetime.now())
            >>> print(f"ATR: {atr:,}원")
        """
        try:
            # 과거 데이터 조회 (period + 여유분)
            end_date = date
            start_date = date - timedelta(days=period * 3)  # 거래일 확보를 위해 3배

            end_str = end_date.strftime("%Y%m%d")
            start_str = start_date.strftime("%Y%m%d")

            # pykrx OHLCV 조회
            df_ohlcv = await asyncio.to_thread(
                stock.get_market_ohlcv_by_date,
                start_str,
                end_str,
                ticker
            )

            if df_ohlcv.empty or len(df_ohlcv) < period + 1:
                logger.warning(f"{ticker}: ATR 계산 불가 (데이터 부족: {len(df_ohlcv)}일, 필요: {period + 1}일)")
                return None

            # 최신 데이터부터 period+1개 선택
            df_ohlcv = df_ohlcv.tail(period + 1)

            # True Range 계산 (krx_data_client는 영문 컬럼 반환)
            high = df_ohlcv['High'].values
            low = df_ohlcv['Low'].values
            close = df_ohlcv['Close'].values

            tr_list = []
            for i in range(1, len(df_ohlcv)):
                h_l = high[i] - low[i]
                h_pc = abs(high[i] - close[i - 1])
                l_pc = abs(low[i] - close[i - 1])
                tr = max(h_l, h_pc, l_pc)
                tr_list.append(tr)

            # ATR = 평균 (최근 period개)
            if len(tr_list) < period:
                logger.warning(f"{ticker}: TR 계산 부족 ({len(tr_list)}/{period})")
                return None

            atr_value = sum(tr_list[-period:]) / period

            logger.debug(f"{ticker}: ATR({period}) = {atr_value:,.0f}원")
            return round(atr_value, 2)

        except Exception as e:
            logger.error(f"{ticker}: ATR 계산 실패 - {e}")
            return None

    async def get_atr_batch(
        self,
        tickers: List[str],
        date: datetime,
        period: int = 14
    ) -> Dict[str, Optional[float]]:
        """
        여러 종목의 ATR 배치 조회 (병렬 처리)

        Args:
            tickers: 종목 코드 리스트
            date: 기준 날짜
            period: ATR 기간

        Returns:
            {ticker: atr_value} (None이면 계산 실패)

        Example:
            >>> atr_data = await service.get_atr_batch(['005930', '000660'], datetime.now())
            >>> print(atr_data)  # {'005930': 1500.0, '000660': 2300.0}
        """
        logger.info(f"ATR 배치 조회 시작: {len(tickers)}개 종목 (period={period})")

        # 병렬 처리
        tasks = [self.calculate_atr(ticker, date, period) for ticker in tickers]
        atr_values = await asyncio.gather(*tasks, return_exceptions=True)

        result = {}
        success_count = 0

        for ticker, atr in zip(tickers, atr_values):
            if isinstance(atr, Exception):
                logger.error(f"{ticker}: ATR 조회 오류 - {atr}")
                result[ticker] = None
            else:
                result[ticker] = atr
                if atr is not None:
                    success_count += 1

        logger.info(f"ATR 배치 조회 완료: {success_count}/{len(tickers)}개 성공")
        return result
