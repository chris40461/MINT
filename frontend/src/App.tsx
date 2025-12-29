// 참고: docs/frontend/02-routing.md
// 참고: docs/architecture/01-system-overview.md

/**
 * SKKU-INSIGHT 루트 컴포넌트
 *
 * React Router 6를 사용한 라우팅 설정
 * Phase 1: Layout 컴포넌트 적용 완료
 */

import { Routes, Route, Navigate } from 'react-router-dom'
import { Header, Footer, ErrorBoundary } from '@/components'
import { Dashboard, ReportPage, TriggerList, AnalysisListPage, AnalysisDetailPage } from '@/pages'

function App() {
  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <Header />

      {/* Main Content */}
      <main className="flex-1">
        <ErrorBoundary>
          <Routes>
            {/* 홈 - 대시보드 (PageContainer 없음 - Dashboard에서 자체 레이아웃) */}
            <Route path="/" element={<Dashboard />} />

            {/* 급등주 트리거 */}
            <Route path="/triggers" element={<TriggerList />} />

            {/* 기업 분석 */}
            <Route path="/analysis" element={<AnalysisListPage />} />
            <Route path="/analysis/:ticker" element={<AnalysisDetailPage />} />

            {/* 장 시작/마감 리포트 */}
            <Route path="/reports" element={<ReportPage />} />
            <Route path="/reports/:type" element={<ReportPage />} />

            {/* 404 - 메인으로 리다이렉트 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ErrorBoundary>
      </main>

      {/* Footer */}
      <Footer />
    </div>
  )
}

export default App
