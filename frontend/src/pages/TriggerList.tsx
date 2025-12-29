// 참고: docs/frontend/02-routing.md
// 참고: docs/frontend/04-components.md

/**
 * 급등주 트리거 목록 페이지
 *
 * 오전/오후 급등주 트리거 결과를 표시합니다.
 */

import { useState } from 'react'
import { useGetTriggers } from '@/hooks/api/useTriggers'
import { Card } from '@/components'
import { TrendingUp, Activity, Target, Filter, Calendar } from 'lucide-react'
import type { Session, TriggerType } from '@/types'

// 트리거 타입 한글 레이블
const TRIGGER_TYPE_LABELS: Record<TriggerType, string> = {
  volume_surge: '거래량 급증',
  gap_up: '갭 상승',
  fund_inflow: '자금 유입',
  intraday_rise: '일중 상승',
  closing_strength: '마감 강도',
  sideways_volume: '횡보주 거래량',
}

// 트리거 타입별 색상
const TRIGGER_TYPE_COLORS: Record<TriggerType, string> = {
  volume_surge: 'bg-blue-900 text-blue-300 border-blue-700',
  gap_up: 'bg-green-900 text-green-300 border-green-700',
  fund_inflow: 'bg-purple-900 text-purple-300 border-purple-700',
  intraday_rise: 'bg-orange-900 text-orange-300 border-orange-700',
  closing_strength: 'bg-cyan-900 text-cyan-300 border-cyan-700',
  sideways_volume: 'bg-pink-900 text-pink-300 border-pink-700',
}

export function TriggerList() {
  const [session, setSession] = useState<Session | undefined>(undefined)
  const [selectedType, setSelectedType] = useState<TriggerType | undefined>(undefined)
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0] // 오늘 날짜 (YYYY-MM-DD)
  )
  const { data, isLoading, error } = useGetTriggers({ session, date: selectedDate })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-gray-400">급등주 트리거 로딩 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900">
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-900 border border-red-700 rounded-lg p-6">
            <p className="text-red-200">
              트리거를 불러오는 중 오류가 발생했습니다: {(error as Error).message}
            </p>
          </div>
        </div>
      </div>
    )
  }

  const triggers = data?.triggers || []
  const metadata = data?.metadata || { total: 0, trigger_types: {} }

  // 필터링된 트리거 목록
  const filteredTriggers = selectedType
    ? triggers.filter((t) => t.trigger_type === selectedType)
    : triggers

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-6">급등주 트리거</h1>
        </div>

        {/* Filters */}
        <div className="grid gap-4 mb-6">
          {/* Session Filter */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-gray-400">
              <Filter size={20} />
              <span className="font-medium">세션:</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setSession(undefined)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  session === undefined
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                전체
              </button>
              <button
                onClick={() => setSession('morning')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  session === 'morning'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                오전 (09:10)
              </button>
              <button
                onClick={() => setSession('afternoon')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  session === 'afternoon'
                    ? 'bg-cyan-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                오후 (15:30)
              </button>
            </div>
          </div>

          {/* Date Filter */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-gray-400">
              <Calendar size={20} />
              <span className="font-medium">날짜 선택:</span>
            </div>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 focus:border-cyan-400 focus:outline-none"
            />
            {selectedDate !== new Date().toISOString().split('T')[0] && (
              <button
                onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors text-sm font-medium"
              >
                오늘로 돌아가기
              </button>
            )}
          </div>
        </div>

        {/* Trigger Type Filter - Only show when data exists */}
        {metadata.total > 0 && (
          <Card className="bg-gray-800 border-gray-700 mb-6">
            <div className="p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Activity className="text-cyan-400" />
                트리거 타입별 필터 (클릭하여 필터링)
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
                {/* 전체 보기 버튼 */}
                <button
                  onClick={() => setSelectedType(undefined)}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    selectedType === undefined
                      ? 'bg-cyan-600 border-cyan-500 text-white shadow-lg'
                      : 'bg-gray-900 border-gray-700 text-gray-400 hover:bg-gray-750 hover:border-gray-600'
                  }`}
                >
                  <div className="text-2xl font-bold">{metadata.total}</div>
                  <div className="text-sm mt-1">전체</div>
                </button>

                {/* 트리거 타입별 버튼 */}
                {Object.entries(metadata.trigger_types).map(([type, count]) => {
                  const triggerType = type as TriggerType
                  const colorClasses = TRIGGER_TYPE_COLORS[triggerType].split(' ')
                  const isSelected = selectedType === triggerType
                  return (
                    <button
                      key={type}
                      onClick={() => setSelectedType(prev => prev === triggerType ? undefined : triggerType)}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        isSelected
                          ? `${colorClasses[0]} border-${colorClasses[1].replace('text-', '')} ${colorClasses[1]} shadow-lg`
                          : 'bg-gray-900 border-gray-700 text-gray-400 hover:bg-gray-750 hover:border-gray-600'
                      }`}
                    >
                      <div className="text-2xl font-bold">{count}</div>
                      <div className="text-sm mt-1">
                        {TRIGGER_TYPE_LABELS[triggerType] || type}
                      </div>
                    </button>
                  )
                })}
              </div>
              {selectedType && (
                <div className="mt-4 text-center">
                  <span className="text-gray-400 text-sm">
                    현재 필터: <span className="text-cyan-400 font-semibold">{TRIGGER_TYPE_LABELS[selectedType]}</span>
                    {' • '}
                    <button
                      onClick={() => setSelectedType(undefined)}
                      className="text-cyan-400 hover:text-cyan-300 underline"
                    >
                      필터 해제
                    </button>
                  </span>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Triggers List */}
        {filteredTriggers.length === 0 ? (
          <Card className="bg-gray-800 border-gray-700">
            <div className="p-12 text-center">
              <Activity className="mx-auto mb-4 text-gray-600" size={48} />
              <h3 className="text-2xl font-bold text-white mb-2">
                {selectedType
                  ? `"${TRIGGER_TYPE_LABELS[selectedType]}" 타입의 트리거가 없습니다`
                  : '트리거 데이터 없음'}
              </h3>
              <p className="text-gray-400 mb-4">
                {selectedType
                  ? '다른 트리거 타입을 선택하거나 필터를 해제해보세요.'
                  : `선택한 날짜(${selectedDate})의 트리거 데이터를 찾을 수 없습니다.`}
              </p>
              {!selectedType && triggers.length === 0 && (
                <div className="bg-gray-900/50 rounded-lg p-4 text-left max-w-md mx-auto">
                  <p className="text-sm text-gray-400">
                    <strong className="text-cyan-400">💡 팁:</strong><br/>
                    • 트리거는 평일에만 생성됩니다 (오전 9:10, 오후 3:30)<br/>
                    • 위 날짜 선택기로 이전 평일을 선택해보세요<br/>
                    • 데이터는 스케줄러가 실행된 날짜만 확인 가능합니다
                  </p>
                </div>
              )}
            </div>
          </Card>
        ) : (
          <>
            <div className="mb-4 text-gray-400">
              총 <span className="text-cyan-400 font-semibold">{filteredTriggers.length}</span>개 종목 표시 중
            </div>
            <div key={selectedType || 'all'} className="grid gap-4">
              {filteredTriggers.map((trigger, idx) => {
            const isPositive = trigger.change_rate >= 0
            return (
              <Card
                key={`${trigger.ticker}-${trigger.detected_at}`}
                className="bg-gray-800 border-gray-700 hover:border-cyan-400 transition-colors"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-2xl font-bold text-cyan-400">#{idx + 1}</span>
                        <h3 className="text-xl font-bold text-white">{trigger.name}</h3>
                        <span className="text-gray-400 text-sm">{trigger.ticker}</span>
                      </div>
                      <div className="flex items-center gap-3 flex-wrap mb-2">
                        <span className="px-2 py-1 bg-cyan-900 text-cyan-300 rounded text-xs flex items-center gap-1">
                          <Calendar size={12} />
                          {new Date(trigger.detected_at).toLocaleDateString('ko-KR', {
                            month: '2-digit',
                            day: '2-digit',
                          })}{' '}
                          {new Date(trigger.detected_at).toLocaleTimeString('ko-KR', {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                        <span className="px-3 py-1 bg-gray-900 text-gray-300 rounded-full text-sm">
                          {trigger.session === 'morning' ? '오전' : '오후'}
                        </span>
                        <span
                          className={`px-3 py-1 rounded-full text-sm border ${
                            TRIGGER_TYPE_COLORS[trigger.trigger_type]
                          }`}
                        >
                          {TRIGGER_TYPE_LABELS[trigger.trigger_type]}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 flex-wrap">
                        <span className="text-2xl font-bold text-white">
                          {trigger.current_price.toLocaleString()}원
                        </span>
                        <span
                          className={`text-lg font-semibold ${
                            isPositive ? 'text-red-400' : 'text-blue-400'
                          }`}
                        >
                          {isPositive ? '+' : ''}
                          {trigger.change_rate.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400 mb-1">복합 점수</div>
                      <div className="text-2xl font-bold text-cyan-400">
                        {(trigger.composite_score * 100).toFixed(1)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-gray-900 rounded-lg p-4">
                    <div>
                      <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                        <Activity size={14} />
                        거래량
                      </div>
                      <div className="font-semibold text-white">
                        {(trigger.volume / 1000000).toFixed(1)}M
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                        <Target size={14} />
                        거래대금
                      </div>
                      <div className="font-semibold text-white">
                        {(trigger.trading_value / 100000000).toFixed(0)}억
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                        <TrendingUp size={14} />
                        등락률
                      </div>
                      <div
                        className={`font-semibold ${
                          isPositive ? 'text-red-400' : 'text-blue-400'
                        }`}
                      >
                        {isPositive ? '+' : ''}
                        {trigger.change_rate.toFixed(2)}%
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                        <Target size={14} />
                        현재가
                      </div>
                      <div className="font-semibold text-white">
                        {trigger.current_price.toLocaleString()}원
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
