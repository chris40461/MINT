"""
KIS REST API Client

한국투자증권 REST API를 사용하여 멀티종목 시세를 조회합니다.

Features:
- OAuth 토큰 발급/갱신 (24시간 유효)
- 멀티종목 시세조회 (최대 30개/호출)
- API 호출 제한 준수 (초당 2건)
- 에러 핸들링 및 재시도
"""

import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)


class KISRestClient:
    """KIS REST API 클라이언트"""

    def __init__(self):
        self.base_url = settings.KIS_BASE_URL
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self.is_mock = settings.KIS_IS_MOCK

        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def get_access_token(self) -> str:
        """
        OAuth 토큰 발급/갱신

        Returns:
            액세스 토큰

        Raises:
            Exception: 토큰 발급 실패
        """
        # 토큰이 유효하면 재사용
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at - timedelta(hours=1):
                logger.debug("기존 토큰 사용")
                return self.access_token

        # 새 토큰 발급
        logger.info("🔑 OAuth 토큰 발급 중...")

        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()

            # OAuth tokenP API는 rt_cd 없이 access_token만 반환
            if "access_token" not in data:
                raise Exception(f"토큰 발급 실패: access_token 필드 없음 - {data}")

            self.access_token = data["access_token"]
            # 토큰 유효기간: 24시간 (여유 1시간)
            self.token_expires_at = datetime.now() + timedelta(hours=23)

            logger.info(f"✅ OAuth 토큰 발급 완료 (만료: {self.token_expires_at.strftime('%Y-%m-%d %H:%M')})")
            return self.access_token

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ 토큰 발급 HTTP 에러: {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ 토큰 발급 실패: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_multi_quote(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        멀티종목 시세조회 (최대 30개) - 관심종목 API 사용

        Args:
            tickers: 종목 코드 리스트 (최대 30개)

        Returns:
            {
                '005930': {
                    'current_price': 70000,
                    'change_rate': 2.5,
                    'change_amount': 1700,
                    'volume': 1000000,
                    'open_price': 68300,
                    'high_price': 70500,
                    'low_price': 68000,
                    'trading_value': 70000000000,
                    'market_status': 'open',
                    'updated_at': datetime.now()
                },
                ...
            }

        Raises:
            Exception: API 호출 실패
        """
        if len(tickers) > 30:
            raise ValueError("멀티종목 시세조회는 최대 30개까지 가능합니다")

        # 토큰 확인/갱신
        token = await self.get_access_token()

        # 관심종목(멀티종목) 시세조회 API - 정규장 전용
        # (시간 체크는 polling_manager에서 수행)
        endpoint = "/uapi/domestic-stock/v1/quotations/intstock-multprice"
        tr_id = "FHKST11300006"  # 실전 전용 (모의투자 미지원)

        url = f"{self.base_url}{endpoint}"

        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

        # 각 종목마다 2개의 파라미터 (FID_COND_MRKT_DIV_CODE_N, FID_INPUT_ISCD_N)
        params = {}
        for idx, ticker in enumerate(tickers, start=1):
            params[f"FID_COND_MRKT_DIV_CODE_{idx}"] = "J"  # J=코스피+코스닥+기타
            params[f"FID_INPUT_ISCD_{idx}"] = ticker

        try:
            response = await self.client.get(url, headers=headers, params=params)

            if response.status_code != 200:
                logger.error(f"API 응답 실패 ({response.status_code}): {response.text}")

            response.raise_for_status()

            data = response.json()

            # API 응답 확인
            if data.get("rt_cd") != "0":
                error_msg = data.get("msg1", "Unknown error")
                logger.warning(f"⚠️ API 응답 오류: {error_msg}")

                # 에러 코드별 처리
                if "EGW00201" in error_msg or "429" in str(response.status_code):
                    # API 호출 제한 초과
                    logger.error(f"❌ API 호출 제한 초과 (429/EGW00201)")
                    raise httpx.HTTPError(f"API rate limit exceeded: {error_msg}")

                raise Exception(f"API 오류: {error_msg}")

            # 응답 파싱 - 관심종목 API 구조
            result = {}
            output = data.get("output", [])

            if not output:
                logger.warning(f"⚠️ 응답 데이터 없음: {tickers}")
                return result

            # 각 종목 데이터 파싱
            for item in output:
                ticker = item.get("inter_shrn_iscd")  # 관심 단축 종목코드
                if not ticker:
                    continue

                try:
                    # 가격 데이터
                    current_price = int(item.get("inter2_prpr", 0))  # 관심2 현재가
                    change_rate = float(item.get("prdy_ctrt", 0))  # 전일대비율
                    change_amount = int(item.get("inter2_prdy_vrss", 0))  # 관심2 전일대비
                    volume = int(item.get("acml_vol", 0))  # 누적거래량

                    # OHLC
                    open_price = int(item.get("inter2_oprc", 0))  # 관심2 시가
                    high_price = int(item.get("inter2_hgpr", 0))  # 관심2 고가
                    low_price = int(item.get("inter2_lwpr", 0))  # 관심2 저가

                    # 거래 데이터
                    trading_value = int(item.get("acml_tr_pbmn", 0))  # 누적거래대금 (원)

                    # 동시호가 관련 데이터 (08:40~09:00, 15:20~15:30)
                    prev_close_price = int(item.get("inter2_prdy_clpr", 0) or 0)  # 전일 종가
                    expected_diff = int(item.get("intr_antc_cntg_vrss", 0) or 0)  # 예상 체결 대비
                    expected_change_rate = float(item.get("intr_antc_cntg_prdy_ctrt", 0) or 0)  # 예상 등락률
                    expected_volume = int(item.get("intr_antc_vol", 0) or 0)  # 예상 거래량

                    # 시장 상태 판단
                    hour_cls_code = item.get("hour_cls_code", "0")
                    if hour_cls_code == "0":
                        market_status = "open"  # 정규장
                    elif hour_cls_code == "1":
                        market_status = "pre_market"  # 장전
                    elif hour_cls_code == "2":
                        market_status = "after_hours"  # 장후
                    else:
                        market_status = "closed"

                    result[ticker] = {
                        'current_price': current_price,
                        'change_rate': change_rate,
                        'change_amount': change_amount,
                        'volume': volume,
                        'open_price': open_price,
                        'high_price': high_price,
                        'low_price': low_price,
                        'trading_value': trading_value,
                        'market_status': market_status,
                        'updated_at': datetime.now(),
                        # 동시호가용 추가 필드
                        'prev_close_price': prev_close_price,
                        'expected_diff': expected_diff,
                        'expected_change_rate': expected_change_rate,
                        'expected_volume': expected_volume,
                    }

                except (ValueError, KeyError) as e:
                    logger.warning(f"⚠️ {ticker} 데이터 파싱 실패: {e}")
                    continue

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API HTTP 에러: {e.response.status_code}")
            if e.response.status_code == 429:
                logger.error("API 호출 제한 초과 (429)")
            raise
        except httpx.TimeoutException:
            logger.error(f"❌ API 타임아웃")
            raise
        except Exception as e:
            logger.error(f"❌ API 호출 실패: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def get_single_quote_overtime(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        시간외 단일 종목 시세조회

        Args:
            ticker: 종목 코드 (예: '005930')

        Returns:
            {
                'current_price': 70000,
                'change_rate': 2.5,
                'change_amount': 1700,
                'volume': 1000000,
                'open_price': 68300,
                'high_price': 70500,
                'low_price': 68000,
                'trading_value': 0,
                'market_status': 'after_hours',
                'updated_at': datetime.now()
            }
            or None if error

        Raises:
            Exception: API 호출 실패
        """
        # 토큰 확인/갱신
        token = await self.get_access_token()

        # 시간외 시세 API
        endpoint = "/uapi/domestic-stock/v1/quotations/inquire-overtime-price"
        tr_id = "FHPST02300000"  # 실전 전용

        url = f"{self.base_url}{endpoint}"

        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P"
        }

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # J=코스피+코스닥+기타
            "FID_INPUT_ISCD": ticker
        }

        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            # API 응답 확인
            if data.get("rt_cd") != "0":
                error_msg = data.get("msg1", "Unknown error")
                logger.warning(f"⚠️ {ticker} API 응답 오류: {error_msg}")
                return None

            # 응답 파싱 - 시간외 API 구조
            output = data.get("output", {})
            if not output:
                logger.warning(f"⚠️ {ticker} 응답 데이터 없음")
                return None

            try:
                # 가격 데이터 (시간외 필드명)
                current_price = int(output.get("ovtm_untp_prpr", 0))  # 시간외 단일가 현재가
                change_rate = float(output.get("ovtm_untp_prdy_ctrt", 0))  # 전일 대비율
                change_amount = int(output.get("ovtm_untp_prdy_vrss", 0))  # 전일 대비
                volume = int(output.get("ovtm_untp_vol", 0))  # 시간외 거래량

                # OHLC
                open_price = int(output.get("ovtm_untp_oprc", 0))  # 시가
                high_price = int(output.get("ovtm_untp_hgpr", 0))  # 고가
                low_price = int(output.get("ovtm_untp_lwpr", 0))  # 저가

                # 거래 데이터 (시간외는 거래대금 없음)
                trading_value = 0

                # 시간 판별
                now = datetime.now()
                hour = now.hour
                minute = now.minute

                if hour < 9:
                    market_status = "pre_market"  # 장전
                elif 15 <= hour < 18:
                    market_status = "after_hours"  # 장후/시간외
                else:
                    market_status = "closed"

                return {
                    'current_price': current_price,
                    'change_rate': change_rate,
                    'change_amount': change_amount,
                    'volume': volume,
                    'open_price': open_price,
                    'high_price': high_price,
                    'low_price': low_price,
                    'trading_value': trading_value,
                    'market_status': market_status,
                    'updated_at': datetime.now()
                }

            except (ValueError, KeyError) as e:
                logger.warning(f"⚠️ {ticker} 데이터 파싱 실패: {e}")
                return None

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ {ticker} API HTTP 에러: {e.response.status_code}")
            raise
        except httpx.TimeoutException:
            logger.error(f"❌ {ticker} API 타임아웃")
            raise
        except Exception as e:
            logger.error(f"❌ {ticker} API 호출 실패: {e}")
            raise

    async def health_check(self) -> bool:
        """
        API 연결 상태 확인 (간단 체크)

        Returns:
            정상 여부
        """
        # Mock 모드는 항상 성공
        if self.is_mock:
            logger.debug("Mock 모드 - health check 통과")
            return True

        # 실제 모드: 토큰만 확인 (이미 캐싱되어 rate limit 문제 없음)
        try:
            token = await self.get_access_token()
            return bool(token)
        except Exception as e:
            logger.error(f"❌ Health check 실패: {e}")
            return False
