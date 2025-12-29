/**
 * 장 시작/마감 리포트 API Hooks
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query'
import { api } from '@/services/api/client'
import type { MorningReport, AfternoonReport } from '@/types'

/**
 * 리포트 Query Key
 */
export const reportsKeys = {
  all: ['reports'] as const,
  lists: () => [...reportsKeys.all, 'list'] as const,
  list: (type: 'morning' | 'afternoon', date?: string) =>
    [...reportsKeys.lists(), type, date] as const,
}

/**
 * 장 시작 리포트 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetMorningReport()
 * const { data } = useGetMorningReport('2025-11-17')
 * ```
 */
export function useGetMorningReport(
  date?: string,
  options?: Omit<UseQueryOptions<MorningReport>, 'queryKey' | 'queryFn'>
) {
  return useQuery<MorningReport>({
    queryKey: reportsKeys.list('morning', date),
    queryFn: async () => {
      const response = await api.get<MorningReport>('/reports/morning', {
        params: date ? { date } : undefined,
      })
      return response.data
    },
    staleTime: 1000 * 60 * 30, // 30분 (리포트는 자주 바뀌지 않음)
    ...options,
  })
}

/**
 * 장 마감 리포트 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetAfternoonReport()
 * const { data } = useGetAfternoonReport('2025-11-17')
 * ```
 */
export function useGetAfternoonReport(
  date?: string,
  options?: Omit<UseQueryOptions<AfternoonReport>, 'queryKey' | 'queryFn'>
) {
  return useQuery<AfternoonReport>({
    queryKey: reportsKeys.list('afternoon', date),
    queryFn: async () => {
      const response = await api.get<AfternoonReport>('/reports/afternoon', {
        params: date ? { date } : undefined,
      })
      return response.data
    },
    staleTime: 1000 * 60 * 30, // 30분
    ...options,
  })
}

/**
 * 특정 타입의 리포트 조회 (제네릭)
 */
export function useGetReport<T extends MorningReport | AfternoonReport>(
  type: 'morning' | 'afternoon',
  date?: string,
  options?: Omit<UseQueryOptions<T>, 'queryKey' | 'queryFn'>
) {
  return useQuery<T>({
    queryKey: reportsKeys.list(type, date),
    queryFn: async () => {
      const response = await api.get<T>(`/reports/${type}`, {
        params: date ? { date } : undefined,
      })
      return response.data
    },
    staleTime: 1000 * 60 * 30,
    ...options,
  })
}
