"""
Options Collector
CBOE를 통한 옵션 요약 통계 수집
"""

import sys
from pathlib import Path

# 직접 실행 시 부모 디렉토리를 Python path에 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from openbb import obb

from config.settings import (
    RATE_LIMIT_SLEEP_OPTIONS,
    END_DATE
)
from utils.logger import get_logger
from utils.retry import retry_with_backoff
import time

logger = get_logger(__name__)


class OptionsCollector:
    """
    CBOE 옵션 요약 통계 수집기

    수집 항목:
    - Put/Call Ratio (Volume & Open Interest)
    - Total Call/Put Volume & Open Interest
    - Average Implied Volatility (Call, Put, Overall)

    Note:
        - 개별 옵션 계약(options)은 포함하지 않음 (사용자 요청 시 실시간 조회)
        - 작은 종목들은 CBOE 옵션이 없을 수 있음 (정상)
    """

    def __init__(self):
        """초기화"""
        self.provider = 'cboe'
        logger.info("OptionsCollector initialized (provider: cboe)")

    @retry_with_backoff(max_retries=5, base_delay=2)
    def _fetch_options_chains(
        self,
        ticker: str
    ) -> Optional[pd.DataFrame]:
        """
        단일 종목의 옵션 체인 데이터 수집

        Args:
            ticker: 종목 코드

        Returns:
            pd.DataFrame: 옵션 체인 데이터
                         실패 시 None
        """
        try:
            logger.debug(f"{ticker}: Fetching options chains from CBOE")

            # initial_setup.py:604-606 참고
            result = obb.derivatives.options.chains(
                symbol=ticker,
                provider=self.provider
            )

            if not hasattr(result, 'to_dataframe'):
                logger.warning(f"{ticker}: No to_dataframe method")
                return None

            df = result.to_dataframe()

            if df.empty:
                logger.warning(f"{ticker}: No options data (possibly no CBOE options)")
                return None

            logger.info(f"{ticker}: Collected {len(df)} options contracts")
            return df

        except Exception as e:
            logger.error(f"{ticker} options collection failed: {str(e)}")
            raise

    def collect_ticker(
        self,
        ticker: str,
        snapshot_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        단일 종목의 옵션 요약 통계 수집 (DB 저장 형식으로 변환)

        Args:
            ticker: 종목 코드
            snapshot_date: 스냅샷 날짜 (기본값: 오늘)

        Returns:
            dict: {
                'ticker': str,
                'snapshot_date': date,
                'put_call_ratio_volume': float,
                'put_call_ratio_oi': float,
                'total_call_volume': int,
                'total_put_volume': int,
                'total_call_oi': int,
                'total_put_oi': int,
                'avg_iv_call': float,
                'avg_iv_put': float,
                'avg_iv': float,
                'provider': str
            }
            실패 시 None

        Note:
            - initial_setup.py:598-654 패턴 따름
            - Call/Put 분리하여 요약 통계 계산
            - 작은 종목은 옵션이 없을 수 있음 (정상)
        """
        if snapshot_date is None:
            snapshot_date = END_DATE

        try:
            df = self._fetch_options_chains(ticker)

            if df is None:
                return None

            # initial_setup.py:615-617 참고: Call/Put 분리
            calls = df[df['option_type'] == 'call']
            puts = df[df['option_type'] == 'put']

            # initial_setup.py:619-622 참고: Volume & OI 합계
            total_call_volume = calls['volume'].sum() if 'volume' in calls.columns else 0
            total_put_volume = puts['volume'].sum() if 'volume' in puts.columns else 0
            total_call_oi = calls['open_interest'].sum() if 'open_interest' in calls.columns else 0
            total_put_oi = puts['open_interest'].sum() if 'open_interest' in puts.columns else 0

            # initial_setup.py:624-625 참고: Put/Call Ratios
            pcr_volume = total_put_volume / total_call_volume if total_call_volume > 0 else None
            pcr_oi = total_put_oi / total_call_oi if total_call_oi > 0 else None

            # initial_setup.py:627-630 참고: IV Averages
            avg_iv_call = calls['implied_volatility'].mean() if 'implied_volatility' in calls.columns else None
            avg_iv_put = puts['implied_volatility'].mean() if 'implied_volatility' in puts.columns else None
            avg_iv = df['implied_volatility'].mean() if 'implied_volatility' in df.columns else None

            record = {
                'ticker': ticker,
                'snapshot_date': snapshot_date.date() if hasattr(snapshot_date, 'date') else snapshot_date,
                'put_call_ratio_volume': pcr_volume,
                'put_call_ratio_oi': pcr_oi,
                'total_call_volume': int(total_call_volume),
                'total_put_volume': int(total_put_volume),
                'total_call_oi': int(total_call_oi),
                'total_put_oi': int(total_put_oi),
                'avg_iv_call': avg_iv_call,
                'avg_iv_put': avg_iv_put,
                'avg_iv': avg_iv,
                'provider': self.provider
            }

            logger.info(f"{ticker}: Converted options summary record")
            return record

        except Exception as e:
            logger.error(f"{ticker} options summary collection failed: {str(e)}")
            return None

    def collect_latest(
        self,
        ticker: str
    ) -> Optional[Dict]:
        """
        최신 옵션 요약 통계 수집 (오늘 날짜로)

        Args:
            ticker: 종목 코드

        Returns:
            dict: 옵션 요약 통계
                  실패 시 None

        Note:
            - Daily update에서 사용
            - snapshot_date는 오늘 날짜로 자동 설정
        """
        logger.info(f"{ticker}: Collecting latest options summary")

        return self.collect_ticker(ticker)

    def collect_multiple(
        self,
        tickers: List[str],
        snapshot_date: Optional[datetime] = None,
        rate_limit: bool = True
    ) -> Dict[str, Dict]:
        """
        여러 종목의 옵션 요약 통계 수집

        Args:
            tickers: 종목 코드 리스트
            snapshot_date: 스냅샷 날짜
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: record}

        Note:
            - 작은 종목은 옵션이 없을 수 있음 (정상, 조용히 skip)
        """
        logger.info(f"Collecting options summary for {len(tickers)} tickers")

        results = {}

        for idx, ticker in enumerate(tickers, 1):
            try:
                record = self.collect_ticker(ticker, snapshot_date)

                if record:
                    results[ticker] = record

                # Rate limiting
                if rate_limit and idx < len(tickers):
                    time.sleep(RATE_LIMIT_SLEEP_OPTIONS)

            except Exception as e:
                # initial_setup.py:653-654 참고: 작은 종목은 옵션이 없는 게 정상
                logger.debug(f"{ticker} options collection failed (possibly no CBOE options): {str(e)}")
                continue

        logger.info(f"Collected options summary for {len(results)}/{len(tickers)} tickers")
        return results

    def collect_latest_batch(
        self,
        tickers: List[str],
        rate_limit: bool = True
    ) -> Dict[str, Dict]:
        """
        여러 종목의 최신 옵션 요약 배치 수집

        Args:
            tickers: 종목 코드 리스트
            rate_limit: Rate limiting 적용 여부

        Returns:
            dict: {ticker: latest_record}

        Note:
            - Daily update에서 사용
            - 각 종목별로 최신 옵션 요약 수집
            - 작은 종목은 옵션이 없을 수 있음 (정상)
        """
        logger.info(f"Collecting latest options summary for {len(tickers)} tickers")

        return self.collect_multiple(
            tickers=tickers,
            snapshot_date=None,  # 오늘 날짜 사용
            rate_limit=rate_limit
        )
