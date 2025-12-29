/**
 * Footer 컴포넌트
 *
 * 애플리케이션 하단 푸터
 * - 저작권 정보
 * - 링크
 */

import { appConfig } from '@/config/api'
import { clsx } from 'clsx'

export interface FooterProps {
  className?: string
}

export const Footer = ({ className }: FooterProps) => {
  const currentYear = new Date().getFullYear()

  return (
    <footer className={clsx('bg-gray-50 border-t border-gray-200 mt-auto', className)}>
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          {/* 저작권 */}
          <div className="text-center md:text-left text-gray-600 text-sm">
            © {currentYear} {appConfig.name}
          </div>

          {/* 링크 */}
          <div className="flex items-center gap-4 text-sm">
            <a
              href="https://github.com/twkim96/MINT"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-emerald-600 transition-colors"
            >
              GitHub
            </a>
            <span className="text-gray-300">|</span>
            <span className="text-gray-500">v{appConfig.version}</span>
          </div>
        </div>

        {/* 면책 조항 */}
        <div className="mt-4 text-center text-xs text-gray-500">
          본 플랫폼은 투자 참고 자료일 뿐, 투자 권유가 아닙니다. 모든 투자 결정은 사용자 본인의 책임입니다.
        </div>
      </div>
    </footer>
  )
}

export default Footer
