"""
FRED (Federal Reserve Economic Data) Collector
거시경제 지표 수집: 금리, CPI, 실업률 등
"""

import sys
from pathlib import Path

# 직접 실행 시 부모 디렉토리를 Python path에 추가
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
from openbb import obb

from config.settings import (
    FRED_API_KEY,
    RATE_LIMIT_SLEEP_FRED,
    END_DATE
)
from utils.logger import get_logger
from utils.retry import retry_with_backoff
import time

logger = get_logger(__name__)


class FREDCollector:
    """
    FRED 거시경제 지표 수집기

    수집 지표:
    - DGS10: 10년물 국채 금리
    - DGS2: 2년물 국채 금리
    - FEDFUNDS: 연방기금금리
    - CPIAUCSL: 소비자물가지수
    - UNRATE: 실업률
    """

    # FRED 지표 매핑 (FRED symbol -> DB field name)
    INDICATORS = {
        'DGS10': 'dgs10',
        'DGS2': 'dgs2',
        'FEDFUNDS': 'fed_funds_rate',
        'CPIAUCSL': 'cpi',
        'UNRATE': 'unemployment_rate'
    }

    def __init__(self):
        """초기화"""
        # FRED API 키 설정
        if FRED_API_KEY:
            obb.user.credentials.fred_api_key = FRED_API_KEY
            logger.info("FRED API key configured")
        else:
            logger.warning("FRED_API_KEY not set - API calls may fail")

        self.end_date = END_DATE
        # FRED는 450일치 데이터를 가져와서 최신 데이터 추출 (CPI YoY 계산을 위해 13개월 이상 필요)
        self.start_date = self.end_date - timedelta(days=450)

    @retry_with_backoff(max_retries=3, base_delay=2)
    def _fetch_indicator(self, symbol: str) -> Optional[pd.Series]:
        """
        단일 FRED 지표 수집

        Args:
            symbol: FRED 지표 심볼 (예: 'DGS10')

        Returns:
            pd.Series: 시계열 데이터 (index: date, values: indicator value)
                      실패 시 None
        """
        try:
            start_date_str = self.start_date.strftime('%Y-%m-%d')

            logger.debug(f"Fetching {symbol} from {start_date_str}...")

            result = obb.economy.fred_series(
                symbol=symbol,
                start_date=start_date_str,
                provider='fred'
            )

            if not hasattr(result, 'to_dataframe'):
                logger.warning(f"{symbol}: No to_dataframe method")
                return None

            df = result.to_dataframe()

            if df.empty:
                logger.warning(f"{symbol}: Empty DataFrame")
                return None

            logger.debug(f"{symbol}: Got {len(df)} rows, columns: {df.columns.tolist()}")

            # FRED 데이터는 'value' 컬럼 또는 마지막 컬럼에 있음
            if 'value' in df.columns:
                valid_data = df['value'].dropna()
            else:
                # 마지막 컬럼 사용 (보통 지표명과 동일)
                valid_data = df.iloc[:, -1].dropna()
                logger.debug(f"{symbol}: Using column '{df.columns[-1]}' as data")

            if valid_data.empty:
                logger.warning(f"{symbol}: All values are NaN")
                return None

            logger.info(f"{symbol}: Collected {len(valid_data)} data points")
            return valid_data

        except Exception as e:
            logger.error(f"{symbol} collection failed: {str(e)}")
            raise

    def collect(self) -> Optional[Dict]:
        """
        모든 FRED 지표 수집 및 계산

        Returns:
            dict: {
                'date': datetime.date,
                'dgs10': float,
                'dgs2': float,
                'yield_spread': float,
                'fed_funds_rate': float,
                'cpi_yoy': float,
                'unemployment_rate': float
            }
            실패 시 None
        """
        logger.info("Starting FRED data collection...")

        fred_data = {}

        # 1. 각 지표 수집
        for symbol, field in self.INDICATORS.items():
            try:
                data = self._fetch_indicator(symbol)

                if data is not None:
                    fred_data[field] = data

                # Rate limiting
                time.sleep(RATE_LIMIT_SLEEP_FRED)

            except Exception as e:
                logger.error(f"{symbol} ({field}) collection failed: {str(e)}")
                # 하나 실패해도 계속 진행

        # 2. 수집 결과 확인
        if len(fred_data) < 2:
            logger.error(f"Insufficient FRED data collected: {len(fred_data)} indicators")
            return None

        logger.info(f"Collected {len(fred_data)} indicators: {list(fred_data.keys())}")

        # 3. 최신 공통 날짜 찾기
        latest_dates = {k: v.index[-1] for k, v in fred_data.items()}
        common_date = max(latest_dates.values())

        # Timestamp -> date 변환
        if hasattr(common_date, 'date'):
            common_date = common_date.date()

        logger.info(f"Common latest date: {common_date}")

        # 4. CPI YoY 계산 (전년 동월 대비 증가율)
        cpi_yoy = None
        if 'cpi' in fred_data:
            cpi_series = fred_data['cpi']
            if len(cpi_series) >= 13:  # 최소 13개월 데이터 필요
                curr = cpi_series.iloc[-1]
                prev = cpi_series.iloc[-13]  # 12개월 전
                cpi_yoy = ((curr / prev) - 1) * 100
                logger.info(f"CPI YoY calculated: {cpi_yoy:.2f}%")
            else:
                logger.warning(f"Insufficient CPI data for YoY calculation: {len(cpi_series)} months")

        # 5. Yield Spread 계산 (10Y - 2Y)
        yield_spread = None
        if 'dgs10' in fred_data and 'dgs2' in fred_data:
            dgs10_latest = fred_data['dgs10'].iloc[-1]
            dgs2_latest = fred_data['dgs2'].iloc[-1]
            yield_spread = dgs10_latest - dgs2_latest
            logger.info(f"Yield Spread calculated: {yield_spread:.2f}")

        # 6. 결과 딕셔너리 생성
        result = {
            'date': common_date,
            'dgs10': fred_data.get('dgs10', pd.Series([None])).iloc[-1],
            'dgs2': fred_data.get('dgs2', pd.Series([None])).iloc[-1],
            'yield_spread': yield_spread,
            'fed_funds_rate': fred_data.get('fed_funds_rate', pd.Series([None])).iloc[-1],
            'cpi_yoy': cpi_yoy,
            'unemployment_rate': fred_data.get('unemployment_rate', pd.Series([None])).iloc[-1]
        }

        # 7. 결과 로깅
        logger.info("FRED data collection completed:")
        logger.info(f"  Date: {result['date']}")
        logger.info(f"  DGS10: {result['dgs10']}")
        logger.info(f"  DGS2: {result['dgs2']}")
        logger.info(f"  Yield Spread: {result['yield_spread']}")
        logger.info(f"  Fed Funds Rate: {result['fed_funds_rate']}")
        logger.info(f"  CPI YoY: {result['cpi_yoy']}")
        logger.info(f"  Unemployment Rate: {result['unemployment_rate']}")

        return result

    def collect_single_indicator(self, symbol: str) -> Optional[pd.Series]:
        """
        단일 지표만 수집 (테스트 또는 개별 수집용)

        Args:
            symbol: FRED 지표 심볼 (예: 'DGS10')

        Returns:
            pd.Series: 시계열 데이터 또는 None
        """
        logger.info(f"Collecting single indicator: {symbol}")
        return self._fetch_indicator(symbol)
