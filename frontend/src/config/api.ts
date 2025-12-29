/**
 * API 설정
 *
 * 환경 변수를 읽고 API 관련 설정을 제공합니다.
 */

/**
 * 환경 변수 읽기 헬퍼 함수
 */
const getEnv = (key: string, defaultValue?: string): string => {
  const value = (import.meta.env as Record<string, string | undefined>)[key]
  if (value === undefined && defaultValue === undefined) {
    console.warn(`[Config] Environment variable ${key} is not defined`)
  }
  return value || defaultValue || ''
}

const getEnvNumber = (key: string, defaultValue: number): number => {
  const value = getEnv(key)
  const parsed = parseInt(value, 10)
  return isNaN(parsed) ? defaultValue : parsed
}

const getEnvBoolean = (key: string, defaultValue: boolean): boolean => {
  const value = getEnv(key)
  if (value === 'true') return true
  if (value === 'false') return false
  return defaultValue
}

/**
 * API 설정
 */
export const apiConfig = {
  /**
   * API 기본 URL
   * @default 'http://localhost:8000/api/v1'
   */
  baseURL: getEnv('VITE_API_BASE_URL', 'http://localhost:8000/api/v1'),

  /**
   * API 요청 타임아웃 (ms)
   * @default 30000 (30초)
   */
  timeout: getEnvNumber('VITE_API_TIMEOUT', 30000),
}

/**
 * React Query 설정
 */
export const queryConfig = {
  /**
   * 데이터가 stale 상태가 되기까지의 시간 (ms)
   * @default 300000 (5분)
   */
  staleTime: getEnvNumber('VITE_QUERY_STALE_TIME', 1000 * 60 * 5),

  /**
   * 메모리에서 캐시가 삭제되기까지의 시간 (ms)
   * @default 1800000 (30분)
   */
  gcTime: getEnvNumber('VITE_QUERY_GC_TIME', 1000 * 60 * 30),
}

/**
 * 개발 환경 설정
 */
export const devConfig = {
  /**
   * React Query DevTools 활성화 여부
   * @default true
   */
  enableDevTools: getEnvBoolean('VITE_ENABLE_DEVTOOLS', true),

  /**
   * 로그 레벨
   * @default 'debug'
   */
  logLevel: getEnv('VITE_LOG_LEVEL', 'debug') as 'debug' | 'info' | 'warn' | 'error',
}

/**
 * 애플리케이션 정보
 */
export const appConfig = {
  /**
   * 애플리케이션 이름
   * @default 'SKKU-INSIGHT'
   */
  name: getEnv('VITE_APP_NAME', 'SKKU-INSIGHT'),

  /**
   * 애플리케이션 버전
   * @default '0.1.0'
   */
  version: getEnv('VITE_APP_VERSION', '0.1.0'),
}

/**
 * 전체 설정 객체
 */
export const config = {
  api: apiConfig,
  query: queryConfig,
  dev: devConfig,
  app: appConfig,
  isDevelopment: (import.meta.env as Record<string, any>).DEV as boolean,
  isProduction: (import.meta.env as Record<string, any>).PROD as boolean,
}

export default config
