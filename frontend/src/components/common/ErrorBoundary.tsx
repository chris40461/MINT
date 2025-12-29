/**
 * ErrorBoundary 컴포넌트
 *
 * 런타임 에러를 캐치하고 Fallback UI를 표시
 */

import { Component, ErrorInfo, ReactNode } from 'react'

export interface ErrorBoundaryProps {
  children: ReactNode
  /**
   * 에러 발생 시 표시할 Fallback UI
   */
  fallback?: ReactNode
  /**
   * 에러 발생 시 표시할 Fallback 함수
   */
  fallbackRender?: (error: Error, errorInfo: ErrorInfo) => ReactNode
  /**
   * 에러 핸들러
   */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(_error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // 에러 로깅
    console.error('[ErrorBoundary] Error caught:', error, errorInfo)

    // 상태 업데이트
    this.setState({
      error,
      errorInfo,
    })

    // 커스텀 에러 핸들러 호출
    this.props.onError?.(error, errorInfo)
  }

  resetError = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // Fallback 함수가 제공된 경우
      if (this.props.fallbackRender && this.state.error && this.state.errorInfo) {
        return this.props.fallbackRender(this.state.error, this.state.errorInfo)
      }

      // Fallback UI가 제공된 경우
      if (this.props.fallback) {
        return this.props.fallback
      }

      // 기본 Fallback UI
      return (
        <div className="min-h-[400px] flex items-center justify-center px-4">
          <div className="text-center max-w-md">
            <div className="mb-4">
              <svg
                className="mx-auto h-16 w-16 text-red-500"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              문제가 발생했습니다
            </h2>

            <p className="text-gray-600 mb-6">
              페이지를 표시하는 중 오류가 발생했습니다.
            </p>

            {/* 개발 환경에서만 에러 상세 정보 표시 */}
            {import.meta.env.DEV && this.state.error && (
              <details className="text-left mb-6 p-4 bg-gray-100 rounded-lg text-sm">
                <summary className="cursor-pointer font-semibold mb-2">
                  에러 상세 정보
                </summary>
                <pre className="whitespace-pre-wrap overflow-auto text-xs">
                  {this.state.error.toString()}
                  {this.state.errorInfo && '\n\n' + this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            <button
              onClick={this.resetError}
              className="inline-flex items-center px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              다시 시도
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
