/**
 * 종목 목록 API Hooks
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query'
import { api } from '@/services/api/client'
import type { Stock, GetStocksRequest, GetStocksResponse, FinancialData } from '@/types'

/**
 * 종목 Query Key
 */
export const stocksKeys = {
  all: ['stocks'] as const,
  lists: () => [...stocksKeys.all, 'list'] as const,
  list: (params: GetStocksRequest) => [...stocksKeys.lists(), params] as const,
  detail: (ticker: string) => [...stocksKeys.all, 'detail', ticker] as const,
  financial: (ticker: string) => [...stocksKeys.all, 'financial', ticker] as const,
}

/**
 * 종목 목록 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetStocks({ keyword: '삼성' })
 * const { data } = useGetStocks({ sort_by: 'market_cap', order: 'desc' })
 * ```
 */
export function useGetStocks(
  params: GetStocksRequest = {},
  options?: Omit<UseQueryOptions<GetStocksResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery<GetStocksResponse>({
    queryKey: stocksKeys.list(params),
    queryFn: async () => {
      const response = await api.get<GetStocksResponse>('/stocks/', {
        params,
      })
      return response.data
    },
    staleTime: 1000 * 60 * 5, // 5분
    ...options,
  })
}

/**
 * 종목 상세 정보 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetStock('005930')
 * ```
 */
export function useGetStock(
  ticker: string,
  options?: Omit<UseQueryOptions<Stock>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Stock>({
    queryKey: stocksKeys.detail(ticker),
    queryFn: async () => {
      const response = await api.get<Stock>(`/stocks/${ticker}/`)
      return response.data
    },
    staleTime: 1000 * 60 * 5, // 5분
    enabled: !!ticker,
    ...options,
  })
}

/**
 * 종목 재무 데이터 조회
 *
 * @example
 * ```tsx
 * const { data, isLoading } = useGetFinancialData('005930')
 * ```
 */
export function useGetFinancialData(
  ticker: string,
  options?: Omit<UseQueryOptions<FinancialData>, 'queryKey' | 'queryFn'>
) {
  return useQuery<FinancialData>({
    queryKey: stocksKeys.financial(ticker),
    queryFn: async () => {
      const response = await api.get<FinancialData>(`/stocks/${ticker}/financial/`)
      return response.data
    },
    staleTime: 1000 * 60 * 60 * 24, // 24시간 (재무 데이터는 하루 단위)
    enabled: !!ticker,
    ...options,
  })
}

/**
 * 여러 종목 검색 (자동완성용)
 *
 * @example
 * ```tsx
 * const { data } = useSearchStocks('삼성')
 * ```
 */
export function useSearchStocks(
  keyword: string,
  options?: Omit<UseQueryOptions<Stock[]>, 'queryKey' | 'queryFn'>
) {
  return useQuery<Stock[]>({
    queryKey: [...stocksKeys.lists(), 'search', keyword],
    queryFn: async () => {
      const response = await api.get<GetStocksResponse>('/stocks/', {
        params: { keyword, limit: 10 },
      })
      return response.data.stocks || []
    },
    staleTime: 1000 * 60 * 5, // 5분
    enabled: keyword.length >= 1, // 1글자 이상일 때만 실행
    ...options,
  })
}

// TODO: useGetSectors, useGetRelatedStocks - sector 기능 구현 후 추가 예정
