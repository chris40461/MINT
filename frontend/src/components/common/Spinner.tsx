/**
 * Spinner 컴포넌트
 *
 * 로딩 상태를 표시하는 스피너
 */

import { HTMLAttributes } from 'react'
import { clsx } from 'clsx'

export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * 스피너 크기
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  /**
   * 중앙 정렬
   * @default false
   */
  center?: boolean
  /**
   * 텍스트 표시
   */
  text?: string
}

export const Spinner = ({ size = 'md', center = false, text, className, ...props }: SpinnerProps) => {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16',
  }

  const spinner = (
    <svg
      className={clsx('animate-spin text-emerald-600', sizeClasses[size])}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )

  const content = (
    <div className={clsx('flex items-center gap-3', className)} {...props}>
      {spinner}
      {text && <span className="text-gray-600">{text}</span>}
    </div>
  )

  if (center) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        {content}
      </div>
    )
  }

  return content
}

export default Spinner
