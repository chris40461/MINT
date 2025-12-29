// 참고: docs/frontend/04-components.md

/**
 * 트리거 카드 컴포넌트 (임시 비활성화 - 타입 에러)
 */

// import { Trigger, TRIGGER_TYPE_LABELS } from '@/types'
// import { format } from 'date-fns'

interface TriggerCardProps {
  trigger: any // Trigger
  onClick?: () => void
}

export function TriggerCard({ trigger, onClick }: TriggerCardProps) {
  const changeRateClass = trigger.change_rate >= 0 ? 'change-rate-up' : 'change-rate-down'

  return (
    <div className="card-hover" onClick={onClick}>
      {/* 헤더 */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{trigger.name}</h3>
          <p className="text-sm text-gray-500">{trigger.ticker}</p>
        </div>
        <span className="badge badge-neutral">
          {trigger.trigger_type}
        </span>
      </div>

      {/* 가격 정보 */}
      <div className="mb-4">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold">
            {trigger.current_price.toLocaleString()}원
          </span>
          <span className={changeRateClass}>
            {trigger.change_rate >= 0 ? '+' : ''}
            {trigger.change_rate.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* 상세 정보 */}
      <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
        <div>
          <p className="text-gray-500">거래량</p>
          <p className="font-medium">
            {(trigger.volume / 1_000_000).toFixed(1)}M
          </p>
        </div>
        <div>
          <p className="text-gray-500">거래대금</p>
          <p className="font-medium">
            {(trigger.trading_value / 100_000_000).toFixed(0)}억
          </p>
        </div>
        <div>
          <p className="text-gray-500">점수</p>
          <p className="font-medium text-blue-600">
            {(trigger.composite_score * 100).toFixed(0)}
          </p>
        </div>
      </div>

      {/* 감지 시간 */}
      <div className="text-xs text-gray-500">
        {new Date(trigger.detected_at).toLocaleTimeString()} 감지
      </div>
    </div>
  )
}
