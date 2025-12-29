// 참고: docs/backend/07-market-reports.md
// 참고: backend/app/models/report.py

/**
 * 시장 리포트 관련 타입 정의
 */

export interface TopStock {
  rank: number
  ticker: string
  name: string
  current_price: number
  score: number // 0-10
  reason: string
}

export interface SurgeStock {
  ticker: string
  name: string
  change_rate: number
  trigger_type: string
  reason: string
  outlook: string
}

export interface MorningReport {
  report_type: 'morning'
  date: string
  generated_at: string

  // 시장 전망
  market_forecast: string
  kospi_range: {
    low: number
    high: number
  }

  // 주목 종목
  top_stocks: TopStock[]

  // 섹터 분석
  sector_analysis: {
    bullish: string[]
    bearish: string[]
  }

  // 투자 전략
  investment_strategy: string

  // 메타데이터
  metadata: {
    model: string
    tokens_used: number
  }
}

export interface AfternoonReport {
  report_type: 'afternoon'
  date: string
  generated_at: string

  // 시장 요약
  market_summary: {
    kospi_close: number
    kospi_change: number
    trading_value: number
    foreign_net: number
    institution_net: number
  }

  // 급등주 분석
  surge_stocks: SurgeStock[]

  // 내일 전략
  tomorrow_strategy: string

  // 메타데이터
  metadata: {
    model: string
    tokens_used: number
  }
}

export type Report = MorningReport | AfternoonReport

export interface ReportResponse {
  success: boolean
  data: Report
}

export interface ReportListItem {
  date: string
  report_type: 'morning' | 'afternoon'
  generated_at: string
  summary: string
  id: string
}

export interface ReportStats {
  total_reports: number
  by_type: {
    morning: number
    afternoon: number
  }
  last_generated: {
    morning: string
    afternoon: string
  }
  average_tokens: {
    morning: number
    afternoon: number
  }
  total_cost_estimate: number // USD
}

// 리포트 타입 한글명
export const REPORT_TYPE_LABELS = {
  morning: '장 시작 리포트',
  afternoon: '장 마감 리포트',
} as const
