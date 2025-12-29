/**
 * EmptyState 컴포넌트
 *
 * 데이터가 없을 때 표시하는 빈 상태
 */

import { HTMLAttributes, ReactNode } from 'react'
import { clsx } from 'clsx'

export interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * 아이콘 (SVG 또는 컴포넌트)
   */
  icon?: ReactNode
  /**
   * 제목
   */
  title: string
  /**
   * 설명
   */
  description?: string
  /**
   * 액션 버튼
   */
  action?: ReactNode
}

export const EmptyState = ({
  icon,
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) => {
  return (
    <div
      className={clsx('flex flex-col items-center justify-center py-12 px-4 text-center', className)}
      {...props}
    >
      {/* 아이콘 */}
      {icon && <div className="mb-4 text-gray-400">{icon}</div>}

      {/* 제목 */}
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>

      {/* 설명 */}
      {description && <p className="text-sm text-gray-600 max-w-sm mb-6">{description}</p>}

      {/* 액션 */}
      {action && <div>{action}</div>}
    </div>
  )
}

/**
 * 기본 아이콘들
 */
export const EmptyStateIcons = {
  NoData: (
    <svg
      className="h-16 w-16"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  ),
  NoResults: (
    <svg
      className="h-16 w-16"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1}
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
      />
    </svg>
  ),
  Error: (
    <svg
      className="h-16 w-16"
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
  ),
}

export default EmptyState
