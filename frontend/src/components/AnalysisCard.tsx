// 참고: docs/frontend/04-components.md

/**
 * 분석 카드 컴포넌트 (임시 비활성화 - 타입 에러)
 */

// import { Analysis, OPINION_LABELS, OPINION_COLORS } from '@/types'

interface AnalysisCardProps {
  analysis: any // Analysis
  compact?: boolean
  onClick?: () => void
}

export function AnalysisCard({ analysis, compact = false, onClick }: AnalysisCardProps) {
  const changeRateClass = analysis.change_rate >= 0 ? 'change-rate-up' : 'change-rate-down'
  const opinionColor = 'blue' // OPINION_COLORS[analysis.opinion]

  return (
    <div className="card-hover" onClick={onClick}>
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{analysis.name}</h3>
          <p className="text-sm text-gray-500">{analysis.ticker}</p>
        </div>
        <span className={`badge ${opinionColor}`}>
          {analysis.opinion}
        </span>
      </div>

      {/* 가격 정보 */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2 mb-1">
          <span className="text-2xl font-bold">
            {analysis.current_price.toLocaleString()}원
          </span>
          <span className={changeRateClass}>
            {analysis.change_rate >= 0 ? '+' : ''}
            {analysis.change_rate.toFixed(2)}%
          </span>
        </div>
        <div className="text-sm text-gray-600">
          목표가: <span className="font-semibold">{analysis.target_price.toLocaleString()}원</span>
        </div>
      </div>

      {/* 요약 */}
      <p className="text-sm text-gray-700 mb-4 line-clamp-2">{analysis.summary}</p>

      {!compact && (
        <>
          {/* 상세 지표 */}
          <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
            <div>
              <p className="text-gray-500">ROE</p>
              <p className="font-medium">{analysis.financial.roe.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-gray-500">PER</p>
              <p className="font-medium">{analysis.financial.per.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-gray-500">RSI</p>
              <p className="font-medium">{analysis.technical.rsi.toFixed(1)}</p>
            </div>
          </div>

          {/* 뉴스 센티먼트 */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-gray-500">뉴스:</span>
            <span className="text-red-600">긍정 {analysis.news.positive_count}</span>
            <span className="text-gray-500">중립 {analysis.news.neutral_count}</span>
            <span className="text-blue-600">부정 {analysis.news.negative_count}</span>
          </div>
        </>
      )}
    </div>
  )
}
