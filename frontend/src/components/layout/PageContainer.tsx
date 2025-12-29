/**
 * PageContainer 컴포넌트
 *
 * 페이지 컨텐츠를 감싸는 컨테이너
 * - max-width 제한
 * - padding 설정
 * - 반응형 디자인
 */

import { ReactNode } from 'react'
import { clsx } from 'clsx'

export interface PageContainerProps {
  children: ReactNode
  className?: string
  /**
   * 최대 너비 설정
   * @default 'container'
   */
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'container' | 'full'
  /**
   * 패딩 설정
   * @default true
   */
  padding?: boolean
}

export const PageContainer = ({
  children,
  className,
  maxWidth = 'container',
  padding = true,
}: PageContainerProps) => {
  const maxWidthClasses = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    '2xl': 'max-w-screen-2xl',
    container: 'container',
    full: 'max-w-full',
  }

  return (
    <div
      className={clsx(
        'mx-auto',
        maxWidthClasses[maxWidth],
        padding && 'px-4 py-8',
        className
      )}
    >
      {children}
    </div>
  )
}

export default PageContainer
