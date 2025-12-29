/**
 * Header 컴포넌트
 *
 * 애플리케이션 상단 헤더
 * - 로고
 * - 네비게이션
 */

import { Link, useLocation } from 'react-router-dom'
import { appConfig } from '@/config/api'
import { clsx } from 'clsx'

export interface HeaderProps {
  className?: string
}

export const Header = ({ className }: HeaderProps) => {
  const location = useLocation()

  const navItems = [
    { path: '/', label: '홈' },
    { path: '/triggers', label: '급등주' },
    { path: '/analysis', label: '분석' },
    { path: '/reports', label: '리포트' },
  ]

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <header className={clsx('bg-white border-b border-gray-200 shadow-sm', className)}>
      <nav className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {/* 로고 */}
          <Link
            to="/"
            className="flex items-center gap-2 text-2xl font-bold text-emerald-600 hover:text-emerald-500 transition-colors"
          >
            <img src="/mint-logo.png" alt="MINT Logo" className="h-10 w-auto" />
            {appConfig.name}
          </Link>

          {/* 네비게이션 */}
          <div className="flex items-center gap-6">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'font-medium transition-colors',
                  isActive(item.path)
                    ? 'text-emerald-600'
                    : 'text-gray-600 hover:text-emerald-500'
                )}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>
    </header>
  )
}

export default Header
