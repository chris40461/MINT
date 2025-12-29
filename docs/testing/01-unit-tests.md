# 단위 테스트 (Unit Tests)

## 📌 문서 목적

백엔드 및 프론트엔드의 개별 함수, 클래스, 컴포넌트에 대한 단위 테스트 전략과 예시를 정의합니다.

---

## 🎯 테스트 전략

### 테스트 우선 순위

| 우선순위 | 대상 | 이유 |
|---------|------|------|
| **높음** | 급등주 감지 로직, 점수 계산 | 핵심 비즈니스 로직 |
| **높음** | LLM 프롬프트 생성 | 품질 직접 영향 |
| **중간** | 데이터 수집, 필터링 | 안정성 중요 |
| **중간** | API 엔드포인트 | 클라이언트 의존성 |
| **낮음** | UI 컴포넌트 | 시각적 확인 가능 |

### 테스트 커버리지 목표

- **백엔드**: 80% 이상
- **프론트엔드**: 60% 이상
- **핵심 로직**: 100%

---

## 🐍 백엔드 단위 테스트 (pytest)

### 1. 테스트 환경 설정

```python
# backend/tests/conftest.py

import pytest
from app.main import app
from app.db.session import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 테스트용 인메모리 DB
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def engine():
    """테스트용 DB 엔진"""
    return create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(scope="session")
def tables(engine):
    """테이블 생성"""
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    """DB 세션"""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """FastAPI 테스트 클라이언트"""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient
    yield TestClient(app)

    app.dependency_overrides.clear()
```

---

### 2. 지표 계산 테스트

```python
# backend/tests/test_metrics.py

import pytest
from app.utils.metrics import (
    calculate_gap_ratio,
    calculate_intraday_change,
    calculate_closing_strength,
    calculate_volume_change,
    calculate_rsi
)

class TestPriceMetrics:
    """가격 지표 계산 테스트"""

    def test_gap_ratio_positive(self):
        """갭 상승 테스트"""
        current_open = 55000
        prev_close = 50000

        gap_ratio = calculate_gap_ratio(current_open, prev_close)

        assert gap_ratio == 10.0  # 10% 상승

    def test_gap_ratio_negative(self):
        """갭 하락 테스트"""
        current_open = 45000
        prev_close = 50000

        gap_ratio = calculate_gap_ratio(current_open, prev_close)

        assert gap_ratio == -10.0  # 10% 하락

    def test_intraday_change(self):
        """장중 등락률 테스트"""
        current_price = 52500
        open_price = 50000

        change = calculate_intraday_change(current_price, open_price)

        assert change == 5.0  # 5% 상승

    def test_closing_strength_strong_buy(self):
        """마감 강도 - 강한 매수세"""
        close = 52000
        low = 50000
        high = 52000

        strength = calculate_closing_strength(close, low, high)

        assert strength == 1.0  # 만점

    def test_closing_strength_strong_sell(self):
        """마감 강도 - 강한 매도세"""
        close = 50000
        low = 50000
        high = 52000

        strength = calculate_closing_strength(close, low, high)

        assert strength == 0.0

    def test_closing_strength_neutral(self):
        """마감 강도 - 보합"""
        close = 51000
        low = 50000
        high = 52000

        strength = calculate_closing_strength(close, low, high)

        assert strength == pytest.approx(0.5, rel=1e-2)


class TestVolumeMetrics:
    """거래량 지표 계산 테스트"""

    def test_volume_change_increase(self):
        """거래량 증가"""
        current_volume = 1_500_000
        prev_volume = 1_000_000

        change = calculate_volume_change(current_volume, prev_volume)

        assert change == 50.0  # 50% 증가

    def test_volume_change_zero_prev(self):
        """전일 거래량 0 처리"""
        current_volume = 1_000_000
        prev_volume = 0

        change = calculate_volume_change(current_volume, prev_volume)

        assert change == 0  # 0 반환


class TestTechnicalIndicators:
    """기술적 지표 테스트"""

    def test_rsi_overbought(self):
        """RSI 과매수"""
        import pandas as pd

        # 연속 상승 시나리오
        prices = pd.Series([
            50000, 51000, 52000, 53000, 54000,
            55000, 56000, 57000, 58000, 59000,
            60000, 61000, 62000, 63000, 64000
        ])

        rsi = calculate_rsi(prices, period=14)

        assert rsi.iloc[-1] > 70  # 과매수

    def test_rsi_oversold(self):
        """RSI 과매도"""
        import pandas as pd

        # 연속 하락 시나리오
        prices = pd.Series([
            64000, 63000, 62000, 61000, 60000,
            59000, 58000, 57000, 56000, 55000,
            54000, 53000, 52000, 51000, 50000
        ])

        rsi = calculate_rsi(prices, period=14)

        assert rsi.iloc[-1] < 30  # 과매도
```

---

### 3. 필터링 테스트

```python
# backend/tests/test_filters.py

import pytest
import pandas as pd
from app.utils.filters import StockFilter

class TestStockFilter:
    """종목 필터링 테스트"""

    @pytest.fixture
    def sample_data(self):
        """샘플 시장 데이터"""
        return pd.DataFrame({
            '종목코드': ['005930', '000660', '005380', '051910'],
            '종목명': ['삼성전자', 'SK하이닉스', '현대차', 'LG화학'],
            '시가': [72000, 128000, 190000, 425000],
            '종가': [74000, 130000, 188000, 430000],
            '거래량': [15_000_000, 5_000_000, 2_000_000, 500_000],
            '거래대금': [1_110_000_000_000, 650_000_000_000, 376_000_000_000, 215_000_000_000],
            '시가총액': [430_000_000_000_000, 95_000_000_000_000, 45_000_000_000_000, 30_000_000_000_000]
        })

    def test_apply_absolute_filters(self, sample_data):
        """절대적 필터 테스트"""
        filter = StockFilter()

        # 거래대금 500억원 이상, 시총 50조원 이상 필터
        filtered = filter.apply_absolute_filters(
            sample_data,
            min_trading_value=50_000_000_000,   # 500억원
            min_market_cap=50_000_000_000_000   # 50조원
        )

        # 삼성전자, SK하이닉스만 통과
        assert len(filtered) == 2
        assert '005930' in filtered['종목코드'].values
        assert '000660' in filtered['종목코드'].values

    def test_filter_uptrend_only(self, sample_data):
        """상승 종목 필터"""
        filter = StockFilter()

        uptrend = filter.filter_uptrend_only(sample_data)

        # 삼성전자, SK하이닉스, LG화학 (상승)
        assert len(uptrend) == 3
        # 현대차는 하락 (제외됨)
        assert '005380' not in uptrend['종목코드'].values

    def test_filter_sideways_only(self):
        """횡보 종목 필터"""
        data = pd.DataFrame({
            '종목코드': ['A', 'B', 'C'],
            '시가': [10000, 10000, 10000],
            '종가': [10300, 10050, 10500]
        })

        filter = StockFilter()

        # ±5% 이내
        sideways = filter.filter_sideways_only(data, max_change_rate=5.0)

        # A (3% 상승), B (0.5% 상승)만 통과
        assert len(sideways) == 2
        assert 'C' not in sideways['종목코드'].values  # 5% 초과
```

---

### 4. 트리거 감지 테스트

```python
# backend/tests/test_triggers.py

import pytest
from datetime import datetime
from app.services.trigger_service import TriggerService
from app.services.data_service import DataService

@pytest.mark.asyncio
class TestTriggerService:
    """급등주 트리거 테스트"""

    @pytest.fixture
    def trigger_service(self, db_session):
        data_service = DataService()
        return TriggerService(data_service)

    async def test_morning_volume_surge(self, trigger_service, mocker):
        """오전 거래량 급증 트리거"""
        # Mock 데이터
        current_data = pd.DataFrame({
            '종목코드': ['005930'],
            '종목명': ['삼성전자'],
            '시가': [72000],
            '종가': [74000],
            '거래량': [20_000_000],  # 전일 대비 100% 증가
            '거래대금': [1_500_000_000_000],
            '시가총액': [430_000_000_000_000]
        })

        prev_data = pd.DataFrame({
            '종목코드': ['005930'],
            '거래량': [10_000_000]  # 전일 거래량
        })

        mocker.patch.object(
            trigger_service.data_service,
            'get_market_snapshot',
            side_effect=[current_data, prev_data]
        )

        results = await trigger_service.morning_volume_surge(
            datetime(2025, 11, 6),
            top_n=3
        )

        # 검증
        assert len(results) > 0
        assert results[0]['종목코드'] == '005930'
        assert results[0]['거래량증가율'] >= 30  # 30% 이상 증가

    async def test_no_triggers_on_low_volume(self, trigger_service, mocker):
        """거래량 미달 시 트리거 미발생"""
        # 거래대금 낮은 데이터
        current_data = pd.DataFrame({
            '종목코드': ['000001'],
            '종목명': ['테스트주식'],
            '시가': [1000],
            '종가': [1100],
            '거래량': [100_000],
            '거래대금': [110_000_000],  # 1.1억원 (필터 미통과)
            '시가총액': [10_000_000_000]
        })

        prev_data = pd.DataFrame({
            '종목코드': ['000001'],
            '거래량': [50_000]
        })

        mocker.patch.object(
            trigger_service.data_service,
            'get_market_snapshot',
            side_effect=[current_data, prev_data]
        )

        results = await trigger_service.morning_volume_surge(
            datetime(2025, 11, 6),
            top_n=3
        )

        # 필터링되어 결과 없음
        assert len(results) == 0
```

---

## ⚛️ 프론트엔드 단위 테스트 (Jest + React Testing Library)

### 1. 테스트 환경 설정

```typescript
// frontend/jest.config.js

module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '\\.(css|less|scss)$': 'identity-obj-proxy'
  },
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  }
};
```

```typescript
// frontend/jest.setup.ts

import '@testing-library/jest-dom';
```

---

### 2. 컴포넌트 테스트

```typescript
// components/common/Button/Button.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button 컴포넌트', () => {
  test('기본 렌더링', () => {
    render(<Button>클릭</Button>);

    const button = screen.getByText('클릭');
    expect(button).toBeInTheDocument();
  });

  test('클릭 이벤트 처리', () => {
    const handleClick = jest.fn();

    render(<Button onClick={handleClick}>클릭</Button>);

    const button = screen.getByText('클릭');
    fireEvent.click(button);

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  test('disabled 상태', () => {
    const handleClick = jest.fn();

    render(
      <Button disabled onClick={handleClick}>
        클릭
      </Button>
    );

    const button = screen.getByText('클릭');
    fireEvent.click(button);

    expect(handleClick).not.toHaveBeenCalled();
    expect(button).toBeDisabled();
  });

  test('loading 상태', () => {
    render(<Button loading>로딩</Button>);

    const spinner = screen.getByText('⏳');
    expect(spinner).toBeInTheDocument();
  });

  test('variant 적용', () => {
    const { container } = render(
      <Button variant="danger">삭제</Button>
    );

    const button = container.querySelector('.btn-danger');
    expect(button).toBeInTheDocument();
  });
});
```

---

### 3. Stock 컴포넌트 테스트

```typescript
// components/stock/PriceDisplay/PriceDisplay.test.tsx

import { render, screen } from '@testing-library/react';
import { PriceDisplay } from './PriceDisplay';

describe('PriceDisplay 컴포넌트', () => {
  test('가격 표시', () => {
    render(<PriceDisplay price={72000} />);

    expect(screen.getByText('72,000원')).toBeInTheDocument();
  });

  test('상승률 표시 (양수)', () => {
    render(
      <PriceDisplay
        price={72000}
        changeRate={5.2}
        changeAmount={3500}
      />
    );

    expect(screen.getByText(/\+3,500/)).toBeInTheDocument();
    expect(screen.getByText(/\+5\.20%/)).toBeInTheDocument();
    expect(screen.getByText('▲')).toBeInTheDocument();
  });

  test('하락률 표시 (음수)', () => {
    render(
      <PriceDisplay
        price={68500}
        changeRate={-5.0}
        changeAmount={-3500}
      />
    );

    expect(screen.getByText(/-3,500/)).toBeInTheDocument();
    expect(screen.getByText(/-5\.00%/)).toBeInTheDocument();
    expect(screen.getByText('▼')).toBeInTheDocument();
  });

  test('CSS 클래스 적용 (positive)', () => {
    const { container } = render(
      <PriceDisplay price={72000} changeRate={5.2} />
    );

    const changeElement = container.querySelector('.positive');
    expect(changeElement).toBeInTheDocument();
  });

  test('CSS 클래스 적용 (negative)', () => {
    const { container } = render(
      <PriceDisplay price={68500} changeRate={-5.0} />
    );

    const changeElement = container.querySelector('.negative');
    expect(changeElement).toBeInTheDocument();
  });
});
```

---

### 4. Hook 테스트

```typescript
// hooks/useTriggers.test.ts

import { renderHook, waitFor } from '@testing-library/react';
import { useTriggers } from './useTriggers';
import * as api from '@/services/api';

jest.mock('@/services/api');

describe('useTriggers Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('초기 로딩 상태', () => {
    const mockFetch = jest.spyOn(api, 'fetchTriggers').mockResolvedValue({
      triggers: []
    });

    const { result } = renderHook(() =>
      useTriggers({ session: 'morning', date: '2025-11-06' })
    );

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
  });

  test('데이터 로드 성공', async () => {
    const mockData = {
      triggers: [
        {
          id: '1',
          ticker: '005930',
          name: '삼성전자',
          currentPrice: 72000,
          changeRate: 5.2
        }
      ]
    };

    jest.spyOn(api, 'fetchTriggers').mockResolvedValue(mockData);

    const { result } = renderHook(() =>
      useTriggers({ session: 'morning', date: '2025-11-06' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
    expect(result.current.error).toBeNull();
  });

  test('데이터 로드 실패', async () => {
    const mockError = new Error('Network error');

    jest.spyOn(api, 'fetchTriggers').mockRejectedValue(mockError);

    const { result } = renderHook(() =>
      useTriggers({ session: 'morning', date: '2025-11-06' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toEqual(mockError);
    expect(result.current.data).toBeNull();
  });

  test('refetch 기능', async () => {
    const mockFetch = jest.spyOn(api, 'fetchTriggers').mockResolvedValue({
      triggers: []
    });

    const { result } = renderHook(() =>
      useTriggers({ session: 'morning', date: '2025-11-06' })
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // refetch 호출
    result.current.refetch();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});
```

---

## 🏃 테스트 실행

### 백엔드

```bash
# 전체 테스트 실행
pytest

# 특정 파일 테스트
pytest backend/tests/test_metrics.py

# 커버리지 리포트
pytest --cov=app --cov-report=html

# 마커별 실행
pytest -m asyncio  # 비동기 테스트만
```

### 프론트엔드

```bash
# 전체 테스트 실행
npm test

# Watch 모드
npm test -- --watch

# 커버리지
npm test -- --coverage

# 특정 파일
npm test -- PriceDisplay.test.tsx
```

---

## 📊 테스트 커버리지 확인

```bash
# 백엔드
pytest --cov=app --cov-report=term --cov-report=html

# 커버리지 리포트는 htmlcov/index.html에 생성

# 프론트엔드
npm test -- --coverage

# coverage/lcov-report/index.html에 생성
```

---

## ⚙️ CI/CD 통합

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        run: |
          cd backend
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm install

      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage --watchAll=false

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./frontend/coverage/lcov.info
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
