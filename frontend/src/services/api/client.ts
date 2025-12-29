// 참고: docs/frontend/03-api-integration.md

/**
 * Axios 클라이언트 설정
 *
 * - API 요청을 위한 Axios 인스턴스 생성
 * - 요청/응답 인터셉터 설정
 * - 에러 핸들링 및 로깅
 */

import axios, { AxiosError, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { apiConfig, devConfig } from '@/config/api'

/**
 * API 에러 응답 타입
 */
export interface ApiErrorResponse {
  detail?: string
  message?: string
  error?: string
  status?: number
}

/**
 * 로거 유틸리티
 */
const logger = {
  debug: (...args: any[]) => {
    if (devConfig.logLevel === 'debug') {
      console.log('[API Debug]', ...args)
    }
  },
  info: (...args: any[]) => {
    if (['debug', 'info'].includes(devConfig.logLevel)) {
      console.info('[API Info]', ...args)
    }
  },
  warn: (...args: any[]) => {
    if (['debug', 'info', 'warn'].includes(devConfig.logLevel)) {
      console.warn('[API Warning]', ...args)
    }
  },
  error: (...args: any[]) => {
    console.error('[API Error]', ...args)
  },
}

/**
 * Axios 클라이언트 인스턴스
 */
export const apiClient = axios.create({
  baseURL: apiConfig.baseURL,
  timeout: apiConfig.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 요청 인터셉터
 *
 * - 인증 토큰 추가 (필요시)
 * - 요청 로깅
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 요청 로깅
    logger.debug(`Request: ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data,
    })

    // TODO: 인증 토큰 추가 (Phase 4: 사용자 인증 구현 시)
    // const token = localStorage.getItem('access_token')
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }

    return config
  },
  (error: AxiosError) => {
    logger.error('Request Error:', error.message)
    return Promise.reject(error)
  }
)

/**
 * 응답 인터셉터
 *
 * - 응답 로깅
 * - FastAPI 표준 응답 unwrap ({success, data} -> data)
 * - 에러 핸들링
 * - 표준화된 에러 객체 반환
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    // 응답 로깅
    logger.debug(`Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      data: response.data,
    })

    // FastAPI 표준 응답 unwrap: {success: true, data: {...}} -> {...}
    if (response.data && typeof response.data === 'object' && 'success' in response.data && 'data' in response.data) {
      logger.debug('Unwrapping FastAPI response')
      response.data = response.data.data
    }

    return response
  },
  (error: AxiosError<ApiErrorResponse>) => {
    // 에러 상세 정보 추출
    const status = error.response?.status
    const url = error.config?.url
    const method = error.config?.method?.toUpperCase()

    if (error.response) {
      // 서버 응답 있음 (4xx, 5xx)
      const errorData = error.response.data
      const errorMessage =
        errorData?.detail ||
        errorData?.message ||
        errorData?.error ||
        `Server Error: ${status}`

      logger.error(`${method} ${url} - ${status}:`, errorMessage)

      // 특정 상태 코드별 처리
      switch (status) {
        case 401:
          logger.warn('Unauthorized - 인증이 필요합니다')
          // TODO: Phase 4에서 로그인 페이지로 리다이렉트
          break
        case 403:
          logger.warn('Forbidden - 권한이 없습니다')
          break
        case 404:
          logger.warn('Not Found - 리소스를 찾을 수 없습니다')
          break
        case 422:
          logger.warn('Validation Error - 입력값을 확인하세요')
          break
        case 500:
          logger.error('Internal Server Error - 서버 오류가 발생했습니다')
          break
        case 503:
          logger.error('Service Unavailable - 서버가 일시적으로 사용 불가능합니다')
          break
      }
    } else if (error.request) {
      // 요청은 보냈지만 응답 없음 (네트워크 에러)
      logger.error(`Network Error: ${method} ${url}`, error.message)
    } else {
      // 요청 설정 중 에러
      logger.error('Request Setup Error:', error.message)
    }

    return Promise.reject(error)
  }
)

/**
 * API 요청 헬퍼 함수들
 */

export const api = {
  /**
   * GET 요청
   */
  get: <T = any>(url: string, config?: AxiosRequestConfig) => {
    return apiClient.get<T>(url, config)
  },

  /**
   * POST 요청
   */
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => {
    return apiClient.post<T>(url, data, config)
  },

  /**
   * PUT 요청
   */
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => {
    return apiClient.put<T>(url, data, config)
  },

  /**
   * PATCH 요청
   */
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig) => {
    return apiClient.patch<T>(url, data, config)
  },

  /**
   * DELETE 요청
   */
  delete: <T = any>(url: string, config?: AxiosRequestConfig) => {
    return apiClient.delete<T>(url, config)
  },
}

export default apiClient
