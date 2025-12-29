// 참고: docs/backend/01-data-collection.md
// 참고: backend/app/models/stock.py

/**
 * 종목 관련 타입 정의
 */

export interface Stock {
  ticker: string
  name: string
  market: 'KOSPI' | 'KOSDAQ'
  market_cap: number
  sector?: string
}

export interface StockPrice {
  ticker: string
  date: string // YYYY-MM-DD
  open: number
  high: number
  low: number
  close: number
  volume: number
  trading_value: number
}

export interface StockResponse {
  success: boolean
  data: Stock
}

export interface StockPriceHistoryResponse {
  success: boolean
  data: {
    ticker: string
    period: {
      start: string
      end: string
    }
    prices: StockPrice[]
  }
}

export interface CurrentPriceData {
  ticker: string
  name: string
  current_price: number
  change_rate: number
  volume: number
  trading_value: number
  timestamp: string
}

export interface TechnicalIndicators {
  ticker: string
  date: string
  rsi: number
  macd: number
  macd_signal: number
  macd_status: 'golden_cross' | 'dead_cross' | 'neutral'
  ma5: number
  ma20: number
  ma60: number
  ma_position: '상회' | '하회' | '중립'
}
