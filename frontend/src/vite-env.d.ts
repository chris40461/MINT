/// <reference types="vite/client" />

/**
 * Vite 환경 변수 타입 정의
 */

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_API_TIMEOUT: string
  readonly VITE_QUERY_STALE_TIME: string
  readonly VITE_QUERY_GC_TIME: string
  readonly VITE_ENABLE_DEVTOOLS: string
  readonly VITE_LOG_LEVEL: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
