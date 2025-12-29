/**
 * Card 컴포넌트
 *
 * 컨텐츠를 담는 카드 컨테이너
 */

import { HTMLAttributes, ReactNode, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * 패딩 설정
   * @default true
   */
  padding?: boolean
  /**
   * 호버 효과
   * @default false
   */
  hoverable?: boolean
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ children, className, padding = true, hoverable = false, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'bg-white rounded-lg shadow-md border border-gray-200',
          padding && 'p-6',
          hoverable && 'hover:shadow-lg transition-shadow cursor-pointer',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export interface CardHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode
  subtitle?: ReactNode
  action?: ReactNode
}

export const CardHeader = ({ title, subtitle, action, className, ...props }: CardHeaderProps) => {
  return (
    <div className={clsx('flex items-start justify-between mb-4', className)} {...props}>
      <div>
        {title && <h3 className="text-lg font-semibold text-gray-900">{title}</h3>}
        {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
      </div>
      {action && <div className="ml-4">{action}</div>}
    </div>
  )
}

export interface CardBodyProps extends HTMLAttributes<HTMLDivElement> {}

export const CardBody = ({ children, className, ...props }: CardBodyProps) => {
  return (
    <div className={clsx('text-gray-700', className)} {...props}>
      {children}
    </div>
  )
}

export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {}

export const CardFooter = ({ children, className, ...props }: CardFooterProps) => {
  return (
    <div className={clsx('mt-4 pt-4 border-t border-gray-200', className)} {...props}>
      {children}
    </div>
  )
}

export default Card
