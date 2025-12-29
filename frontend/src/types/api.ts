/**
 * Backend API 타입 정의
 *
 * backend/app/db/models.py와 동기화
 */

// ============= 공통 타입 =============

/**
 * API 응답 공통 포맷
 */
export interface ApiResponse<T> {
  data: T
  message?: string
  timestamp?: string
}

/**
 * 페이지네이션 응답
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/**
 * 에러 응답
 */
export interface ApiError {
  detail?: string
  message?: string
  error?: string
  status?: number
}

// ============= 재무 데이터 =============

/**
 * 재무 데이터 (FinancialData 모델)
 */
export interface FinancialData {
  ticker: string
  name: string | null
  // 재무 지표
  bps: number // 주당순자산가치
  per: number // 주가수익비율
  pbr: number // 주가순자산비율
  eps: number // 주당순이익
  div: number // 배당수익률
  dps: number // 주당배당금
  // 계산된 지표
  roe: number // 자기자본이익률
  // DART API 지표
  debt_ratio: number // 부채비율
  revenue_growth_yoy: number // 매출 성장률
  // 메타데이터
  market_cap: number // 시가총액 (억원)
  updated_at: string | null // ISO 8601
}

// ============= 급등주 트리거 =============

/**
 * 트리거 타입
 */
export type TriggerType =
  | 'volume_surge' // 거래량 급증
  | 'gap_up' // 갭 상승 모멘텀
  | 'fund_inflow' // 시총 대비 자금유입
  | 'intraday_rise' // 일중 상승률
  | 'closing_strength' // 마감 강도
  | 'sideways_volume' // 횡보주 거래량

/**
 * 세션 (장 시간)
 */
export type Session = 'morning' | 'afternoon'

/**
 * 급등주 트리거 결과 (Backend Trigger 모델)
 */
export interface Trigger {
  ticker: string
  name: string
  trigger_type: TriggerType
  session: Session
  // 가격/거래 정보
  current_price: number
  change_rate: number // 등락률 (%)
  volume: number
  trading_value: number // 거래대금
  // 점수
  composite_score: number
  // 메타데이터
  detected_at: string // ISO 8601
}

/**
 * 트리거 메타데이터
 */
export interface TriggerMetadata {
  date: string // YYYY-MM-DD
  session: string // "morning" | "afternoon" | "all"
  total: number
  trigger_types: Record<string, number>
}

/**
 * 트리거 조회 요청
 */
export interface GetTriggersRequest {
  date?: string // YYYY-MM-DD, 기본값: 오늘
  session?: Session // morning 또는 afternoon
  trigger_type?: TriggerType
}

/**
 * 트리거 조회 응답 (Backend 실제 응답 형식)
 */
export interface GetTriggersResponse {
  triggers: Trigger[]
  metadata: TriggerMetadata
}

// Backward compatibility (deprecated)
export type TriggerResult = Trigger

// ============= 장 시작/마감 리포트 =============

/**
 * 주목 종목 (Top 10)
 */
export interface FocusStock {
  ticker: string
  name: string
  rank: number // 1-10
  // 가격 정보
  current_price: number
  change_rate: number
  // 점수
  total_score: number
  momentum_score: number
  volume_score: number
  technical_score: number
  sentiment_score: number
  // 진입 전략 (Morning Report)
  entry_strategy?: {
    analysis?: string // Chain-of-Thought: 진입 판단 분석
    entry_price: number // 진입가
    entry_timing: string // 진입 타이밍
    target_price_1: number // 1차 목표가 (ATR 기반)
    target_price_2: number // 2차 목표가 (ATR 기반)
    stop_loss: number // 손절가 (ATR 기반)
    risk_reward_ratio: string // 손익비
    holding_period: string // 보유기간
    technical_basis: string // 기술적 근거
    volume_strategy: string // 거래량 전략
    exit_condition: string // 청산 조건
    confidence?: number // 전략 신뢰도 (0.0~1.0)
  }
}

/**
 * 시장 요약
 */
export interface MarketSummary {
  kospi_close: number
  kospi_change: number // %
  trading_value: number // 거래대금 (억원)
  foreign_net: number // 외국인 순매수 (억원)
  institution_net: number // 기관 순매수 (억원)
}

/**
 * 주목 종목 (Backend에서 실제로 반환하는 형식)
 */
export interface TopStock {
  ticker: string
  name: string
  rank: number // 1-10
  current_price: number
  score: number
  reason: string
  entry_strategy: {
    analysis?: string // Chain-of-Thought: 진입 판단 분석
    entry_price: number
    entry_timing: string
    target_price_1: number // ATR 기반
    target_price_2: number // ATR 기반
    stop_loss: number // ATR 기반
    risk_reward_ratio: string
    holding_period: string
    technical_basis: string
    volume_strategy: string
    exit_condition: string
    confidence?: number // 전략 신뢰도 (0.0~1.0)
  }
}

/**
 * 섹터 항목
 */
export interface SectorItem {
  sector: string
  reason: string
}

/**
 * 장 시작 리포트 (Morning Report)
 *
 * Backend 실제 응답 형식에 맞춤
 */
export interface MorningReport {
  report_type: 'morning'
  date: string // YYYY-MM-DD
  generated_at: string // ISO 8601
  // 시장 전망
  market_forecast: string // 전체 전망 텍스트
  kospi_range: {
    low: number
    high: number
    reasoning: string
  }
  market_risks: string[]
  // 주목 종목 Top 10
  top_stocks: TopStock[]
  // 섹터 분석
  sector_analysis: {
    bullish: SectorItem[] // 강세 예상 업종
    bearish: SectorItem[] // 약세 예상 업종
  }
  // 투자 전략
  investment_strategy: string
  // 시간대별 전략 (키: "09:00_09:30", 값: 전략 텍스트)
  daily_schedule: Record<string, string>
  // 메타데이터
  metadata?: {
    market_data?: MarketSummary
    grounding_sources?: any[]
    tokens_used?: number
  }
}

/**
 * 확장된 시장 요약 (KOSPI + KOSDAQ + 수급 + 시장폭)
 */
export interface ExtendedMarketSummary {
  // KOSPI
  kospi_close: number
  kospi_change: number // %
  kospi_point_change: number

  // KOSDAQ
  kosdaq_close: number
  kosdaq_change: number // %
  kosdaq_point_change: number

  // 거래대금 (억원)
  trading_value: number

  // 수급 - KOSPI (억원)
  foreign_net_kospi: number
  institution_net_kospi: number
  individual_net_kospi: number

  // 수급 - KOSDAQ (억원)
  foreign_net_kosdaq: number
  institution_net_kosdaq: number
  individual_net_kosdaq: number

  // 시장 폭 (Market Breadth)
  advance_count: number // 상승 종목 수
  decline_count: number // 하락 종목 수
  unchanged_count: number // 보합 종목 수
}

/**
 * 시장 폭 분석
 */
export interface MarketBreadth {
  sentiment: string // 강세장/약세장/혼조세
  interpretation: string // 해석 텍스트
}

/**
 * 업종 정보 (상세)
 */
export interface SectorInfoDetail {
  sector: string
  change: string // 예: "+2.09%"
  reason: string
}

/**
 * 업종별 분석
 */
export interface SectorAnalysisDetail {
  bullish: SectorInfoDetail[]
  bearish: SectorInfoDetail[]
}

/**
 * 테마 분석
 */
export interface ThemeAnalysis {
  theme: string
  drivers: string
  leading_stocks: string[]
}

/**
 * 급등주 분석 (상세)
 */
export interface SurgeStockAnalysis {
  ticker: string
  name: string
  change_rate?: number
  trigger_type?: string
  category: string // 테마/업종
  reason: string // 급등 사유
  outlook: string // 향후 전망
}

/**
 * 장 마감 리포트 (Afternoon Report)
 *
 * 증권사 장마감 시황 보고서 형식
 */
export interface AfternoonReport {
  report_type: 'afternoon'
  date: string // YYYY-MM-DD
  generated_at: string // ISO 8601

  // 확장된 시장 요약
  market_summary: ExtendedMarketSummary
  market_summary_text: string // LLM 생성 시장 요약 텍스트

  // 시장 폭 분석
  market_breadth?: MarketBreadth

  // 업종별 분석
  sector_analysis?: SectorAnalysisDetail

  // 수급 해석
  supply_demand_analysis: string

  // 오늘의 테마
  today_themes: ThemeAnalysis[]

  // 급등주 분석 (Google Search Grounding 포함)
  surge_analysis: SurgeStockAnalysis[]

  // 내일 전략
  tomorrow_strategy: string

  // 내일 확인 사항
  check_points: string[]

  // 메타데이터
  metadata?: {
    model?: string
    tokens_used?: number
    grounding_sources?: any[]
  }
}

/**
 * 리포트 타입
 */
export type ReportType = 'morning' | 'afternoon'

/**
 * 리포트 조회 요청
 */
export interface GetReportRequest {
  type: ReportType
  date?: string // YYYY-MM-DD, 기본값: 오늘
}

// ============= 기업 분석 =============

/**
 * 투자 의견
 */
export type InvestmentOpinion =
  | 'strong_buy' // 강력 매수
  | 'buy' // 매수
  | 'hold' // 보유
  | 'sell' // 매도
  | 'strong_sell' // 강력 매도

/**
 * 기업 분석 결과 (AnalysisResult 모델)
 */
export interface CompanyAnalysis {
  ticker: string
  date: string // YYYY-MM-DD
  // 요약
  summary: {
    opinion: InvestmentOpinion
    target_price: number
    current_price: number
    upside: number // %
    key_points: string[] // 핵심 근거 (3개)
  }
  // 재무 분석
  financial_analysis: {
    profitability: string // 수익성 평가
    growth: string // 성장성 평가
    stability: string // 안정성 평가
    valuation: string // 밸류에이션 평가
  }
  // 산업 및 경쟁 분석
  industry_analysis: {
    industry_trend: string // 업종 트렌드
    competitive_advantage: string // 경쟁 우위
    market_position: string // 시장 지위
  }
  // 기술적 분석
  technical_analysis: {
    trend: string // 추세
    support_resistance: string // 지지/저항
    indicators: string // 지표 분석
  }
  // 뉴스 분석
  news_analysis: {
    sentiment: 'positive' | 'neutral' | 'negative'
    key_news: string[]
    impact: string
  }
  // 리스크 요인
  risk_factors: string[]
  // 투자 전략
  investment_strategy: {
    short_term: string // 단기 (1주-1개월)
    mid_term: string // 중기 (1-3개월)
    long_term: string // 장기 (3개월+)
  }
  // 메타데이터
  generated_at: string // ISO 8601
  model_name: string
  tokens_used: number
}

/**
 * 기업 분석 조회 요청
 */
export interface GetAnalysisRequest {
  ticker: string
  date?: string // YYYY-MM-DD, 기본값: 오늘
  force_refresh?: boolean // 캐시 무시하고 재생성
}

// ============= 종목 목록 =============

/**
 * 종목 기본 정보 (DB 저장 데이터 중심)
 */
export interface Stock {
  ticker: string
  name: string
  market: string // 시장 (KOSPI/KOSDAQ)
  market_cap: number // 시가총액 (억원)
  sector?: string // 업종

  // 재무 지표 (DB에서 조회)
  per?: number // PER (주가수익비율)
  pbr?: number // PBR (주가순자산비율)
  eps?: number // EPS (주당순이익)
  bps?: number // BPS (주당순자산)
  roe?: number // ROE (자기자본이익률, %)
  debt_ratio?: number // 부채비율 (%)
  div?: number // 배당수익률 (%)
  dps?: number // 주당배당금
  revenue_growth_yoy?: number // 매출 성장률 (YoY, %)
  updated_at?: string // 재무 데이터 업데이트 일시
}

/**
 * 종목 조회 요청
 */
export interface GetStocksRequest {
  keyword?: string // 종목명 또는 티커 검색
  market?: string // 시장 (KOSPI/KOSDAQ)
  // 재무 지표 필터
  min_per?: number // 최소 PER
  max_per?: number // 최대 PER
  min_pbr?: number // 최소 PBR
  max_pbr?: number // 최대 PBR
  min_roe?: number // 최소 ROE (%)
  max_roe?: number // 최대 ROE (%)
  // 시가총액 필터
  min_market_cap?: number // 최소 시가총액 (억원)
  max_market_cap?: number // 최대 시가총액 (억원)
  // 정렬
  sort_by?: 'market_cap' | 'per' | 'pbr' | 'roe' | 'name' // 정렬 기준
  sort_order?: 'asc' | 'desc' // 정렬 순서
  // 페이지네이션
  limit?: number // 최대 결과 수
  page?: number
  page_size?: number
}

/**
 * 종목 조회 응답 (Backend 실제 응답 형식, API client가 unwrap)
 */
export interface GetStocksResponse {
  total: number
  stocks: Stock[]
}
