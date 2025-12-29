/**
 * 기업 분석 API Hooks
 */

import { useQuery, useMutation, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query'
import { api } from '@/services/api/client'
import type { CompanyAnalysis, GetAnalysisRequest } from '@/types'

/**
 * 기업 분석 Query Key
 */
export const analysisKeys = {
  all: ['analysis'] as const,
  lists: () => [...analysisKeys.all, 'list'] as const,
  list: (ticker: string, date?: string) => [...analysisKeys.lists(), ticker, date] as const,
  detail: (ticker: string) => [...analysisKeys.all, 'detail', ticker] as const,
}

/**
 * 기업 분석 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetAnalysis('005930')
 * const { data } = useGetAnalysis('005930', '2025-11-17')
 * ```
 */
export function useGetAnalysis(
  ticker: string,
  date?: string,
  options?: Omit<UseQueryOptions<CompanyAnalysis>, 'queryKey' | 'queryFn'>
) {
  return useQuery<CompanyAnalysis>({
    queryKey: analysisKeys.list(ticker, date),
    queryFn: async () => {
      const response = await api.get<CompanyAnalysis>(`/analysis/${ticker}`, {
        params: date ? { date } : undefined,
      })
      return response.data
    },
    staleTime: 1000 * 60 * 60 * 24, // 24시간 (분석은 하루 단위)
    enabled: !!ticker, // ticker가 있을 때만 실행
    ...options,
  })
}

/**
 * 기업 분석 강제 재생성 (캐시 무시)
 *
 * @example
 * ```tsx
 * const { mutate, isPending } = useRefreshAnalysis()
 * mutate({ ticker: '005930' })
 * ```
 */
export function useRefreshAnalysis(
  options?: UseMutationOptions<CompanyAnalysis, Error, GetAnalysisRequest>
) {
  return useMutation<CompanyAnalysis, Error, GetAnalysisRequest>({
    mutationFn: async (params) => {
      // LLM 분석은 최대 120초 소요될 수 있음 (뉴스 크롤링 + STS + LLM)
      const response = await api.post<CompanyAnalysis>(
        `/analysis/${params.ticker}/refresh`,
        { date: params.date },
        { timeout: 300000 } 
      )
      return response.data
    },
    ...options,
  })
}

/**
 * 캐시 상태 타입
 */
export interface CacheStatus {
  ticker: string
  cache_exists: boolean
  cache_key: string
  cached_at?: string
  expires_at?: string
  ttl_seconds?: number
  message?: string
}

/**
 * 분석 캐시 상태 확인
 *
 * @example
 * ```tsx
 * const { data: cacheStatus } = useGetCacheStatus('005930')
 * if (cacheStatus?.cache_exists && cacheStatus.ttl_seconds > 0) {
 *   // 캐시 유효
 * }
 * ```
 */
export function useGetCacheStatus(
  ticker: string,
  options?: Omit<UseQueryOptions<CacheStatus>, 'queryKey' | 'queryFn'>
) {
  return useQuery<CacheStatus>({
    queryKey: [...analysisKeys.all, 'cache-status', ticker] as const,
    queryFn: async () => {
      const response = await api.get<CacheStatus>(`/analysis/${ticker}/cache-status`)
      return response.data
    },
    staleTime: 1000 * 60 * 5, // 5분
    enabled: !!ticker,
    ...options,
  })
}
