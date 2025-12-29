# 기업 분석 페이지 (Stock Analysis Page)

## 📌 문서 목적

개별 종목의 상세 분석 결과를 표시하는 페이지 설계 및 구현 방법을 정의합니다.

---

## 🎨 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  ← 뒤로가기         삼성전자 (005930)                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐│
│  │ 💰 현재가       │  │ 📊 시가총액    │  │ 📈 투자의견  ││
│  │ 72,000원        │  │ 430조원         │  │ 강력 매수    ││
│  │ +3,500 (+5.1%) │  │ PER 12.5       │  │ ⭐⭐⭐⭐⭐  ││
│  └─────────────────┘  └─────────────────┘  └──────────────┘│
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📌 요약                                                 │  │
│  │ 반도체 업황 개선에 따른 실적 개선 전망. HBM3 수주 증가로│  │
│  │ 향후 3개월간 상승 여력 높음. 목표가 80,000원.          │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📊 가격 차트                          [1D][1W][1M][3M]│  │
│  │ ┌───────────────────────────────────────────────────┐│  │
│  │ │                        ╱╲                         ││  │
│  │ │                   ╱╲  ╱  ╲                        ││  │
│  │ │              ╱╲  ╱  ╲╱    ╲                       ││  │
│  │ │         ╱╲  ╱  ╲╱            ╲                    ││  │
│  │ │    ╱╲  ╱  ╲╱                  ╲                   ││  │
│  │ │───╱──╲╱────────────────────────╲──────────────────││  │
│  │ └───────────────────────────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────┐  ┌────────────────────┐             │
│  │ 📝 재무 분석       │  │ 📰 뉴스 분석       │             │
│  │ • ROE: 15.2%      │  │ • 긍정 뉴스 8건   │             │
│  │ • PER: 12.5       │  │ • 부정 뉴스 2건   │             │
│  │ • 부채비율: 45%   │  │ • 센티먼트: 긍정  │             │
│  └────────────────────┘  └────────────────────┘             │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🔧 기술적 분석                                         │  │
│  │ • RSI: 65 (중립)                                       │  │
│  │ • MACD: 골든크로스                                     │  │
│  │ • 20일 이동평균선 상회                                │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚠️ 리스크 요인                                         │  │
│  │ 1. 미중 무역 분쟁 심화 가능성                         │  │
│  │ 2. 글로벌 반도체 수요 둔화 우려                       │  │
│  │ 3. 환율 변동성 확대                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 컴포넌트 구조

```
frontend/src/pages/StockAnalysisPage/
├── StockAnalysisPage.tsx       # 메인 페이지 컨테이너
├── components/
│   ├── StockHeader.tsx         # 종목 헤더 (종목명, 가격)
│   ├── SummaryCards.tsx        # 요약 카드 (가격, 시총, 의견)
│   ├── QuickSummary.tsx        # 한줄 요약
│   ├── PriceChart.tsx          # 가격 차트
│   ├── FinancialAnalysis.tsx   # 재무 분석
│   ├── NewsAnalysis.tsx        # 뉴스 분석
│   ├── TechnicalAnalysis.tsx   # 기술적 분석
│   ├── RiskFactors.tsx         # 리스크 요인
│   └── InvestmentStrategy.tsx  # 투자 전략
```

---

## 📄 메인 페이지 컴포넌트

```typescript
// pages/StockAnalysisPage/StockAnalysisPage.tsx

import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useStockAnalysis } from '@/hooks/useStockAnalysis';
import {
  StockHeader,
  SummaryCards,
  QuickSummary,
  PriceChart,
  FinancialAnalysis,
  NewsAnalysis,
  TechnicalAnalysis,
  RiskFactors,
  InvestmentStrategy
} from './components';

export const StockAnalysisPage: React.FC = () => {
  const { ticker } = useParams<{ ticker: string }>();
  const { data, loading, error, refetch } = useStockAnalysis(ticker);

  const [chartPeriod, setChartPeriod] = useState<'1D' | '1W' | '1M' | '3M'>('1M');

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <ErrorDisplay
        error={error}
        onRetry={refetch}
      />
    );
  }

  const analysis = data?.analysis;

  return (
    <div className="stock-analysis-page">
      <StockHeader
        ticker={ticker}
        name={analysis.stockName}
        onBack={() => window.history.back()}
      />

      <SummaryCards
        currentPrice={analysis.currentPrice}
        changeRate={analysis.changeRate}
        marketCap={analysis.marketCap}
        per={analysis.per}
        opinion={analysis.opinion}
        targetPrice={analysis.targetPrice}
      />

      <QuickSummary summary={analysis.summary} />

      <PriceChart
        ticker={ticker}
        period={chartPeriod}
        onPeriodChange={setChartPeriod}
      />

      <div className="analysis-grid">
        <FinancialAnalysis data={analysis.financial} />
        <NewsAnalysis data={analysis.news} />
      </div>

      <TechnicalAnalysis data={analysis.technical} />

      <RiskFactors risks={analysis.risks} />

      <InvestmentStrategy
        shortTerm={analysis.strategy.shortTerm}
        midTerm={analysis.strategy.midTerm}
        longTerm={analysis.strategy.longTerm}
      />
    </div>
  );
};
```

---

## 📊 요약 카드

```typescript
// components/SummaryCards.tsx

interface SummaryCardsProps {
  currentPrice: number;
  changeRate: number;
  marketCap: number;
  per: number;
  opinion: string;
  targetPrice: number;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  currentPrice,
  changeRate,
  marketCap,
  per,
  opinion,
  targetPrice
}) => {
  const isPositive = changeRate > 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {/* 현재가 카드 */}
      <div className="summary-card">
        <div className="card-label">💰 현재가</div>
        <div className="card-value">
          {currentPrice.toLocaleString()}원
        </div>
        <div className={`card-change ${isPositive ? 'positive' : 'negative'}`}>
          {isPositive ? '+' : ''}{(currentPrice * changeRate / 100).toLocaleString()}
          ({isPositive ? '+' : ''}{changeRate.toFixed(2)}%)
        </div>
      </div>

      {/* 시가총액 카드 */}
      <div className="summary-card">
        <div className="card-label">📊 시가총액</div>
        <div className="card-value">
          {(marketCap / 1_000_000_000_000).toFixed(0)}조원
        </div>
        <div className="card-detail">
          PER {per.toFixed(1)}
        </div>
      </div>

      {/* 투자의견 카드 */}
      <div className="summary-card opinion-card">
        <div className="card-label">📈 투자의견</div>
        <div className="card-value">
          <OpinionBadge opinion={opinion} />
        </div>
        <div className="card-detail">
          목표가 {targetPrice.toLocaleString()}원
        </div>
      </div>
    </div>
  );
};

// 투자의견 뱃지
const OpinionBadge: React.FC<{ opinion: string }> = ({ opinion }) => {
  const configs = {
    'STRONG_BUY': { label: '강력 매수', color: '#00C851', stars: 5 },
    'BUY': { label: '매수', color: '#33B5E5', stars: 4 },
    'HOLD': { label: '중립', color: '#FFBB33', stars: 3 },
    'SELL': { label: '매도', color: '#FF8800', stars: 2 },
    'STRONG_SELL': { label: '강력 매도', color: '#FF4444', stars: 1 }
  };

  const config = configs[opinion] || configs['HOLD'];

  return (
    <div className="opinion-badge" style={{ backgroundColor: config.color }}>
      <span className="opinion-label">{config.label}</span>
      <span className="opinion-stars">{'⭐'.repeat(config.stars)}</span>
    </div>
  );
};
```

---

## 📈 가격 차트

```typescript
// components/PriceChart.tsx

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { usePriceHistory } from '@/hooks/usePriceHistory';

interface PriceChartProps {
  ticker: string;
  period: '1D' | '1W' | '1M' | '3M';
  onPeriodChange: (period: '1D' | '1W' | '1M' | '3M') => void;
}

export const PriceChart: React.FC<PriceChartProps> = ({
  ticker,
  period,
  onPeriodChange
}) => {
  const { data: priceData, loading } = usePriceHistory(ticker, period);

  return (
    <div className="price-chart-container">
      <div className="chart-header">
        <h3>📊 가격 차트</h3>
        <div className="period-buttons">
          {(['1D', '1W', '1M', '3M'] as const).map((p) => (
            <button
              key={p}
              className={`period-btn ${period === p ? 'active' : ''}`}
              onClick={() => onPeriodChange(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={priceData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="date"
            tickFormatter={(date) => new Date(date).toLocaleDateString('ko-KR', {
              month: 'short',
              day: 'numeric'
            })}
          />
          <YAxis
            domain={['dataMin - 1000', 'dataMax + 1000']}
            tickFormatter={(value) => value.toLocaleString()}
          />
          <Tooltip
            labelFormatter={(date) => new Date(date).toLocaleDateString('ko-KR')}
            formatter={(value: number) => [`${value.toLocaleString()}원`, '종가']}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#2196F3"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
```

---

## 💰 재무 분석

```typescript
// components/FinancialAnalysis.tsx

interface FinancialAnalysisProps {
  data: {
    roe: number;
    per: number;
    pbr: number;
    debtRatio: number;
    revenueGrowth: number;
  };
}

export const FinancialAnalysis: React.FC<FinancialAnalysisProps> = ({ data }) => {
  return (
    <div className="analysis-card">
      <h3>📝 재무 분석</h3>

      <div className="metric-list">
        <MetricItem
          label="ROE (자기자본이익률)"
          value={`${data.roe.toFixed(1)}%`}
          status={data.roe >= 15 ? 'good' : data.roe >= 10 ? 'neutral' : 'bad'}
        />

        <MetricItem
          label="PER (주가수익비율)"
          value={data.per.toFixed(1)}
          status={data.per <= 15 ? 'good' : data.per <= 20 ? 'neutral' : 'bad'}
        />

        <MetricItem
          label="PBR (주가순자산비율)"
          value={data.pbr.toFixed(1)}
          status={data.pbr <= 1 ? 'good' : data.pbr <= 2 ? 'neutral' : 'bad'}
        />

        <MetricItem
          label="부채비율"
          value={`${data.debtRatio.toFixed(1)}%`}
          status={data.debtRatio <= 50 ? 'good' : data.debtRatio <= 100 ? 'neutral' : 'bad'}
        />

        <MetricItem
          label="매출 성장률 (YoY)"
          value={`${data.revenueGrowth > 0 ? '+' : ''}${data.revenueGrowth.toFixed(1)}%`}
          status={data.revenueGrowth >= 10 ? 'good' : data.revenueGrowth >= 0 ? 'neutral' : 'bad'}
        />
      </div>
    </div>
  );
};

// 지표 아이템
const MetricItem: React.FC<{
  label: string;
  value: string;
  status: 'good' | 'neutral' | 'bad';
}> = ({ label, value, status }) => {
  const statusColors = {
    good: '#00C851',
    neutral: '#FFBB33',
    bad: '#FF4444'
  };

  return (
    <div className="metric-item">
      <span className="metric-label">{label}</span>
      <span className="metric-value" style={{ color: statusColors[status] }}>
        {value}
      </span>
    </div>
  );
};
```

---

## 📰 뉴스 분석

```typescript
// components/NewsAnalysis.tsx

interface NewsAnalysisProps {
  data: {
    positiveCount: number;
    negativeCount: number;
    neutralCount: number;
    sentiment: 'positive' | 'neutral' | 'negative';
    recentNews: Array<{
      title: string;
      date: string;
      sentiment: 'positive' | 'negative';
    }>;
  };
}

export const NewsAnalysis: React.FC<NewsAnalysisProps> = ({ data }) => {
  return (
    <div className="analysis-card">
      <h3>📰 뉴스 분석 (최근 1주일)</h3>

      <div className="sentiment-summary">
        <div className="sentiment-item positive">
          긍정 뉴스 {data.positiveCount}건
        </div>
        <div className="sentiment-item negative">
          부정 뉴스 {data.negativeCount}건
        </div>
        <div className="sentiment-item neutral">
          중립 뉴스 {data.neutralCount}건
        </div>
      </div>

      <div className="overall-sentiment">
        종합 센티먼트:
        <SentimentBadge sentiment={data.sentiment} />
      </div>

      <div className="recent-news-list">
        <h4>주요 뉴스</h4>
        {data.recentNews.map((news, idx) => (
          <div key={idx} className="news-item">
            <span className={`news-icon ${news.sentiment}`}>
              {news.sentiment === 'positive' ? '📈' : '📉'}
            </span>
            <div className="news-content">
              <div className="news-title">{news.title}</div>
              <div className="news-date">{news.date}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const SentimentBadge: React.FC<{ sentiment: string }> = ({ sentiment }) => {
  const configs = {
    positive: { label: '긍정', color: '#00C851' },
    neutral: { label: '중립', color: '#FFBB33' },
    negative: { label: '부정', color: '#FF4444' }
  };

  const config = configs[sentiment] || configs.neutral;

  return (
    <span
      className="sentiment-badge"
      style={{ backgroundColor: config.color }}
    >
      {config.label}
    </span>
  );
};
```

---

## 🔧 기술적 분석

```typescript
// components/TechnicalAnalysis.tsx

interface TechnicalAnalysisProps {
  data: {
    rsi: number;
    macd: {
      status: 'golden_cross' | 'dead_cross' | 'neutral';
    };
    movingAverage: {
      position: '상회' | '하회' | '중립';
    };
    bollingerBands: {
      position: '상단돌파' | '하단돌파' | '밴드내';
    };
  };
}

export const TechnicalAnalysis: React.FC<TechnicalAnalysisProps> = ({ data }) => {
  return (
    <div className="analysis-card full-width">
      <h3>🔧 기술적 분석</h3>

      <div className="technical-metrics">
        <div className="tech-metric">
          <span className="tech-label">RSI (14일)</span>
          <span className="tech-value">{data.rsi.toFixed(1)}</span>
          <span className="tech-status">
            {data.rsi >= 70 ? '과매수' :
             data.rsi <= 30 ? '과매도' : '중립'}
          </span>
        </div>

        <div className="tech-metric">
          <span className="tech-label">MACD</span>
          <span className="tech-value">
            {data.macd.status === 'golden_cross' ? '골든크로스' :
             data.macd.status === 'dead_cross' ? '데드크로스' : '중립'}
          </span>
        </div>

        <div className="tech-metric">
          <span className="tech-label">20일 이동평균선</span>
          <span className="tech-value">{data.movingAverage.position}</span>
        </div>

        <div className="tech-metric">
          <span className="tech-label">볼린저 밴드</span>
          <span className="tech-value">{data.bollingerBands.position}</span>
        </div>
      </div>
    </div>
  );
};
```

---

## ⚠️ 리스크 요인

```typescript
// components/RiskFactors.tsx

interface RiskFactorsProps {
  risks: string[];
}

export const RiskFactors: React.FC<RiskFactorsProps> = ({ risks }) => {
  return (
    <div className="analysis-card warning-card">
      <h3>⚠️ 리스크 요인</h3>

      <ul className="risk-list">
        {risks.map((risk, idx) => (
          <li key={idx} className="risk-item">
            <span className="risk-number">{idx + 1}.</span>
            <span className="risk-text">{risk}</span>
          </li>
        ))}
      </ul>
    </div>
  );
};
```

---

## 🎯 투자 전략

```typescript
// components/InvestmentStrategy.tsx

interface InvestmentStrategyProps {
  shortTerm: string;
  midTerm: string;
  longTerm: string;
}

export const InvestmentStrategy: React.FC<InvestmentStrategyProps> = ({
  shortTerm,
  midTerm,
  longTerm
}) => {
  return (
    <div className="analysis-card strategy-card">
      <h3>🎯 투자 전략</h3>

      <div className="strategy-grid">
        <div className="strategy-item">
          <h4>단기 (1-2주)</h4>
          <p>{shortTerm}</p>
        </div>

        <div className="strategy-item">
          <h4>중기 (1-3개월)</h4>
          <p>{midTerm}</p>
        </div>

        <div className="strategy-item">
          <h4>장기 (6개월+)</h4>
          <p>{longTerm}</p>
        </div>
      </div>
    </div>
  );
};
```

---

## 🔄 데이터 훅

```typescript
// hooks/useStockAnalysis.ts

import { useState, useEffect } from 'react';
import { fetchAnalysis } from '@/services/api';

export const useStockAnalysis = (ticker: string) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refetch = async () => {
    try {
      setLoading(true);
      const result = await fetchAnalysis(ticker);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refetch();
  }, [ticker]);

  return { data, loading, error, refetch };
};
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: MINT 개발팀
