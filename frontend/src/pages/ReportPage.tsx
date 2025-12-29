// 참고: docs/frontend/02-routing.md
// 참고: docs/frontend/04-components.md

/**
 * 시장 리포트 페이지
 *
 * 장 시작/마감 AI 리포트를 표시합니다.
 */

import { useState } from 'react'
import { useGetMorningReport, useGetAfternoonReport } from '@/hooks/api/useReports'
import { Card } from '@/components'
import { TrendingUp, TrendingDown, AlertCircle, Clock, Target, Calendar, ChevronDown, ChevronUp, BarChart3 } from 'lucide-react'

type ReportType = 'morning' | 'afternoon'

export function ReportPage() {
  const [reportType, setReportType] = useState<ReportType>('morning')
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0] // 오늘 날짜 (YYYY-MM-DD)
  )
  const [expandedStocks, setExpandedStocks] = useState<Set<string>>(new Set())

  // 리포트 타입에 따라 적절한 hook 사용
  const { data: morningReport, isLoading: morningLoading, error: morningError } = useGetMorningReport(
    selectedDate,
    { enabled: reportType === 'morning' }
  )
  const { data: afternoonReport, isLoading: afternoonLoading, error: afternoonError } = useGetAfternoonReport(
    selectedDate,
    { enabled: reportType === 'afternoon' }
  )

  const report = reportType === 'morning' ? morningReport : afternoonReport
  const isLoading = reportType === 'morning' ? morningLoading : afternoonLoading
  const error = reportType === 'morning' ? morningError : afternoonError

  const toggleStock = (ticker: string) => {
    setExpandedStocks(prev => {
      const newSet = new Set(prev)
      if (newSet.has(ticker)) {
        newSet.delete(ticker)
      } else {
        newSet.add(ticker)
      }
      return newSet
    })
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-gray-400">{reportType === 'morning' ? '장 시작' : '장 마감'} 리포트 로딩 중...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header with Filters */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-6">AI 시장 리포트</h1>

          {/* Filters Row */}
          <div className="grid gap-4 mb-6">
            {/* Report Type Filter */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-gray-400">
                <BarChart3 size={20} />
                <span className="font-medium">리포트 타입:</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setReportType('morning')}
                  className={`px-6 py-2 rounded-lg transition-all font-medium ${
                    reportType === 'morning'
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  장 시작 리포트
                </button>
                <button
                  onClick={() => setReportType('afternoon')}
                  className={`px-6 py-2 rounded-lg transition-all font-medium ${
                    reportType === 'afternoon'
                      ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  장 마감 리포트
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
        </div>

        {/* Empty State */}
        {(error || !report) && (
          <Card className="bg-gray-800 border-gray-700">
            <div className="p-12 text-center">
              <BarChart3 className="mx-auto mb-4 text-gray-600" size={64} />
              <h3 className="text-2xl font-bold text-white mb-2">리포트 데이터 없음</h3>
              <p className="text-gray-400 mb-4">
                {error
                  ? `리포트를 불러오는 중 오류가 발생했습니다: ${(error as Error).message}`
                  : `선택한 날짜(${selectedDate})의 ${reportType === 'morning' ? '장 시작' : '장 마감'} 리포트를 찾을 수 없습니다.`
                }
              </p>
              <div className="bg-gray-900/50 rounded-lg p-4 text-left max-w-md mx-auto">
                <p className="text-sm text-gray-400">
                  <strong className="text-cyan-400">💡 팁:</strong><br/>
                  • 리포트는 평일에만 생성됩니다<br/>
                  • 장 시작 리포트: 오전 8시 생성<br/>
                  • 장 마감 리포트: 오후 3시 40분 생성<br/>
                  • 위 날짜 선택기로 이전 평일을 선택해보세요
                </p>
              </div>
            </div>
          </Card>
        )}

        {/* KOSPI 예상 범위 (MorningReport only) */}
        {report && reportType === 'morning' && 'kospi_range' in report && (
          <Card className="bg-gray-800 border-gray-700 mb-6">
          <div className="p-6">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
              <Target className="text-cyan-400" />
              KOSPI 예상 범위
            </h2>
            <div className="flex items-center justify-center gap-6 mb-6">
              <div className="flex-1 bg-red-900/30 border border-red-700/30 rounded-xl p-6 text-center">
                <div className="text-sm text-red-400 mb-2 font-semibold">하단 지지선</div>
                <div className="text-4xl font-bold text-red-400 mb-1">{report.kospi_range.low.toLocaleString()}</div>
                <div className="text-xs text-red-300">Support Level</div>
              </div>
              <div className="text-gray-500 text-3xl font-bold">~</div>
              <div className="flex-1 bg-green-900/30 border border-green-700/30 rounded-xl p-6 text-center">
                <div className="text-sm text-green-400 mb-2 font-semibold">상단 저항선</div>
                <div className="text-4xl font-bold text-green-400 mb-1">{report.kospi_range.high.toLocaleString()}</div>
                <div className="text-xs text-green-300">Resistance Level</div>
              </div>
            </div>
            <div className="bg-gray-900/90 rounded-lg p-4">
              <div className="text-xs text-cyan-400 font-semibold mb-2">분석 근거</div>
              <p className="text-gray-300 text-sm leading-relaxed">{report.kospi_range.reasoning}</p>
            </div>
          </div>
        </Card>
        )}

        {/* 시장 전망 & 리스크 (MorningReport only) */}
        {report && reportType === 'morning' && 'market_forecast' in report && (
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            <Card className="bg-gray-800 border-gray-700">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                  <BarChart3 className="text-cyan-400" />
                  시장 전망
                </h2>
                <div className="bg-gray-900/90 rounded-lg p-4 space-y-3">
                  {report.market_forecast
                    .split(/\.\s+/)
                    .filter((sentence: string) => sentence.trim())
                    .map((sentence: string, idx: number) => {
                      const trimmed = sentence.trim()
                      return (
                        <div key={idx} className="flex items-start gap-2">
                          <span className="text-cyan-400 mt-1">•</span>
                          <p className="text-gray-300 leading-relaxed flex-1">
                            {trimmed}{!trimmed.endsWith('.') && '.'}
                          </p>
                        </div>
                      )
                    })}
                </div>
              </div>
            </Card>

            <Card className="bg-gray-800 border-gray-700">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                  <AlertCircle className="text-orange-400" />
                  주요 리스크 요인
                </h2>
                <div className="space-y-2">
                  {report.market_risks.map((risk: string, idx: number) => (
                    <div key={idx} className="flex items-start gap-3 bg-orange-900/10 border border-orange-700/30 rounded-lg p-3">
                      <span className="text-orange-400 font-bold text-lg">•</span>
                      <span className="text-gray-300 flex-1 text-sm">{risk}</span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* 주목 종목 Top 10 (MorningReport only) */}
        {report && reportType === 'morning' && 'top_stocks' in report && (
          <div className="mb-6">
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="text-cyan-400" />
            주목 종목 Top 10
          </h2>
          <div className="grid gap-3">
            {report.top_stocks.map((stock) => {
              const isExpanded = expandedStocks.has(stock.ticker)
              // entry_strategy null 체크 추가 (LLM 에러 시 방지)
              const hasStrategy = stock.entry_strategy && stock.current_price > 0
              const gain1 = hasStrategy && stock.entry_strategy.target_price_1
                ? ((stock.entry_strategy.target_price_1 - stock.current_price) / stock.current_price * 100).toFixed(1)
                : 'N/A'
              const gain2 = hasStrategy && stock.entry_strategy.target_price_2
                ? ((stock.entry_strategy.target_price_2 - stock.current_price) / stock.current_price * 100).toFixed(1)
                : 'N/A'
              const loss = hasStrategy && stock.entry_strategy.stop_loss
                ? ((stock.entry_strategy.stop_loss - stock.current_price) / stock.current_price * 100).toFixed(1)
                : 'N/A'

              return (
                <Card
                  key={stock.ticker}
                  className="bg-gray-800 border-gray-700 hover:border-cyan-400 transition-all cursor-pointer"
                  onClick={() => toggleStock(stock.ticker)}
                >
                  <div className="p-5">
                    {/* Compact Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-2xl font-bold text-cyan-400">
                            #{stock.rank}
                          </span>
                          <h3 className="text-xl font-bold text-white">{stock.name}</h3>
                          <span className="text-gray-500 text-sm">{stock.ticker}</span>
                        </div>
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="text-2xl font-bold text-white">
                            {stock.current_price.toLocaleString()}
                            <span className="text-sm text-gray-400 ml-1">원</span>
                          </span>
                          <div className="px-3 py-1 bg-cyan-900 text-cyan-300 rounded-full text-sm font-semibold">
                            점수 {stock.score.toFixed(1)}
                          </div>
                          {stock.entry_strategy?.confidence !== undefined && (
                            <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
                              stock.entry_strategy.confidence >= 0.8
                                ? 'bg-green-900 text-green-300'
                                : stock.entry_strategy.confidence >= 0.6
                                ? 'bg-yellow-900 text-yellow-300'
                                : 'bg-red-900 text-red-300'
                            }`}>
                              신뢰도 {(stock.entry_strategy.confidence * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleStock(stock.ticker)
                        }}
                        className="text-cyan-400 hover:text-cyan-300 transition-colors p-2"
                      >
                        {isExpanded ? <ChevronUp size={24} /> : <ChevronDown size={24} />}
                      </button>
                    </div>

                    {/* Quick Stats Grid */}
                    <div className="grid grid-cols-4 gap-3 mb-3">
                      <div className="bg-gray-900/90 rounded-lg p-3 text-center">
                        <div className="text-xs text-gray-400 mb-1">진입가</div>
                        <div className="text-sm font-bold text-white">
                          {stock.entry_strategy.entry_price.toLocaleString()}
                        </div>
                      </div>
                      <div className="bg-green-900/30 rounded-lg p-3 text-center border border-green-700/30">
                        <div className="text-xs text-green-400 mb-1 flex items-center justify-center gap-1">
                          <TrendingUp size={12} />
                          1차 목표
                        </div>
                        <div className="text-sm font-bold text-green-400">
                          +{gain1}%
                        </div>
                      </div>
                      <div className="bg-green-900/30 rounded-lg p-3 text-center border border-green-700/30">
                        <div className="text-xs text-green-400 mb-1 flex items-center justify-center gap-1">
                          <TrendingUp size={12} />
                          2차 목표
                        </div>
                        <div className="text-sm font-bold text-green-400">
                          +{gain2}%
                        </div>
                      </div>
                      <div className="bg-red-900/30 rounded-lg p-3 text-center border border-red-700/30">
                        <div className="text-xs text-red-400 mb-1 flex items-center justify-center gap-1">
                          <TrendingDown size={12} />
                          손절
                        </div>
                        <div className="text-sm font-bold text-red-400">
                          {loss}%
                        </div>
                      </div>
                    </div>

                    {/* Reason Summary */}
                    <p className="text-gray-300 text-sm leading-relaxed mb-2">{stock.reason}</p>

                    {/* Expandable Strategy Details */}
                    {isExpanded && (
                      <div className="mt-4 pt-4 border-t border-gray-700 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                        <div className="flex items-center gap-2 text-cyan-400 font-bold mb-3">
                          <Target size={18} />
                          <span>상세 진입 전략</span>
                        </div>

                        {/* Analysis (Chain-of-Thought) */}
                        {stock.entry_strategy?.analysis && (
                          <div className="bg-blue-900/20 border border-blue-700/30 rounded-lg p-4">
                            <div className="text-xs text-blue-400 font-semibold mb-2">📊 진입 판단 분석</div>
                            <div className="text-sm text-gray-300 leading-relaxed">{stock.entry_strategy.analysis}</div>
                          </div>
                        )}

                        {/* Strategy Grid */}
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                          <div className="bg-gray-900/90 rounded-lg p-3">
                            <div className="text-xs text-gray-400 mb-1">진입 타이밍</div>
                            <div className="font-semibold text-white text-sm">{stock.entry_strategy.entry_timing}</div>
                          </div>
                          <div className="bg-gray-900/90 rounded-lg p-3">
                            <div className="text-xs text-gray-400 mb-1 flex items-center gap-1">
                              <Clock size={12} />
                              보유기간
                            </div>
                            <div className="font-semibold text-white text-sm">{stock.entry_strategy.holding_period}</div>
                          </div>
                          <div className="bg-gray-900/90 rounded-lg p-3">
                            <div className="text-xs text-gray-400 mb-1">손익비</div>
                            <div className="font-semibold text-cyan-400">{stock.entry_strategy.risk_reward_ratio}</div>
                          </div>
                        </div>

                        {/* Price Levels */}
                        <div className="bg-gray-900/90 rounded-lg p-4 space-y-2">
                          <div className="flex justify-between items-center">
                            <span className="text-sm text-gray-400">진입가</span>
                            <span className="font-bold text-white">{stock.entry_strategy.entry_price.toLocaleString()}원</span>
                          </div>
                          <div className="flex justify-between items-center text-green-400">
                            <span className="text-sm">1차 목표가</span>
                            <span className="font-bold">{stock.entry_strategy.target_price_1.toLocaleString()}원 ({gain1}%)</span>
                          </div>
                          <div className="flex justify-between items-center text-green-400">
                            <span className="text-sm">2차 목표가</span>
                            <span className="font-bold">{stock.entry_strategy.target_price_2.toLocaleString()}원 ({gain2}%)</span>
                          </div>
                          <div className="flex justify-between items-center text-red-400">
                            <span className="text-sm">손절가</span>
                            <span className="font-bold">{stock.entry_strategy.stop_loss.toLocaleString()}원 ({loss}%)</span>
                          </div>
                        </div>

                        {/* Strategy Details */}
                        <div className="space-y-3">
                          <div className="bg-gray-900/90 rounded-lg p-3">
                            <div className="text-xs text-cyan-400 font-semibold mb-1">기술적 근거</div>
                            <div className="text-sm text-gray-300 leading-relaxed">{stock.entry_strategy.technical_basis}</div>
                          </div>
                          <div className="bg-gray-900/90 rounded-lg p-3">
                            <div className="text-xs text-cyan-400 font-semibold mb-1">거래량 전략</div>
                            <div className="text-sm text-gray-300 leading-relaxed">{stock.entry_strategy.volume_strategy}</div>
                          </div>
                          <div className="bg-gray-900/90 rounded-lg p-3">
                            <div className="text-xs text-cyan-400 font-semibold mb-1">청산 조건</div>
                            <div className="text-sm text-gray-300 leading-relaxed">{stock.entry_strategy.exit_condition}</div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Expand/Collapse Hint */}
                    {!isExpanded && (
                      <div className="text-center mt-3 pt-3 border-t border-gray-700">
                        <span className="text-xs text-cyan-400">클릭하여 상세 전략 보기</span>
                      </div>
                    )}
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
        )}

        {/* 섹터 분석 (MorningReport only) */}
        {report && reportType === 'morning' && 'sector_analysis' in report && (
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <Card className="bg-gray-800 border-green-700/30">
            <div className="p-6">
              <h3 className="text-xl font-bold text-green-400 mb-4 flex items-center gap-2">
                <TrendingUp />
                강세 예상 업종
              </h3>
              <div className="space-y-3">
                {report.sector_analysis.bullish.map((sector, idx) => (
                  <div key={idx} className="bg-green-900/20 border-l-4 border-green-400 rounded-r-lg p-4">
                    <div className="font-bold text-white mb-2 flex items-center gap-2">
                      <span className="text-green-400">▲</span>
                      {sector.sector}
                    </div>
                    <p className="text-gray-300 text-sm leading-relaxed">{sector.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          </Card>

          <Card className="bg-gray-800 border-red-700/30">
            <div className="p-6">
              <h3 className="text-xl font-bold text-red-400 mb-4 flex items-center gap-2">
                <TrendingDown />
                약세 예상 업종
              </h3>
              <div className="space-y-3">
                {report.sector_analysis.bearish.map((sector, idx) => (
                  <div key={idx} className="bg-red-900/20 border-l-4 border-red-400 rounded-r-lg p-4">
                    <div className="font-bold text-white mb-2 flex items-center gap-2">
                      <span className="text-red-400">▼</span>
                      {sector.sector}
                    </div>
                    <p className="text-gray-300 text-sm leading-relaxed">{sector.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
        )}

        {/* 투자 전략 (MorningReport only) */}
        {report && reportType === 'morning' && 'investment_strategy' in report && (
          <Card className="bg-gray-800 border-cyan-700/30 mb-6">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                <Target className="text-cyan-400" />
                오늘의 투자 전략
              </h2>
              <div className="bg-gray-900/90 rounded-lg p-5 border-l-4 border-cyan-400 space-y-3">
                {report.investment_strategy
                  .split(/\.\s+/)
                  .filter((sentence: string) => sentence.trim())
                  .map((sentence: string, idx: number) => {
                    const trimmed = sentence.trim()
                    return (
                      <div key={idx} className="flex items-start gap-2">
                        <span className="text-cyan-400 mt-1">•</span>
                        <p className="text-gray-300 leading-relaxed flex-1">
                          {trimmed}{!trimmed.endsWith('.') && '.'}
                        </p>
                      </div>
                    )
                  })}
              </div>
            </div>
          </Card>
        )}

        {/* 시간대별 전략 (MorningReport only) */}
        {report && reportType === 'morning' && 'daily_schedule' in report && (
          <Card className="bg-gray-800 border-gray-700">
            <div className="p-6">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                <Clock className="text-cyan-400" />
                시간대별 전략
              </h2>
              <div className="grid gap-3">
                {Object.entries(report.daily_schedule).map(([timeKey, strategy]) => {
                  const timeRange = timeKey.replace(/_/g, ':')
                  return (
                    <div key={timeKey} className="bg-gray-900/90 rounded-lg p-4 border-l-4 border-cyan-400 hover:bg-gray-900 transition-colors">
                      <div className="flex items-start gap-4">
                        <div className="bg-cyan-900/30 text-cyan-400 font-mono font-bold px-3 py-1 rounded text-sm min-w-[120px] text-center">
                          {timeRange}
                        </div>
                        <p className="text-gray-300 flex-1 text-sm leading-relaxed">{strategy}</p>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </Card>
        )}

        {/* ================= AFTERNOON REPORT SECTIONS ================= */}

        {/* 시장 요약 (AfternoonReport only) */}
        {report && reportType === 'afternoon' && 'market_summary' in report && (
          <>
            {/* KOSPI / KOSDAQ 지수 카드 */}
            <div className="grid md:grid-cols-2 gap-6 mb-6">
              <Card className="bg-gray-800 border-gray-700">
                <div className="p-6">
                  <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="text-cyan-400" />
                    KOSPI
                  </h3>
                  <div className="text-center">
                    <div className="text-4xl font-bold text-white mb-2">
                      {report.market_summary.kospi_close?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className={`text-2xl font-bold ${report.market_summary.kospi_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {report.market_summary.kospi_change >= 0 ? '+' : ''}{report.market_summary.kospi_change?.toFixed(2)}%
                      <span className="text-lg ml-2">
                        ({report.market_summary.kospi_point_change >= 0 ? '+' : ''}{report.market_summary.kospi_point_change?.toFixed(2)}p)
                      </span>
                    </div>
                  </div>
                </div>
              </Card>

              <Card className="bg-gray-800 border-gray-700">
                <div className="p-6">
                  <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="text-purple-400" />
                    KOSDAQ
                  </h3>
                  <div className="text-center">
                    <div className="text-4xl font-bold text-white mb-2">
                      {report.market_summary.kosdaq_close?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className={`text-2xl font-bold ${report.market_summary.kosdaq_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {report.market_summary.kosdaq_change >= 0 ? '+' : ''}{report.market_summary.kosdaq_change?.toFixed(2)}%
                      <span className="text-lg ml-2">
                        ({report.market_summary.kosdaq_point_change >= 0 ? '+' : ''}{report.market_summary.kosdaq_point_change?.toFixed(2)}p)
                      </span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* 시장 요약 텍스트 */}
            {report.market_summary_text && (
              <Card className="bg-gray-800 border-gray-700 mb-6">
                <div className="p-6">
                  <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="text-cyan-400" />
                    시장 요약
                  </h2>
                  <div className="bg-gray-900/90 rounded-lg p-4 space-y-3">
                    {report.market_summary_text
                      .split(/\.\s+/)
                      .filter((sentence: string) => sentence.trim())
                      .map((sentence: string, idx: number) => {
                        const trimmed = sentence.trim()
                        return (
                          <div key={idx} className="flex items-start gap-2">
                            <span className="text-cyan-400 mt-1">•</span>
                            <p className="text-gray-300 leading-relaxed flex-1">
                              {trimmed}{!trimmed.endsWith('.') && '.'}
                            </p>
                          </div>
                        )
                      })}
                  </div>
                </div>
              </Card>
            )}

            {/* 시장 폭 분석 + 거래대금 */}
            <div className="grid md:grid-cols-2 gap-6 mb-6">
              {/* 시장 폭 (Market Breadth) */}
              <Card className="bg-gray-800 border-gray-700">
                <div className="p-6">
                  <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <BarChart3 className="text-cyan-400" />
                    시장 폭 (Market Breadth)
                  </h3>
                  <div className="space-y-4">
                    {/* 상승/하락/보합 바 */}
                    <div className="flex h-8 rounded-lg overflow-hidden">
                      <div
                        className="bg-green-500 flex items-center justify-center text-white text-xs font-bold"
                        style={{ width: `${(report.market_summary.advance_count / (report.market_summary.advance_count + report.market_summary.decline_count + report.market_summary.unchanged_count) * 100)}%` }}
                      >
                        {report.market_summary.advance_count > 100 && report.market_summary.advance_count}
                      </div>
                      <div
                        className="bg-gray-500 flex items-center justify-center text-white text-xs font-bold"
                        style={{ width: `${(report.market_summary.unchanged_count / (report.market_summary.advance_count + report.market_summary.decline_count + report.market_summary.unchanged_count) * 100)}%` }}
                      >
                      </div>
                      <div
                        className="bg-red-500 flex items-center justify-center text-white text-xs font-bold"
                        style={{ width: `${(report.market_summary.decline_count / (report.market_summary.advance_count + report.market_summary.decline_count + report.market_summary.unchanged_count) * 100)}%` }}
                      >
                        {report.market_summary.decline_count > 100 && report.market_summary.decline_count}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-green-900/30 rounded-lg p-3">
                        <div className="text-green-400 font-bold text-xl">{report.market_summary.advance_count}</div>
                        <div className="text-xs text-green-300">상승</div>
                      </div>
                      <div className="bg-gray-700/50 rounded-lg p-3">
                        <div className="text-gray-300 font-bold text-xl">{report.market_summary.unchanged_count}</div>
                        <div className="text-xs text-gray-400">보합</div>
                      </div>
                      <div className="bg-red-900/30 rounded-lg p-3">
                        <div className="text-red-400 font-bold text-xl">{report.market_summary.decline_count}</div>
                        <div className="text-xs text-red-300">하락</div>
                      </div>
                    </div>
                    {/* 시장 폭 해석 */}
                    {report.market_breadth && (
                      <div className="bg-gray-900/90 rounded-lg p-3 mt-3">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-1 rounded text-xs font-bold ${
                            report.market_breadth.sentiment === '강세장' ? 'bg-green-900 text-green-300' :
                            report.market_breadth.sentiment === '약세장' ? 'bg-red-900 text-red-300' :
                            'bg-yellow-900 text-yellow-300'
                          }`}>
                            {report.market_breadth.sentiment}
                          </span>
                        </div>
                        <p className="text-gray-300 text-sm">{report.market_breadth.interpretation}</p>
                      </div>
                    )}
                  </div>
                </div>
              </Card>

              {/* 거래대금 */}
              <Card className="bg-gray-800 border-gray-700">
                <div className="p-6">
                  <h3 className="text-xl font-bold text-white mb-4">거래대금</h3>
                  <div className="text-center mb-4">
                    <div className="text-4xl font-bold text-cyan-400">
                      {(report.market_summary.trading_value / 10000).toFixed(1)}
                      <span className="text-lg text-gray-400 ml-1">조원</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* 수급 동향 */}
            <Card className="bg-gray-800 border-gray-700 mb-6">
              <div className="p-6">
                <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                  <TrendingUp className="text-cyan-400" />
                  수급 동향
                </h2>
                <div className="grid md:grid-cols-2 gap-6">
                  {/* KOSPI 수급 */}
                  <div className="bg-gray-900/50 rounded-lg p-4">
                    <h4 className="text-lg font-bold text-cyan-400 mb-3">KOSPI</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">외국인</span>
                        <span className={`font-bold ${report.market_summary.foreign_net_kospi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.market_summary.foreign_net_kospi >= 0 ? '+' : ''}{report.market_summary.foreign_net_kospi?.toLocaleString()}억
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">기관</span>
                        <span className={`font-bold ${report.market_summary.institution_net_kospi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.market_summary.institution_net_kospi >= 0 ? '+' : ''}{report.market_summary.institution_net_kospi?.toLocaleString()}억
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">개인</span>
                        <span className={`font-bold ${report.market_summary.individual_net_kospi >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.market_summary.individual_net_kospi >= 0 ? '+' : ''}{report.market_summary.individual_net_kospi?.toLocaleString()}억
                        </span>
                      </div>
                    </div>
                  </div>
                  {/* KOSDAQ 수급 */}
                  <div className="bg-gray-900/50 rounded-lg p-4">
                    <h4 className="text-lg font-bold text-purple-400 mb-3">KOSDAQ</h4>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">외국인</span>
                        <span className={`font-bold ${report.market_summary.foreign_net_kosdaq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.market_summary.foreign_net_kosdaq >= 0 ? '+' : ''}{report.market_summary.foreign_net_kosdaq?.toLocaleString()}억
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">기관</span>
                        <span className={`font-bold ${report.market_summary.institution_net_kosdaq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.market_summary.institution_net_kosdaq >= 0 ? '+' : ''}{report.market_summary.institution_net_kosdaq?.toLocaleString()}억
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-400">개인</span>
                        <span className={`font-bold ${report.market_summary.individual_net_kosdaq >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {report.market_summary.individual_net_kosdaq >= 0 ? '+' : ''}{report.market_summary.individual_net_kosdaq?.toLocaleString()}억
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                {/* 수급 해석 */}
                {report.supply_demand_analysis && (
                  <div className="bg-gray-900/90 rounded-lg p-4 mt-4 border-l-4 border-cyan-400">
                    <p className="text-gray-300 leading-relaxed">{report.supply_demand_analysis}</p>
                  </div>
                )}
              </div>
            </Card>

            {/* 업종별 분석 (AfternoonReport) */}
            {report.sector_analysis && (
              <div className="grid md:grid-cols-2 gap-6 mb-6">
                <Card className="bg-gray-800 border-green-700/30">
                  <div className="p-6">
                    <h3 className="text-xl font-bold text-green-400 mb-4 flex items-center gap-2">
                      <TrendingUp />
                      강세 업종
                    </h3>
                    <div className="space-y-3">
                      {report.sector_analysis.bullish?.map((sector, idx) => (
                        <div key={idx} className="bg-green-900/20 border-l-4 border-green-400 rounded-r-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-bold text-white flex items-center gap-2">
                              <span className="text-green-400">▲</span>
                              {sector.sector}
                            </span>
                            <span className="text-green-400 font-bold">{sector.change}</span>
                          </div>
                          <p className="text-gray-300 text-sm leading-relaxed">{sector.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>

                <Card className="bg-gray-800 border-red-700/30">
                  <div className="p-6">
                    <h3 className="text-xl font-bold text-red-400 mb-4 flex items-center gap-2">
                      <TrendingDown />
                      약세 업종
                    </h3>
                    <div className="space-y-3">
                      {report.sector_analysis.bearish?.map((sector, idx) => (
                        <div key={idx} className="bg-red-900/20 border-l-4 border-red-400 rounded-r-lg p-4">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-bold text-white flex items-center gap-2">
                              <span className="text-red-400">▼</span>
                              {sector.sector}
                            </span>
                            <span className="text-red-400 font-bold">{sector.change}</span>
                          </div>
                          <p className="text-gray-300 text-sm leading-relaxed">{sector.reason}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* 오늘의 테마 */}
            {report.today_themes && report.today_themes.length > 0 && (
              <Card className="bg-gray-800 border-gray-700 mb-6">
                <div className="p-6">
                  <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    <TrendingUp className="text-yellow-400" />
                    오늘의 주도 테마
                  </h2>
                  <div className="grid gap-4">
                    {report.today_themes.map((theme, idx) => (
                      <div key={idx} className="bg-gray-900/90 rounded-lg p-4 border-l-4 border-yellow-400">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-yellow-400 font-bold text-lg">{theme.theme}</span>
                        </div>
                        <p className="text-gray-300 text-sm mb-3">{theme.drivers}</p>
                        {theme.leading_stocks && theme.leading_stocks.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            <span className="text-xs text-gray-400">대장주:</span>
                            {theme.leading_stocks.map((stock, stockIdx) => (
                              <span key={stockIdx} className="px-2 py-1 bg-yellow-900/30 text-yellow-300 rounded text-xs font-medium">
                                {stock}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* 급등주 분석 */}
            {report.surge_analysis && report.surge_analysis.length > 0 && (
              <Card className="bg-gray-800 border-gray-700 mb-6">
                <div className="p-6">
                  <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    <TrendingUp className="text-green-400" />
                    급등주 분석
                  </h2>
                  <div className="grid gap-4">
                    {report.surge_analysis.map((stock, idx) => (
                      <div key={idx} className="bg-gray-900/90 rounded-lg p-4 hover:bg-gray-900 transition-colors">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h4 className="text-lg font-bold text-white">
                              {stock.name}
                              <span className="text-sm text-gray-500 ml-2">{stock.ticker}</span>
                            </h4>
                            {stock.change_rate && (
                              <span className={`text-sm font-bold ${stock.change_rate >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {stock.change_rate >= 0 ? '+' : ''}{stock.change_rate.toFixed(2)}%
                              </span>
                            )}
                          </div>
                          <span className="px-3 py-1 bg-cyan-900/30 text-cyan-300 rounded-full text-xs font-medium">
                            {stock.category}
                          </span>
                        </div>
                        <div className="space-y-2">
                          <div>
                            <span className="text-xs text-cyan-400 font-semibold">급등 사유</span>
                            <p className="text-gray-300 text-sm">{stock.reason}</p>
                          </div>
                          <div>
                            <span className="text-xs text-cyan-400 font-semibold">향후 전망</span>
                            <p className="text-gray-300 text-sm">{stock.outlook}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}

            {/* 내일 전략 */}
            {report.tomorrow_strategy && (
              <Card className="bg-gray-800 border-cyan-700/30 mb-6">
                <div className="p-6">
                  <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    <Target className="text-cyan-400" />
                    내일 투자 전략
                  </h2>
                  <div className="bg-gray-900/90 rounded-lg p-5 border-l-4 border-cyan-400 space-y-3">
                    {report.tomorrow_strategy
                      .split(/\.\s+/)
                      .filter((sentence: string) => sentence.trim())
                      .map((sentence: string, idx: number) => {
                        const trimmed = sentence.trim()
                        return (
                          <div key={idx} className="flex items-start gap-2">
                            <span className="text-cyan-400 mt-1">•</span>
                            <p className="text-gray-300 leading-relaxed flex-1">
                              {trimmed}{!trimmed.endsWith('.') && '.'}
                            </p>
                          </div>
                        )
                      })}
                  </div>
                </div>
              </Card>
            )}

            {/* 내일 확인 사항 (체크 포인트) */}
            {report.check_points && report.check_points.length > 0 && (
              <Card className="bg-gray-800 border-orange-700/30 mb-6">
                <div className="p-6">
                  <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
                    <AlertCircle className="text-orange-400" />
                    내일 확인 사항
                  </h2>
                  <div className="space-y-2">
                    {report.check_points.map((point: string, idx: number) => (
                      <div key={idx} className="flex items-start gap-3 bg-orange-900/10 border border-orange-700/30 rounded-lg p-3">
                        <span className="text-orange-400 font-bold text-lg">{idx + 1}.</span>
                        <span className="text-gray-300 flex-1 text-sm">{point}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  )
}
