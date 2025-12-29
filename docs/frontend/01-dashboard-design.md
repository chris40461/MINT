# 대시보드 설계 (Dashboard Design)

## 📌 문서 목적

급등주 목록, 실시간 업데이트, 필터링 기능을 제공하는 메인 대시보드 UI/UX 설계를 정의합니다.

---

## 🎨 전체 레이아웃

### 1. 와이어프레임

```
┌─────────────────────────────────────────────────────────────┐
│  MINT                    🔔 알림   👤 사용자         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 📊 KOSPI    │  │ 📈 급등주   │  │ 🕐 마지막    │         │
│  │ 2,650.34    │  │ 18개 감지   │  │ 업데이트     │         │
│  │ +1.2% ▲    │  │ 오늘 15:30  │  │ 1분 전       │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🔍 검색   [                    ]  🔽 세션  🔽 트리거  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 급등주 목록                                 📥 내보내기 │  │
│  ├───┬─────────┬────────┬────────┬────────┬──────────────┤  │
│  │ # │ 종목명  │ 현재가 │ 등락률 │ 거래량 │ 트리거 타입  │  │
│  ├───┼─────────┼────────┼────────┼────────┼──────────────┤  │
│  │ 1 │ 삼성전자│ 72,000 │ +5.2%  │ 15.2M  │ 거래량 급증  │  │
│  │ 2 │ SK하이닉│ 128,500│ +3.8%  │ 8.5M   │ 갭 상승      │  │
│  │ 3 │ LG에너지│ 425,000│ +4.1%  │ 2.1M   │ 마감 강도    │  │
│  │...│         │        │        │        │              │  │
│  └───┴─────────┴────────┴────────┴────────┴──────────────┘  │
│                                                               │
│  [1] [2] [3] ... [10]                       총 18개 / 페이지 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 컴포넌트 구조

### 1. 디렉토리 구조

```
frontend/src/components/Dashboard/
├── Dashboard.tsx                # 메인 대시보드 컨테이너
├── SummaryCards.tsx            # 상단 요약 카드
│   ├── MarketIndexCard.tsx     # KOSPI/KOSDAQ 카드
│   ├── TriggerCountCard.tsx    # 급등주 개수 카드
│   └── LastUpdateCard.tsx      # 마지막 업데이트 시간
├── FilterBar.tsx               # 검색 및 필터
├── TriggerTable.tsx            # 급등주 테이블
│   ├── TriggerRow.tsx          # 테이블 행
│   └── TriggerBadge.tsx        # 트리거 타입 뱃지
└── Pagination.tsx              # 페이지네이션
```

### 2. 메인 대시보드 컴포넌트

```typescript
// components/Dashboard/Dashboard.tsx

import React, { useState, useEffect } from 'react';
import { SummaryCards } from './SummaryCards';
import { FilterBar } from './FilterBar';
import { TriggerTable } from './TriggerTable';
import { Pagination } from './Pagination';
import { useTriggers } from '@/hooks/useTriggers';

export const Dashboard: React.FC = () => {
  const [filters, setFilters] = useState({
    session: 'all',       // morning | afternoon | all
    triggerType: 'all',   // volume_surge | gap_up | ...
    date: new Date().toISOString().split('T')[0]
  });

  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const { data, loading, error, refetch } = useTriggers(filters);

  // 자동 갱신 (1분마다)
  useEffect(() => {
    const interval = setInterval(() => {
      refetch();
    }, 60000);

    return () => clearInterval(interval);
  }, [refetch]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay error={error} />;

  const triggers = data?.triggers || [];
  const paginatedTriggers = triggers.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  return (
    <div className="dashboard">
      <SummaryCards
        kospiIndex={data?.market.kospi}
        triggerCount={triggers.length}
        lastUpdate={data?.lastUpdate}
      />

      <FilterBar
        filters={filters}
        onFilterChange={setFilters}
      />

      <TriggerTable
        triggers={paginatedTriggers}
        onRefresh={refetch}
      />

      <Pagination
        currentPage={currentPage}
        totalItems={triggers.length}
        itemsPerPage={itemsPerPage}
        onPageChange={setCurrentPage}
      />
    </div>
  );
};
```

---

## 📊 상단 요약 카드

### MarketIndexCard

```typescript
// components/Dashboard/SummaryCards/MarketIndexCard.tsx

interface MarketIndexCardProps {
  index: {
    name: string;
    value: number;
    changeRate: number;
  };
}

export const MarketIndexCard: React.FC<MarketIndexCardProps> = ({ index }) => {
  const isPositive = index.changeRate > 0;

  return (
    <div className="summary-card">
      <div className="card-icon">📊</div>
      <div className="card-content">
        <h3>{index.name}</h3>
        <div className="index-value">
          {index.value.toLocaleString('ko-KR', { minimumFractionDigits: 2 })}
        </div>
        <div className={`change-rate ${isPositive ? 'positive' : 'negative'}`}>
          {isPositive ? '+' : ''}{index.changeRate.toFixed(2)}%
          {isPositive ? ' ▲' : ' ▼'}
        </div>
      </div>
    </div>
  );
};
```

### TriggerCountCard

```typescript
// components/Dashboard/SummaryCards/TriggerCountCard.tsx

interface TriggerCountCardProps {
  count: number;
  session: string;
  timestamp: string;
}

export const TriggerCountCard: React.FC<TriggerCountCardProps> = ({
  count,
  session,
  timestamp
}) => {
  return (
    <div className="summary-card">
      <div className="card-icon">📈</div>
      <div className="card-content">
        <h3>급등주 감지</h3>
        <div className="count-value">{count}개</div>
        <div className="session-info">
          {session === 'morning' ? '오전' : '오후'} {timestamp}
        </div>
      </div>
    </div>
  );
};
```

---

## 🔍 필터 바

```typescript
// components/Dashboard/FilterBar.tsx

interface FilterBarProps {
  filters: {
    session: string;
    triggerType: string;
    date: string;
  };
  onFilterChange: (filters: any) => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange
}) => {
  return (
    <div className="filter-bar">
      <div className="search-box">
        <input
          type="text"
          placeholder="종목명 또는 코드 검색..."
          onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
        />
        <span className="search-icon">🔍</span>
      </div>

      <div className="filter-dropdowns">
        {/* 세션 선택 */}
        <select
          value={filters.session}
          onChange={(e) => onFilterChange({ ...filters, session: e.target.value })}
        >
          <option value="all">전체 세션</option>
          <option value="morning">오전 (09:10)</option>
          <option value="afternoon">오후 (15:30)</option>
        </select>

        {/* 트리거 타입 선택 */}
        <select
          value={filters.triggerType}
          onChange={(e) => onFilterChange({ ...filters, triggerType: e.target.value })}
        >
          <option value="all">전체 트리거</option>
          <option value="volume_surge">거래량 급증</option>
          <option value="gap_up">갭 상승</option>
          <option value="fund_inflow">자금 유입</option>
          <option value="intraday_rise">일중 상승</option>
          <option value="closing_strength">마감 강도</option>
          <option value="sideways_volume">횡보주 거래량</option>
        </select>

        {/* 날짜 선택 */}
        <input
          type="date"
          value={filters.date}
          onChange={(e) => onFilterChange({ ...filters, date: e.target.value })}
        />
      </div>
    </div>
  );
};
```

---

## 📋 급등주 테이블

```typescript
// components/Dashboard/TriggerTable.tsx

interface Trigger {
  id: string;
  ticker: string;
  name: string;
  currentPrice: number;
  changeRate: number;
  volume: number;
  triggerType: string;
  compositeScore: number;
}

interface TriggerTableProps {
  triggers: Trigger[];
  onRefresh: () => void;
}

export const TriggerTable: React.FC<TriggerTableProps> = ({
  triggers,
  onRefresh
}) => {
  return (
    <div className="trigger-table-container">
      <div className="table-header">
        <h2>급등주 목록</h2>
        <button onClick={onRefresh} className="refresh-btn">
          🔄 새로고침
        </button>
        <button className="export-btn">📥 CSV 내보내기</button>
      </div>

      <table className="trigger-table">
        <thead>
          <tr>
            <th>#</th>
            <th>종목명</th>
            <th>종목코드</th>
            <th>현재가</th>
            <th>등락률</th>
            <th>거래량</th>
            <th>트리거 타입</th>
            <th>점수</th>
            <th>상세</th>
          </tr>
        </thead>
        <tbody>
          {triggers.map((trigger, index) => (
            <TriggerRow
              key={trigger.id}
              rank={index + 1}
              trigger={trigger}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

### TriggerRow 컴포넌트

```typescript
// components/Dashboard/TriggerTable/TriggerRow.tsx

interface TriggerRowProps {
  rank: number;
  trigger: Trigger;
}

export const TriggerRow: React.FC<TriggerRowProps> = ({ rank, trigger }) => {
  const navigate = useNavigate();

  const handleRowClick = () => {
    navigate(`/analysis/${trigger.ticker}`);
  };

  return (
    <tr
      className="trigger-row"
      onClick={handleRowClick}
      style={{ cursor: 'pointer' }}
    >
      <td>{rank}</td>
      <td className="stock-name">{trigger.name}</td>
      <td className="stock-ticker">{trigger.ticker}</td>
      <td className="price">
        {trigger.currentPrice.toLocaleString()}원
      </td>
      <td className={trigger.changeRate > 0 ? 'positive' : 'negative'}>
        {trigger.changeRate > 0 ? '+' : ''}
        {trigger.changeRate.toFixed(2)}%
      </td>
      <td className="volume">
        {formatVolume(trigger.volume)}
      </td>
      <td>
        <TriggerBadge type={trigger.triggerType} />
      </td>
      <td className="score">
        {trigger.compositeScore.toFixed(2)}
      </td>
      <td>
        <button
          className="detail-btn"
          onClick={(e) => {
            e.stopPropagation();
            navigate(`/analysis/${trigger.ticker}`);
          }}
        >
          📊 분석
        </button>
      </td>
    </tr>
  );
};

// 거래량 포맷팅
function formatVolume(volume: number): string {
  if (volume >= 1000000) {
    return `${(volume / 1000000).toFixed(1)}M`;
  } else if (volume >= 1000) {
    return `${(volume / 1000).toFixed(1)}K`;
  }
  return volume.toString();
}
```

### TriggerBadge 컴포넌트

```typescript
// components/Dashboard/TriggerTable/TriggerBadge.tsx

interface TriggerBadgeProps {
  type: string;
}

const TRIGGER_LABELS = {
  volume_surge: '거래량 급증',
  gap_up: '갭 상승',
  fund_inflow: '자금 유입',
  intraday_rise: '일중 상승',
  closing_strength: '마감 강도',
  sideways_volume: '횡보주 거래량'
};

const TRIGGER_COLORS = {
  volume_surge: '#FF6B6B',
  gap_up: '#4ECDC4',
  fund_inflow: '#45B7D1',
  intraday_rise: '#FFA07A',
  closing_strength: '#98D8C8',
  sideways_volume: '#F7DC6F'
};

export const TriggerBadge: React.FC<TriggerBadgeProps> = ({ type }) => {
  const label = TRIGGER_LABELS[type] || type;
  const color = TRIGGER_COLORS[type] || '#95a5a6';

  return (
    <span
      className="trigger-badge"
      style={{ backgroundColor: color }}
    >
      {label}
    </span>
  );
};
```

---

## 🔄 실시간 업데이트

### 1. WebSocket 연결 (선택사항)

```typescript
// hooks/useRealtimeUpdates.ts

import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

export const useRealtimeUpdates = (onUpdate: (data: any) => void) => {
  const [socket, setSocket] = useState<Socket | null>(null);

  useEffect(() => {
    // WebSocket 연결
    const newSocket = io('ws://localhost:8000', {
      transports: ['websocket']
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
    });

    newSocket.on('trigger_update', (data) => {
      console.log('New trigger detected:', data);
      onUpdate(data);
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    setSocket(newSocket);

    return () => {
      newSocket.close();
    };
  }, [onUpdate]);

  return socket;
};
```

### 2. Polling 방식 (기본)

```typescript
// hooks/useTriggers.ts

import { useState, useEffect, useCallback } from 'react';
import { fetchTriggers } from '@/services/api';

export const useTriggers = (filters: any) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      const result = await fetchTriggers(filters);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    refetch();

    // 1분마다 자동 갱신
    const interval = setInterval(refetch, 60000);

    return () => clearInterval(interval);
  }, [refetch]);

  return { data, loading, error, refetch };
};
```

---

## 🎨 스타일링 (Tailwind CSS)

```typescript
// components/Dashboard/Dashboard.tsx

<div className="min-h-screen bg-gray-50 p-6">
  {/* 요약 카드 */}
  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
    <SummaryCards />
  </div>

  {/* 필터 바 */}
  <div className="bg-white rounded-lg shadow p-4 mb-6">
    <FilterBar />
  </div>

  {/* 테이블 */}
  <div className="bg-white rounded-lg shadow overflow-hidden">
    <TriggerTable />
  </div>
</div>
```

---

## 📱 반응형 디자인

### 브레이크포인트

```css
/* Mobile: < 768px */
.dashboard {
  padding: 1rem;
}

.trigger-table {
  font-size: 0.875rem;
}

/* Tablet: 768px - 1024px */
@media (min-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Desktop: > 1024px */
@media (min-width: 1024px) {
  .summary-cards {
    grid-template-columns: repeat(3, 1fr);
  }

  .trigger-table {
    font-size: 1rem;
  }
}
```

---

## 🚀 성능 최적화

### 1. 가상 스크롤 (많은 데이터)

```typescript
import { FixedSizeList } from 'react-window';

const VirtualizedTriggerList = ({ triggers }) => (
  <FixedSizeList
    height={600}
    itemCount={triggers.length}
    itemSize={60}
    width="100%"
  >
    {({ index, style }) => (
      <div style={style}>
        <TriggerRow trigger={triggers[index]} />
      </div>
    )}
  </FixedSizeList>
);
```

### 2. 메모이제이션

```typescript
const MemoizedTriggerRow = React.memo(TriggerRow, (prev, next) => {
  return prev.trigger.id === next.trigger.id &&
         prev.trigger.currentPrice === next.trigger.currentPrice;
});
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
