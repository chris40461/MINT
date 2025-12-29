/**
 * React Query Provider
 *
 * 서버 상태 관리를 위한 React Query 설정
 * - QueryClient 생성 및 전역 설정
 * - 에러 핸들링
 * - DevTools 통합 (개발 환경)
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ReactNode, useState } from 'react'
import { queryConfig, devConfig } from '@/config/api'

interface QueryProviderProps {
  children: ReactNode
}

// QueryClient 기본 설정
const createQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 데이터가 stale 상태가 되기까지의 시간
        staleTime: queryConfig.staleTime,

        // 메모리에서 캐시가 삭제되기까지의 시간
        gcTime: queryConfig.gcTime,

        // 실패 시 재시도 횟수
        retry: (failureCount, error: any) => {
          // 404, 401, 403 등은 재시도하지 않음
          if (error?.response?.status && [404, 401, 403].includes(error.response.status)) {
            return false
          }
          // 그 외의 경우 최대 1번 재시도
          return failureCount < 1
        },

        // 윈도우 포커스 시 자동 refetch 비활성화
        refetchOnWindowFocus: false,

        // 네트워크 재연결 시 자동 refetch
        refetchOnReconnect: true,
      },
      mutations: {
        // Mutation 실패 시 재시도 안 함
        retry: false,
      },
    },
  })
}

/**
 * QueryProvider 컴포넌트
 *
 * React Query의 QueryClient를 제공하고 DevTools를 통합합니다.
 */
export const QueryProvider = ({ children }: QueryProviderProps) => {
  // QueryClient는 컴포넌트 내에서 생성하여 SSR 이슈 방지
  const [queryClient] = useState(() => createQueryClient())

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {/* 개발 환경에서만 DevTools 표시 */}
      {(import.meta.env as Record<string, any>).DEV && devConfig.enableDevTools && (
        <ReactQueryDevtools
          initialIsOpen={false}
          position="bottom"
        />
      )}
    </QueryClientProvider>
  )
}

export default QueryProvider
