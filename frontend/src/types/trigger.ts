// 참고: docs/backend/02-trigger-detection.md
// 참고: backend/app/models/trigger.py

/**
 * 급등주 트리거 관련 타입 정의
 */

export type TriggerType =
  | 'volume_surge'       // 거래량 급증
  | 'gap_up'             // 갭 상승
  | 'fund_inflow'        // 자금 유입
  | 'intraday_rise'      // 일중 상승
  | 'closing_strength'   // 마감 강도
  | 'sideways_volume'    // 횡보주 거래량

export type SessionType = 'morning' | 'afternoon'

export interface Trigger {
  ticker: string
  name: string
  trigger_type: TriggerType
  current_price: number
  change_rate: number
  volume: number
  trading_value: number
  composite_score: number // 0-1
  session: SessionType
  detected_at: string
}

export interface TriggerMetadata {
  date: string
  session: SessionType
  total: number
  trigger_types: Record<string, number>
}

export interface TriggerResponse {
  success: boolean
  data: {
    triggers: Trigger[]
    metadata: TriggerMetadata
  }
}

export interface TriggerStatsData {
  period: {
    start: string
    end: string
  }
  total_triggers: number
  daily_average: number
  by_type: Record<TriggerType, number>
  by_session: {
    morning: number
    afternoon: number
  }
  top_frequent_stocks: Array<{
    ticker: string
    name: string
    count: number
  }>
}

// 트리거 타입별 한글명
export const TRIGGER_TYPE_LABELS: Record<TriggerType, string> = {
  volume_surge: '거래량 급증',
  gap_up: '갭 상승',
  fund_inflow: '자금 유입',
  intraday_rise: '일중 상승',
  closing_strength: '마감 강도',
  sideways_volume: '횡보주 거래량',
}

// 세션 한글명
export const SESSION_LABELS: Record<SessionType, string> = {
  morning: '오전',
  afternoon: '오후',
}
