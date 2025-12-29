/**
 * 타입 통합 export
 */

// Backend API 타입 (통합)
export * from './api'

// 공통 타입 (호환성 유지)
export interface PaginationParams {
  page?: number
  limit?: number
}

export interface DateRangeParams {
  start_date?: string
  end_date?: string
}
