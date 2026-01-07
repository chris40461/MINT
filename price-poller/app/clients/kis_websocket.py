"""
KIS WebSocket Client

한국투자증권 WebSocket API를 사용하여 실시간 시세를 수신합니다.

Features:
- 실시간 체결가 (H0STCNT0)
- 실시간 호가 (H0STASP0)
- Circuit Breaker + Exponential Backoff
- 자동 재연결 및 재구독
- Graceful Degradation (REST API 폴백)

References:
- KIS WebSocket API: https://apiportal.koreainvestment.com
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
"""

import asyncio
import json
import logging
import random
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Callable, Any, Set
from collections import deque

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    ConnectionClosedOK,
    InvalidHandshake,
)

from app.config import settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit Breaker 상태"""
    CLOSED = "closed"       # 정상 동작
    OPEN = "open"           # 장애 감지, 연결 차단
    HALF_OPEN = "half_open" # 복구 시도 중


@dataclass
class WebSocketConfig:
    """WebSocket 설정"""
    # 재연결 설정
    base_delay: float = 1.0           # 초기 대기 시간 (초)
    max_delay: float = 60.0           # 최대 대기 시간
    max_retries: int = 10             # 최대 재시도 횟수
    jitter_factor: float = 0.3        # 랜덤 지터 (30%)

    # Circuit Breaker 설정
    failure_threshold: int = 5        # 연속 실패 시 회로 개방
    recovery_timeout: float = 30.0    # 복구 대기 시간 (초)

    # 구독 제한
    max_subscriptions: int = 40       # 최대 구독 수 (41건 중 체결통보 1건 제외)

    # Heartbeat
    ping_interval: float = 30.0       # Ping 간격
    ping_timeout: float = 10.0        # Ping 타임아웃


@dataclass
class TickerData:
    """실시간 시세 데이터"""
    ticker: str
    timestamp: datetime
    data_type: str  # 'ccnl' or 'asking_price'

    # 체결 데이터 (H0STCNT0)
    current_price: int = 0
    change_rate: float = 0.0
    volume: int = 0                    # 틱 거래량
    acml_vol: int = 0                  # 누적 거래량
    acml_tr_pbmn: int = 0              # 누적 거래대금
    cttr: float = 0.0                  # 체결강도
    shnu_rate: float = 0.0             # 매수비율
    shnu_cntg_smtn: int = 0            # 총 매수 수량
    seln_cntg_smtn: int = 0            # 총 매도 수량
    ccld_dvsn: str = ""                # 체결구분 (1:매수, 5:매도)

    # 호가 데이터 (H0STASP0)
    askp: List[int] = field(default_factory=list)     # 매도호가 1~10
    bidp: List[int] = field(default_factory=list)     # 매수호가 1~10
    askp_rsqn: List[int] = field(default_factory=list)  # 매도호가 잔량 1~10
    bidp_rsqn: List[int] = field(default_factory=list)  # 매수호가 잔량 1~10
    total_askp_rsqn: int = 0           # 총 매도호가 잔량
    total_bidp_rsqn: int = 0           # 총 매수호가 잔량
    antc_cnpr: int = 0                 # 예상 체결가
    antc_cnqn: int = 0                 # 예상 체결량


class KISWebSocketClient:
    """
    KIS WebSocket 클라이언트

    Circuit Breaker + Exponential Backoff을 적용한 안정적인 WebSocket 연결 관리
    """

    # WebSocket URL
    WS_URL_REAL = "ws://ops.koreainvestment.com:21000"
    WS_URL_MOCK = "ws://ops.koreainvestment.com:31000"

    # TR ID
    TR_CCNL = "H0STCNT0"      # 실시간 체결가
    TR_ASKING = "H0STASP0"    # 실시간 호가

    def __init__(
        self,
        app_key: str = None,
        app_secret: str = None,
        is_mock: bool = None,
        config: WebSocketConfig = None,
        on_ccnl: Callable[[TickerData], None] = None,
        on_asking_price: Callable[[TickerData], None] = None,
        on_error: Callable[[Exception], None] = None,
    ):
        """
        초기화

        Args:
            app_key: KIS App Key (기본값: settings에서 가져옴)
            app_secret: KIS App Secret
            is_mock: 모의투자 여부
            config: WebSocket 설정
            on_ccnl: 체결 데이터 콜백
            on_asking_price: 호가 데이터 콜백
            on_error: 에러 콜백
        """
        self.app_key = app_key or settings.KIS_APP_KEY
        self.app_secret = app_secret or settings.KIS_APP_SECRET
        self.is_mock = is_mock if is_mock is not None else settings.KIS_IS_MOCK
        self.config = config or WebSocketConfig()

        # 콜백
        self.on_ccnl = on_ccnl
        self.on_asking_price = on_asking_price
        self.on_error = on_error

        # WebSocket 상태
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.approval_key: Optional[str] = None
        self.connected = False
        self.running = False

        # Circuit Breaker 상태
        self.circuit_state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None

        # 구독 관리
        self.ccnl_subscriptions: Set[str] = set()      # 체결가 구독 종목
        self.asking_subscriptions: Set[str] = set()    # 호가 구독 종목

        # 메시지 처리
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._listen_task: Optional[asyncio.Task] = None
        self._process_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Fallback 모드
        self.fallback_mode = False

        # 메트릭
        self.metrics = {
            'messages_received': 0,
            'reconnections': 0,
            'errors': 0,
            'last_message_at': None,
        }

    @property
    def ws_url(self) -> str:
        """WebSocket URL"""
        return self.WS_URL_MOCK if self.is_mock else self.WS_URL_REAL

    @property
    def total_subscriptions(self) -> int:
        """총 구독 수"""
        return len(self.ccnl_subscriptions) + len(self.asking_subscriptions)

    async def get_approval_key(self) -> str:
        """
        WebSocket 접속키 발급

        Returns:
            approval_key
        """
        import httpx

        base_url = settings.KIS_BASE_URL
        url = f"{base_url}/oauth2/Approval"

        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            approval_key = data.get("approval_key")

            if not approval_key:
                raise Exception(f"approval_key 발급 실패: {data}")

            logger.info(f"WebSocket approval_key 발급 완료")
            return approval_key

    async def connect(self) -> bool:
        """
        WebSocket 연결

        Returns:
            연결 성공 여부
        """
        if self.circuit_state == CircuitState.OPEN:
            await self._check_circuit_recovery()
            if self.circuit_state == CircuitState.OPEN:
                logger.warning("Circuit Breaker OPEN - 연결 시도 차단")
                return False

        try:
            # 1. Approval key 발급
            if not self.approval_key:
                self.approval_key = await self.get_approval_key()

            # 2. WebSocket 연결
            logger.info(f"WebSocket 연결 중... ({self.ws_url})")

            self.ws = await websockets.connect(
                self.ws_url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
            )

            self.connected = True
            self.consecutive_failures = 0
            self.circuit_state = CircuitState.CLOSED

            logger.info(f"WebSocket 연결 성공 (Mock: {self.is_mock})")
            return True

        except Exception as e:
            self.consecutive_failures += 1
            self._update_circuit_state()
            logger.error(f"WebSocket 연결 실패: {e}")

            if self.on_error:
                self.on_error(e)

            return False

    async def connect_with_retry(self) -> bool:
        """
        Exponential Backoff + Jitter로 재연결

        Returns:
            연결 성공 여부
        """
        retries = 0

        while retries < self.config.max_retries:
            try:
                if self.circuit_state == CircuitState.OPEN:
                    await self._check_circuit_recovery()

                if await self.connect():
                    # 재연결 성공 시 이전 구독 복원
                    await self._resubscribe_all()
                    self.metrics['reconnections'] += 1
                    return True

            except Exception as e:
                logger.warning(f"연결 시도 실패: {e}")

            retries += 1

            # Exponential Backoff with Jitter
            delay = min(self.config.base_delay * (2 ** retries), self.config.max_delay)
            jitter = delay * self.config.jitter_factor * random.random()
            wait_time = delay + jitter

            logger.warning(
                f"WebSocket 재연결 대기 ({retries}/{self.config.max_retries}): "
                f"{wait_time:.1f}초"
            )

            await asyncio.sleep(wait_time)

        logger.error("WebSocket 재연결 실패 - 최대 재시도 횟수 초과")
        return False

    def _update_circuit_state(self):
        """Circuit Breaker 상태 업데이트"""
        if self.consecutive_failures >= self.config.failure_threshold:
            self.circuit_state = CircuitState.OPEN
            self.last_failure_time = time.time()
            self.metrics['errors'] += 1
            logger.warning(
                f"Circuit Breaker OPEN - {self.consecutive_failures}회 연속 실패"
            )

    async def _check_circuit_recovery(self):
        """회로 복구 가능 여부 확인"""
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.config.recovery_timeout:
                self.circuit_state = CircuitState.HALF_OPEN
                logger.info("Circuit Breaker HALF_OPEN - 복구 시도 중")

    async def _resubscribe_all(self):
        """연결 복구 후 이전 구독 복원"""
        total = len(self.ccnl_subscriptions) + len(self.asking_subscriptions)
        if total == 0:
            return

        logger.info(f"재구독 시작: {total}개 종목")

        # 체결가 재구독
        for ticker in list(self.ccnl_subscriptions):
            await self._send_subscribe(self.TR_CCNL, ticker)
            await asyncio.sleep(0.1)  # Rate limit 준수

        # 호가 재구독
        for ticker in list(self.asking_subscriptions):
            await self._send_subscribe(self.TR_ASKING, ticker)
            await asyncio.sleep(0.1)

        logger.info("재구독 완료")

    async def subscribe_ccnl(self, tickers: List[str]) -> bool:
        """
        실시간 체결가 구독 (H0STCNT0)

        Args:
            tickers: 종목 코드 리스트

        Returns:
            성공 여부
        """
        if not self.connected or not self.ws:
            logger.error("WebSocket 미연결 상태")
            return False

        for ticker in tickers:
            if self.total_subscriptions >= self.config.max_subscriptions:
                logger.warning(f"최대 구독 수 초과 ({self.config.max_subscriptions})")
                return False

            if ticker not in self.ccnl_subscriptions:
                await self._send_subscribe(self.TR_CCNL, ticker)
                self.ccnl_subscriptions.add(ticker)
                await asyncio.sleep(0.1)

        logger.info(f"체결가 구독: {tickers} (총 {len(self.ccnl_subscriptions)}개)")
        return True

    async def subscribe_asking(self, tickers: List[str]) -> bool:
        """
        실시간 호가 구독 (H0STASP0)

        Args:
            tickers: 종목 코드 리스트

        Returns:
            성공 여부
        """
        if not self.connected or not self.ws:
            logger.error("WebSocket 미연결 상태")
            return False

        for ticker in tickers:
            if self.total_subscriptions >= self.config.max_subscriptions:
                logger.warning(f"최대 구독 수 초과 ({self.config.max_subscriptions})")
                return False

            if ticker not in self.asking_subscriptions:
                await self._send_subscribe(self.TR_ASKING, ticker)
                self.asking_subscriptions.add(ticker)
                await asyncio.sleep(0.1)

        logger.info(f"호가 구독: {tickers} (총 {len(self.asking_subscriptions)}개)")
        return True

    async def unsubscribe_ccnl(self, tickers: List[str]) -> bool:
        """체결가 구독 해제"""
        if not self.connected or not self.ws:
            return False

        for ticker in tickers:
            if ticker in self.ccnl_subscriptions:
                await self._send_unsubscribe(self.TR_CCNL, ticker)
                self.ccnl_subscriptions.discard(ticker)
                await asyncio.sleep(0.1)

        logger.info(f"체결가 구독 해제: {tickers}")
        return True

    async def unsubscribe_asking(self, tickers: List[str]) -> bool:
        """호가 구독 해제"""
        if not self.connected or not self.ws:
            return False

        for ticker in tickers:
            if ticker in self.asking_subscriptions:
                await self._send_unsubscribe(self.TR_ASKING, ticker)
                self.asking_subscriptions.discard(ticker)
                await asyncio.sleep(0.1)

        logger.info(f"호가 구독 해제: {tickers}")
        return True

    async def _send_subscribe(self, tr_id: str, ticker: str):
        """구독 요청 전송"""
        message = {
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "1",  # 1: 등록
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": tr_id,
                    "tr_key": ticker,
                }
            }
        }
        await self.ws.send(json.dumps(message))

    async def _send_unsubscribe(self, tr_id: str, ticker: str):
        """구독 해제 요청 전송"""
        message = {
            "header": {
                "approval_key": self.approval_key,
                "custtype": "P",
                "tr_type": "2",  # 2: 해제
                "content-type": "utf-8",
            },
            "body": {
                "input": {
                    "tr_id": tr_id,
                    "tr_key": ticker,
                }
            }
        }
        await self.ws.send(json.dumps(message))

    async def listen(self):
        """
        메시지 수신 루프

        연결이 끊어지면 자동 재연결 시도
        """
        self.running = True

        while self.running:
            try:
                if not self.connected or not self.ws:
                    if not await self.connect_with_retry():
                        logger.error("WebSocket 연결 불가 - Fallback 모드 활성화")
                        await self.graceful_degradation()
                        continue

                # 메시지 수신
                message = await self.ws.recv()
                await self._handle_message(message)

            except ConnectionClosed as e:
                logger.warning(f"WebSocket 연결 종료: {e}")
                self.connected = False
                self.consecutive_failures += 1
                self._update_circuit_state()

            except asyncio.CancelledError:
                logger.info("메시지 수신 루프 취소됨")
                break

            except Exception as e:
                logger.error(f"메시지 수신 오류: {e}")
                self.metrics['errors'] += 1

                if self.on_error:
                    self.on_error(e)

                await asyncio.sleep(1)

    async def _handle_message(self, message: str):
        """메시지 처리"""
        self.metrics['messages_received'] += 1
        self.metrics['last_message_at'] = datetime.now()

        try:
            # JSON 메시지 (구독 응답 등)
            if message.startswith('{'):
                data = json.loads(message)
                header = data.get('header', {})
                tr_id = header.get('tr_id', '')

                # 구독 응답 처리
                if header.get('tr_key'):
                    logger.debug(f"구독 응답: {tr_id} - {header.get('tr_key')}")
                return

            # 실시간 데이터 (파이프 구분)
            if '|' in message:
                await self._parse_realtime_data(message)

        except json.JSONDecodeError:
            # 파이프 구분 메시지 시도
            if '|' in message:
                await self._parse_realtime_data(message)
            else:
                logger.warning(f"알 수 없는 메시지 형식: {message[:100]}")

        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")

    async def _parse_realtime_data(self, message: str):
        """실시간 데이터 파싱"""
        try:
            parts = message.split('|')
            if len(parts) < 4:
                return

            # 헤더: 암호화여부|TR_ID|데이터건수|데이터
            encrypt_flag = parts[0]
            tr_id = parts[1]
            data_count = int(parts[2])
            data_str = parts[3]

            # 데이터 파싱 (^ 구분)
            fields = data_str.split('^')

            if tr_id == self.TR_CCNL:
                # 체결 데이터
                ticker_data = self._parse_ccnl(fields)
                if ticker_data and self.on_ccnl:
                    self.on_ccnl(ticker_data)

            elif tr_id == self.TR_ASKING:
                # 호가 데이터
                ticker_data = self._parse_asking(fields)
                if ticker_data and self.on_asking_price:
                    self.on_asking_price(ticker_data)

        except Exception as e:
            logger.error(f"실시간 데이터 파싱 오류: {e}")

    def _parse_ccnl(self, fields: List[str]) -> Optional[TickerData]:
        """
        체결 데이터 파싱 (H0STCNT0 - 46개 필드)

        컬럼 순서 (KIS API 공식):
        0: MKSC_SHRN_ISCD (종목코드)
        1: STCK_CNTG_HOUR (체결시간)
        2: STCK_PRPR (주식현재가)
        3: PRDY_VRSS_SIGN (전일대비부호)
        4: PRDY_VRSS (전일대비)
        5: PRDY_CTRT (전일대비율)
        6: WGHN_AVRG_STCK_PRC (가중평균주가)
        7: STCK_OPRC (시가)
        8: STCK_HGPR (고가)
        9: STCK_LWPR (저가)
        10: ASKP1 (매도호가1)
        11: BIDP1 (매수호가1)
        12: CNTG_VOL (체결거래량)
        13: ACML_VOL (누적거래량)
        14: ACML_TR_PBMN (누적거래대금)
        15: SELN_CNTG_CSNU (매도체결건수)
        16: SHNU_CNTG_CSNU (매수체결건수)
        17: NTBY_CNTG_CSNU (순매수체결건수)
        18: CTTR (체결강도)
        19: SELN_CNTG_SMTN (총매도수량)
        20: SHNU_CNTG_SMTN (총매수수량)
        21: CCLD_DVSN (체결구분 1:매수 5:매도)
        22: SHNU_RATE (매수비율)
        ...
        """
        try:
            if len(fields) < 23:
                return None

            return TickerData(
                ticker=fields[0],                                          # MKSC_SHRN_ISCD
                timestamp=datetime.now(),
                data_type='ccnl',
                current_price=int(fields[2]) if fields[2] else 0,          # STCK_PRPR
                change_rate=float(fields[5]) if fields[5] else 0.0,        # PRDY_CTRT
                volume=int(fields[12]) if fields[12] else 0,               # CNTG_VOL
                acml_vol=int(fields[13]) if fields[13] else 0,             # ACML_VOL
                acml_tr_pbmn=int(fields[14]) if fields[14] else 0,         # ACML_TR_PBMN
                cttr=float(fields[18]) if len(fields) > 18 and fields[18] else 0.0,       # CTTR
                seln_cntg_smtn=int(fields[19]) if len(fields) > 19 and fields[19] else 0,  # SELN_CNTG_SMTN
                shnu_cntg_smtn=int(fields[20]) if len(fields) > 20 and fields[20] else 0,  # SHNU_CNTG_SMTN
                ccld_dvsn=fields[21] if len(fields) > 21 else "",                          # CCLD_DVSN
                shnu_rate=float(fields[22]) if len(fields) > 22 and fields[22] else 0.0,   # SHNU_RATE
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"체결 데이터 파싱 실패: {e}")
            return None

    def _parse_asking(self, fields: List[str]) -> Optional[TickerData]:
        """
        호가 데이터 파싱 (H0STASP0)

        컬럼 순서 (KIS API 공식):
        0: MKSC_SHRN_ISCD (종목코드)
        1: BSOP_HOUR (영업시간)
        2: HOUR_CLS_CODE (시간구분코드)
        3-12: ASKP1~ASKP10 (매도호가 1~10)
        13-22: BIDP1~BIDP10 (매수호가 1~10)
        23-32: ASKP_RSQN1~ASKP_RSQN10 (매도호가잔량 1~10)
        33-42: BIDP_RSQN1~BIDP_RSQN10 (매수호가잔량 1~10)
        43: TOTAL_ASKP_RSQN (총 매도호가 잔량)
        44: TOTAL_BIDP_RSQN (총 매수호가 잔량)
        45: OVTM_TOTAL_ASKP_RSQN (시간외 총 매도호가 잔량)
        46: OVTM_TOTAL_BIDP_RSQN (시간외 총 매수호가 잔량)
        47: ANTC_CNPR (예상체결가)
        48: ANTC_CNQN (예상체결량)
        ...
        """
        try:
            if len(fields) < 45:
                return None

            # 10호가 파싱 (안전하게 파싱)
            def safe_int(val):
                return int(val) if val else 0

            askp = [safe_int(fields[i]) for i in range(3, 13)]       # 매도호가 1~10
            bidp = [safe_int(fields[i]) for i in range(13, 23)]      # 매수호가 1~10
            askp_rsqn = [safe_int(fields[i]) for i in range(23, 33)] # 매도잔량 1~10
            bidp_rsqn = [safe_int(fields[i]) for i in range(33, 43)] # 매수잔량 1~10

            return TickerData(
                ticker=fields[0],                                               # MKSC_SHRN_ISCD
                timestamp=datetime.now(),
                data_type='asking_price',
                askp=askp,
                bidp=bidp,
                askp_rsqn=askp_rsqn,
                bidp_rsqn=bidp_rsqn,
                total_askp_rsqn=safe_int(fields[43]),                           # TOTAL_ASKP_RSQN
                total_bidp_rsqn=safe_int(fields[44]),                           # TOTAL_BIDP_RSQN
                antc_cnpr=safe_int(fields[47]) if len(fields) > 47 else 0,      # ANTC_CNPR
                antc_cnqn=safe_int(fields[48]) if len(fields) > 48 else 0,      # ANTC_CNQN
            )
        except (ValueError, IndexError) as e:
            logger.warning(f"호가 데이터 파싱 실패: {e}")
            return None

    async def graceful_degradation(self):
        """
        WebSocket 장애 시 REST API로 폴백

        백그라운드에서 계속 재연결 시도
        """
        logger.warning("Graceful Degradation: REST API 폴백 모드 활성화")
        self.fallback_mode = True

        # 백그라운드에서 주기적으로 재연결 시도
        asyncio.create_task(self._background_reconnect())

    async def _background_reconnect(self):
        """백그라운드에서 주기적으로 재연결 시도"""
        while self.fallback_mode and self.running:
            await asyncio.sleep(self.config.recovery_timeout)

            if await self.connect_with_retry():
                self.fallback_mode = False
                logger.info("WebSocket 복구 완료 - 정상 모드 복귀")
                break

    async def close(self):
        """연결 종료"""
        self.running = False

        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                logger.warning(f"WebSocket 종료 오류: {e}")

        self.connected = False
        self.ws = None
        logger.info("WebSocket 연결 종료")

    def get_metrics(self) -> Dict[str, Any]:
        """메트릭 조회"""
        return {
            **self.metrics,
            'circuit_state': self.circuit_state.value,
            'connected': self.connected,
            'fallback_mode': self.fallback_mode,
            'ccnl_subscriptions': len(self.ccnl_subscriptions),
            'asking_subscriptions': len(self.asking_subscriptions),
        }
