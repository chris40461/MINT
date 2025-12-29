/**
 * Badge 컴포넌트
 *
 * 상태, 태그 등을 표시하는 뱃지
 */

import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  /**
   * 뱃지 변형
   * @default 'default'
   */
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info'
  /**
   * 뱃지 크기
   * @default 'md'
   */
  size?: 'sm' | 'md' | 'lg'
  /**
   * 점 표시
   * @default false
   */
  dot?: boolean
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ children, className, variant = 'default', size = 'md', dot = false, ...props }, ref) => {
    const baseClasses = 'inline-flex items-center rounded-full font-medium'

    const variantClasses = {
      default: 'bg-gray-100 text-gray-800',
      primary: 'bg-blue-100 text-blue-800',
      success: 'bg-green-100 text-green-800',
      warning: 'bg-yellow-100 text-yellow-800',
      danger: 'bg-red-100 text-red-800',
      info: 'bg-purple-100 text-purple-800',
    }

    const sizeClasses = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-0.5 text-sm',
      lg: 'px-3 py-1 text-base',
    }

    const dotVariantClasses = {
      default: 'bg-gray-500',
      primary: 'bg-blue-500',
      success: 'bg-green-500',
      warning: 'bg-yellow-500',
      danger: 'bg-red-500',
      info: 'bg-purple-500',
    }

    return (
      <span
        ref={ref}
        className={clsx(baseClasses, variantClasses[variant], sizeClasses[size], className)}
        {...props}
      >
        {dot && (
          <span
            className={clsx('mr-1.5 h-2 w-2 rounded-full', dotVariantClasses[variant])}
            aria-hidden="true"
          />
        )}
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'

export default Badge
