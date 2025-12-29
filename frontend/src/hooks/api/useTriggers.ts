/**
 * 급등주 트리거 API Hooks
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query'
import { api } from '@/services/api/client'
import type { GetTriggersRequest, GetTriggersResponse } from '@/types'

/**
 * 급등주 트리거 조회 Query Key
 */
export const triggersKeys = {
  all: ['triggers'] as const,
  lists: () => [...triggersKeys.all, 'list'] as const,
  list: (params: GetTriggersRequest) => [...triggersKeys.lists(), params] as const,
}

/**
 * 급등주 트리거 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetTriggers({ session: 'morning' })
 * ```
 */
export function useGetTriggers(
  params: GetTriggersRequest = {},
  options?: Omit<UseQueryOptions<GetTriggersResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery<GetTriggersResponse>({
    queryKey: triggersKeys.list(params),
    queryFn: async () => {
      const response = await api.get<GetTriggersResponse>('/triggers/', {
        params,
      })
      return response.data
    },
    staleTime: 1000 * 60 * 5, // 5분
    ...options,
  })
}

/**
 * 특정 날짜의 오전 트리거 조회
 */
export function useGetMorningTriggers(
  date?: string,
  options?: Omit<UseQueryOptions<GetTriggersResponse>, 'queryKey' | 'queryFn'>
) {
  return useGetTriggers({ date, session: 'morning' }, options)
}

/**
 * 특정 날짜의 오후 트리거 조회
 */
export function useGetAfternoonTriggers(
  date?: string,
  options?: Omit<UseQueryOptions<GetTriggersResponse>, 'queryKey' | 'queryFn'>
) {
  return useGetTriggers({ date, session: 'afternoon' }, options)
}
