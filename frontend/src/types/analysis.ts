// 참고: docs/backend/06-company-analysis.md
// 참고: backend/app/models/analysis.py

/**
 * 기업 분석 관련 타입 정의
 */

export type OpinionType =
  | 'STRONG_BUY'
  | 'BUY'
  | 'HOLD'
  | 'SELL'
  | 'STRONG_SELL'

export interface FinancialData {
  roe: number          // ROE (%)
  per: number          // PER
  pbr: number          // PBR
  debt_ratio: number   // 부채비율 (%)
  revenue_growth: number // 매출 성장률 (%)
}

export interface NewsData {
  positive_count: number
  negative_count: number
  neutral_count: number
  sentiment: 'positive' | 'neutral' | 'negative'
}

export interface TechnicalData {
  rsi: number
  macd_status: 'golden_cross' | 'dead_cross' | 'neutral'
  ma_position: '상회' | '하회' | '중립'
}

export interface Analysis {
  ticker: string
  name: string
  current_price: number
  change_rate: number
  market_cap: number

  // 분석 결과
  summary: string
  opinion: OpinionType
  target_price: number

  // 상세 분석
  financial: FinancialData
  news: NewsData
  technical: TechnicalData
  risks: string[]

  // 메타데이터
  analyzed_at: string
}

export interface AnalysisResponse {
  success: boolean
  data: Analysis
}

export interface MetricScore {
  ticker: string
  name: string
  total_score: number // 0-10
  breakdown: {
    momentum: number
    volume: number
    sentiment: number
    technical: number
    financial: number
  }
  calculated_at: string
}

export interface ComparisonData {
  ticker: string
  name: string
  sector: string
  sector_average: {
    per: number
    pbr: number
    roe: number
  }
  comparison: {
    per: '상회' | '하회' | '유사'
    pbr: '상회' | '하회' | '유사'
    roe: '상회' | '하회' | '유사'
  }
  ranking: {
    market_cap: number
    per: number
    roe: number
  }
  peers: Array<{
    ticker: string
    name: string
    per: number
    pbr: number
  }>
}

// 투자 의견 한글명
export const OPINION_LABELS: Record<OpinionType, string> = {
  STRONG_BUY: '적극 매수',
  BUY: '매수',
  HOLD: '보유',
  SELL: '매도',
  STRONG_SELL: '적극 매도',
}

// 투자 의견별 색상
export const OPINION_COLORS: Record<OpinionType, string> = {
  STRONG_BUY: 'text-red-600 bg-red-50',
  BUY: 'text-red-500 bg-red-50',
  HOLD: 'text-gray-600 bg-gray-50',
  SELL: 'text-blue-500 bg-blue-50',
  STRONG_SELL: 'text-blue-600 bg-blue-50',
}
