/**
 * ScrollToTop 컴포넌트
 *
 * 라우트 변경 시 스크롤을 맨 위로 이동합니다.
 */

import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

export function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}

export default ScrollToTop
