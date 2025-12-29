# 리포트 뷰어 (Reports Viewer)

## 📌 문서 목적

장 시작/마감 리포트를 표시하고 과거 리포트를 조회하는 뷰어 페이지 설계를 정의합니다.

---

## 🎨 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│  SKKU-INSIGHT > 리포트                                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────┐  ┌────────────┐  📅 2025-11-06             │
│  │ 🌅 장 시작 │  │ 🌆 장 마감 │                             │
│  └────────────┘  └────────────┘                             │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 📊 시장 전망                                           │  │
│  │                                                         │  │
│  │ 오늘의 시장은 미국 증시 상승과 원/달러 환율 안정에    │  │
│  │ 힘입어 소폭 상승 출발이 예상됩니다.                   │  │
│  │                                                         │  │
│  │ KOSPI 예상 범위: 2,630 ~ 2,680pt                       │  │
│  │                                                         │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⭐ 주목 종목 TOP 5                                     │  │
│  ├───┬─────────┬────────┬────────┬──────────────────────┤  │
│  │ # │ 종목명  │ 현재가 │ 점수   │ 선정 이유            │  │
│  ├───┼─────────┼────────┼────────┼──────────────────────┤  │
│  │ 1 │ 삼성전자│ 72,000 │ 9.2/10 │ HBM3 수주 확대      │  │
│  │ 2 │ SK하이닉│128,500 │ 8.8/10 │ D램 가격 상승       │  │
│  │...│         │        │        │                      │  │
│  └───┴─────────┴────────┴────────┴──────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🏭 섹터 분석                                           │  │
│  │ • 강세 예상: 반도체, 2차전지                          │  │
│  │ • 약세 예상: 은행, 건설                               │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 💡 투자 전략                                           │  │
│  │ 반도체 중심의 포트폴리오 유지. 단기 차익 실현 후      │  │
│  │ 조정 시 재진입 전략 권장.                             │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  📥 PDF 다운로드  |  📧 이메일 전송  |  🔗 공유             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧩 컴포넌트 구조

```
frontend/src/pages/ReportsPage/
├── ReportsPage.tsx             # 메인 페이지
├── components/
│   ├── ReportTabs.tsx          # 장 시작/마감 탭
│   ├── DatePicker.tsx          # 날짜 선택
│   ├── MorningReport/
│   │   ├── MarketForecast.tsx  # 시장 전망
│   │   ├── TopStocks.tsx       # 주목 종목
│   │   ├── SectorAnalysis.tsx  # 섹터 분석
│   │   └── Strategy.tsx        # 투자 전략
│   ├── AfternoonReport/
│   │   ├── MarketSummary.tsx   # 시장 요약
│   │   ├── SurgeStocks.tsx     # 급등주 분석
│   │   └── TomorrowStrategy.tsx # 내일 전략
│   └── ReportActions.tsx       # 액션 버튼 (PDF, 이메일)
```

---

## 📄 메인 페이지

```typescript
// pages/ReportsPage/ReportsPage.tsx

import React, { useState } from 'react';
import { useReport } from '@/hooks/useReport';
import {
  ReportTabs,
  DatePicker,
  MorningReport,
  AfternoonReport,
  ReportActions
} from './components';

export const ReportsPage: React.FC = () => {
  const [reportType, setReportType] = useState<'morning' | 'afternoon'>('morning');
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );

  const { data, loading, error } = useReport(reportType, selectedDate);

  if (loading) return <LoadingSkeleton />;
  if (error) return <ErrorDisplay error={error} />;

  const report = data?.report;

  return (
    <div className="reports-page">
      <div className="reports-header">
        <h1>📊 리포트</h1>
        <DatePicker
          value={selectedDate}
          onChange={setSelectedDate}
        />
      </div>

      <ReportTabs
        activeTab={reportType}
        onTabChange={setReportType}
      />

      <div className="report-content">
        {reportType === 'morning' ? (
          <MorningReport data={report} />
        ) : (
          <AfternoonReport data={report} />
        )}
      </div>

      <ReportActions
        reportType={reportType}
        date={selectedDate}
        data={report}
      />
    </div>
  );
};
```

---

## 🌅 장 시작 리포트

### 1. 시장 전망

```typescript
// components/MorningReport/MarketForecast.tsx

interface MarketForecastProps {
  forecast: {
    summary: string;
    kospiRange: {
      low: number;
      high: number;
    };
    keyFactors: string[];
  };
}

export const MarketForecast: React.FC<MarketForecastProps> = ({ forecast }) => {
  return (
    <div className="report-section">
      <h2>📊 시장 전망</h2>

      <div className="forecast-summary">
        <p>{forecast.summary}</p>
      </div>

      <div className="kospi-range">
        <h3>KOSPI 예상 범위</h3>
        <div className="range-display">
          <span className="range-value low">{forecast.kospiRange.low.toLocaleString()}pt</span>
          <div className="range-bar">
            <div className="range-indicator" />
          </div>
          <span className="range-value high">{forecast.kospiRange.high.toLocaleString()}pt</span>
        </div>
      </div>

      <div className="key-factors">
        <h3>주요 영향 요인</h3>
        <ul>
          {forecast.keyFactors.map((factor, idx) => (
            <li key={idx}>{factor}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
```

### 2. 주목 종목 Top 5

```typescript
// components/MorningReport/TopStocks.tsx

interface TopStock {
  rank: number;
  ticker: string;
  name: string;
  currentPrice: number;
  score: number;
  reason: string;
}

interface TopStocksProps {
  stocks: TopStock[];
}

export const TopStocks: React.FC<TopStocksProps> = ({ stocks }) => {
  return (
    <div className="report-section">
      <h2>⭐ 주목 종목 TOP 5</h2>

      <table className="top-stocks-table">
        <thead>
          <tr>
            <th>#</th>
            <th>종목명</th>
            <th>현재가</th>
            <th>점수</th>
            <th>선정 이유</th>
            <th>상세</th>
          </tr>
        </thead>
        <tbody>
          {stocks.map((stock) => (
            <tr key={stock.ticker}>
              <td className="rank">{stock.rank}</td>
              <td className="name">
                {stock.name}
                <span className="ticker">({stock.ticker})</span>
              </td>
              <td className="price">
                {stock.currentPrice.toLocaleString()}원
              </td>
              <td className="score">
                <ScoreBadge score={stock.score} />
              </td>
              <td className="reason">{stock.reason}</td>
              <td>
                <button
                  className="detail-btn"
                  onClick={() => window.open(`/analysis/${stock.ticker}`)}
                >
                  📊 분석
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const ScoreBadge: React.FC<{ score: number }> = ({ score }) => {
  const getColor = (score: number) => {
    if (score >= 9) return '#00C851';
    if (score >= 7) return '#33B5E5';
    if (score >= 5) return '#FFBB33';
    return '#FF8800';
  };

  return (
    <span
      className="score-badge"
      style={{ backgroundColor: getColor(score) }}
    >
      {score.toFixed(1)}/10
    </span>
  );
};
```

### 3. 섹터 분석

```typescript
// components/MorningReport/SectorAnalysis.tsx

interface SectorAnalysisProps {
  bullish: string[];  // 강세 예상 섹터
  bearish: string[];  // 약세 예상 섹터
}

export const SectorAnalysis: React.FC<SectorAnalysisProps> = ({
  bullish,
  bearish
}) => {
  return (
    <div className="report-section">
      <h2>🏭 섹터 분석</h2>

      <div className="sector-grid">
        <div className="sector-column bullish">
          <h3>📈 강세 예상</h3>
          <ul>
            {bullish.map((sector, idx) => (
              <li key={idx} className="sector-item">
                <span className="sector-icon">▲</span>
                {sector}
              </li>
            ))}
          </ul>
        </div>

        <div className="sector-column bearish">
          <h3>📉 약세 예상</h3>
          <ul>
            {bearish.map((sector, idx) => (
              <li key={idx} className="sector-item">
                <span className="sector-icon">▼</span>
                {sector}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
```

### 4. 투자 전략

```typescript
// components/MorningReport/Strategy.tsx

interface StrategyProps {
  strategy: string;
  entryPoints: string[];
  exitPoints: string[];
}

export const Strategy: React.FC<StrategyProps> = ({
  strategy,
  entryPoints,
  exitPoints
}) => {
  return (
    <div className="report-section strategy-section">
      <h2>💡 투자 전략</h2>

      <div className="strategy-summary">
        <p>{strategy}</p>
      </div>

      <div className="strategy-points">
        <div className="entry-points">
          <h3>✅ 진입 포인트</h3>
          <ul>
            {entryPoints.map((point, idx) => (
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>

        <div className="exit-points">
          <h3>🚪 청산 포인트</h3>
          <ul>
            {exitPoints.map((point, idx) => (
              <li key={idx}>{point}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
```

---

## 🌆 장 마감 리포트

### 1. 시장 요약

```typescript
// components/AfternoonReport/MarketSummary.tsx

interface MarketSummaryProps {
  summary: {
    kospiClose: number;
    kospiChange: number;
    tradingValue: number;
    foreignNet: number;
    institutionNet: number;
  };
}

export const MarketSummary: React.FC<MarketSummaryProps> = ({ summary }) => {
  return (
    <div className="report-section">
      <h2>📊 시장 요약</h2>

      <div className="summary-grid">
        <div className="summary-item">
          <div className="label">KOSPI</div>
          <div className="value">
            {summary.kospiClose.toLocaleString()}
            <span className={summary.kospiChange > 0 ? 'positive' : 'negative'}>
              {summary.kospiChange > 0 ? '+' : ''}{summary.kospiChange.toFixed(2)}%
            </span>
          </div>
        </div>

        <div className="summary-item">
          <div className="label">거래대금</div>
          <div className="value">
            {(summary.tradingValue / 1_000_000_000_000).toFixed(1)}조원
          </div>
        </div>

        <div className="summary-item">
          <div className="label">외국인</div>
          <div className="value">
            {summary.foreignNet > 0 ? '+' : ''}
            {(summary.foreignNet / 100_000_000).toFixed(0)}억원
          </div>
        </div>

        <div className="summary-item">
          <div className="label">기관</div>
          <div className="value">
            {summary.institutionNet > 0 ? '+' : ''}
            {(summary.institutionNet / 100_000_000).toFixed(0)}억원
          </div>
        </div>
      </div>
    </div>
  );
};
```

### 2. 급등주 상세 분석

```typescript
// components/AfternoonReport/SurgeStocks.tsx

interface SurgeStock {
  ticker: string;
  name: string;
  changeRate: number;
  triggerType: string;
  reason: string;
  outlook: string;
}

interface SurgeStocksProps {
  stocks: SurgeStock[];
}

export const SurgeStocks: React.FC<SurgeStocksProps> = ({ stocks }) => {
  return (
    <div className="report-section">
      <h2>📈 급등주 상세 분석</h2>

      {stocks.map((stock) => (
        <div key={stock.ticker} className="surge-stock-card">
          <div className="stock-header">
            <h3>
              {stock.name} ({stock.ticker})
              <span className="change-rate positive">
                +{stock.changeRate.toFixed(2)}%
              </span>
            </h3>
            <TriggerBadge type={stock.triggerType} />
          </div>

          <div className="stock-analysis">
            <div className="analysis-item">
              <h4>🔍 급등 이유</h4>
              <p>{stock.reason}</p>
            </div>

            <div className="analysis-item">
              <h4>🔮 향후 전망</h4>
              <p>{stock.outlook}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
```

---

## 📥 리포트 액션

```typescript
// components/ReportActions.tsx

interface ReportActionsProps {
  reportType: 'morning' | 'afternoon';
  date: string;
  data: any;
}

export const ReportActions: React.FC<ReportActionsProps> = ({
  reportType,
  date,
  data
}) => {
  const handleDownloadPDF = async () => {
    try {
      const response = await fetch(
        `/api/v1/reports/${reportType}/pdf?date=${date}`
      );
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${reportType}_report_${date}.pdf`;
      a.click();
    } catch (error) {
      console.error('PDF download failed:', error);
    }
  };

  const handleSendEmail = async () => {
    const email = prompt('이메일 주소를 입력하세요:');
    if (!email) return;

    try {
      await fetch('/api/v1/reports/email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reportType,
          date,
          email
        })
      });
      alert('이메일이 전송되었습니다.');
    } catch (error) {
      alert('이메일 전송에 실패했습니다.');
    }
  };

  const handleShare = async () => {
    const url = `${window.location.origin}/reports/${reportType}?date=${date}`;

    if (navigator.share) {
      await navigator.share({
        title: `${reportType === 'morning' ? '장 시작' : '장 마감'} 리포트`,
        url
      });
    } else {
      navigator.clipboard.writeText(url);
      alert('링크가 클립보드에 복사되었습니다.');
    }
  };

  return (
    <div className="report-actions">
      <button className="action-btn" onClick={handleDownloadPDF}>
        📥 PDF 다운로드
      </button>
      <button className="action-btn" onClick={handleSendEmail}>
        📧 이메일 전송
      </button>
      <button className="action-btn" onClick={handleShare}>
        🔗 공유
      </button>
    </div>
  );
};
```

---

## 📅 과거 리포트 조회

```typescript
// components/ReportHistory.tsx

export const ReportHistory: React.FC = () => {
  const [reports, setReports] = useState([]);

  useEffect(() => {
    fetchReportHistory().then(setReports);
  }, []);

  return (
    <div className="report-history">
      <h2>📚 과거 리포트</h2>

      <div className="history-list">
        {reports.map((report) => (
          <div key={report.id} className="history-item">
            <div className="report-info">
              <span className="report-date">{report.date}</span>
              <span className="report-type">
                {report.type === 'morning' ? '🌅 장 시작' : '🌆 장 마감'}
              </span>
            </div>
            <button
              className="view-btn"
              onClick={() => window.open(`/reports/${report.type}?date=${report.date}`)}
            >
              보기
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 🎨 스타일링

```css
/* reports.css */

.report-section {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 16px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.report-section h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #333;
}

.top-stocks-table {
  width: 100%;
  border-collapse: collapse;
}

.top-stocks-table th,
.top-stocks-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.score-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  color: white;
  font-weight: 600;
  font-size: 14px;
}

.report-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  padding: 24px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-top: 24px;
}

.action-btn {
  padding: 12px 24px;
  background: #2196F3;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.3s;
}

.action-btn:hover {
  background: #1976D2;
}
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
