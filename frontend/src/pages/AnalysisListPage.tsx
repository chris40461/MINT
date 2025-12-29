// 참고: docs/frontend/02-routing.md
// 참고: docs/frontend/04-components.md

/**
 * 기업 분석 리스트 페이지
 *
 * 종목 검색, 필터링, 정렬 기능 제공
 */

import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGetStocks } from '@/hooks/api/useStocks'
import { useGetTriggers } from '@/hooks/api/useTriggers'
import { useGetMorningReport } from '@/hooks/api/useReports'
import { Card } from '@/components'
import {
  Search,
  Filter,
  TrendingUp,
  Building2,
  Loader2,
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  X,
  ArrowUpDown,
} from 'lucide-react'
import { formatMarketCap } from '@/utils/format'
import type { Stock, GetStocksRequest } from '@/types'

type FilterType = 'ALL' | 'TRIGGER' | 'REPORT'
type SortField = 'market_cap' | 'per' | 'pbr' | 'roe' | 'name'
type SortOrder = 'asc' | 'desc'

interface FilterState {
  market: string | undefined
  minPer: string
  maxPer: string
  minPbr: string
  maxPbr: string
  minRoe: string
  maxRoe: string
  minMarketCap: string
  maxMarketCap: string
}

const initialFilterState: FilterState = {
  market: undefined,
  minPer: '',
  maxPer: '',
  minPbr: '',
  maxPbr: '',
  minRoe: '',
  maxRoe: '',
  minMarketCap: '',
  maxMarketCap: '',
}

export function AnalysisListPage() {
  const navigate = useNavigate()
  const [filterType, setFilterType] = useState<FilterType>('ALL')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [isInitialLoad, setIsInitialLoad] = useState(true)
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [filters, setFilters] = useState<FilterState>(initialFilterState)
  const [sortBy, setSortBy] = useState<SortField>('market_cap')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // 오늘 날짜
  const today = new Date().toISOString().split('T')[0]

  // 급등주 트리거에서 종목 가져오기
  const { data: triggersData, isLoading: isTriggersLoading } = useGetTriggers({ date: today })

  // 오전 리포트에서 종목 가져오기
  const { data: morningReport, isLoading: isReportLoading } = useGetMorningReport(today)

  // Featured ticker 리스트 추출
  const featuredTickers = useMemo(() => {
    const tickers = new Set<string>()

    if (filterType === 'TRIGGER') {
      if (triggersData?.triggers && Array.isArray(triggersData.triggers)) {
        triggersData.triggers.forEach((trigger) => {
          if (trigger.ticker) tickers.add(trigger.ticker)
        })
      }
    } else if (filterType === 'REPORT') {
      if (morningReport?.top_stocks && Array.isArray(morningReport.top_stocks)) {
        morningReport.top_stocks.forEach((stock) => {
          if (stock.ticker) tickers.add(stock.ticker)
        })
      }
    }

    return Array.from(tickers).join(',')
  }, [filterType, triggersData, morningReport])

  // API 요청 파라미터 구성
  const apiParams = useMemo<GetStocksRequest>(() => {
    // Featured 모드 (급등주 또는 리포트)
    if (filterType !== 'ALL' && featuredTickers) {
      return {
        keyword: featuredTickers,
        limit: 100,
      }
    }

    // 일반 검색/필터링 모드
    const params: GetStocksRequest = {
      limit: 100,
      sort_by: sortBy,
      sort_order: sortOrder,
    }

    if (searchKeyword) params.keyword = searchKeyword
    if (filters.market) params.market = filters.market
    if (filters.minPer) params.min_per = parseFloat(filters.minPer)
    if (filters.maxPer) params.max_per = parseFloat(filters.maxPer)
    if (filters.minPbr) params.min_pbr = parseFloat(filters.minPbr)
    if (filters.maxPbr) params.max_pbr = parseFloat(filters.maxPbr)
    if (filters.minRoe) params.min_roe = parseFloat(filters.minRoe)
    if (filters.maxRoe) params.max_roe = parseFloat(filters.maxRoe)
    if (filters.minMarketCap) params.min_market_cap = parseFloat(filters.minMarketCap)
    if (filters.maxMarketCap) params.max_market_cap = parseFloat(filters.maxMarketCap)

    return params
  }, [filterType, featuredTickers, searchKeyword, filters, sortBy, sortOrder])

  // API 호출
  const { data, isLoading, error } = useGetStocks(apiParams, {
    enabled: filterType === 'ALL' || !!featuredTickers,
  })

  // 종목 리스트
  const stocks = useMemo(() => data?.stocks || [], [data])

  // 초기 로딩 완료 체크
  useEffect(() => {
    if (!isLoading && isInitialLoad) setIsInitialLoad(false)
  }, [isLoading, isInitialLoad])

  // 필터 변경 핸들러
  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }))
  }

  // 필터 초기화
  const resetFilters = () => {
    setFilters(initialFilterState)
    setSearchKeyword('')
  }

  // 정렬 변경
  const handleSortChange = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  // 필터 타입 변경
  const handleFilterTypeChange = (type: FilterType) => {
    setFilterType(type)
    if (type !== 'ALL') {
      resetFilters()
    }
  }

  // 활성 필터 개수
  const activeFilterCount = useMemo(() => {
    let count = 0
    if (filters.market) count++
    if (filters.minPer || filters.maxPer) count++
    if (filters.minPbr || filters.maxPbr) count++
    if (filters.minRoe || filters.maxRoe) count++
    if (filters.minMarketCap || filters.maxMarketCap) count++
    return count
  }, [filters])

  // 데이터 로딩 중
  const isDataLoading = isTriggersLoading || isReportLoading || (isLoading && isInitialLoad)

  if (isDataLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
          <p className="text-gray-600">종목 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <p className="text-red-700">
              종목 정보를 불러오는 중 오류가 발생했습니다: {(error as Error).message}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
            <Building2 className="text-emerald-600" />
            기업 분석
          </h1>
          <p className="text-gray-600">
            {filterType === 'TRIGGER'
              ? '오늘의 급등주 트리거 종목'
              : filterType === 'REPORT'
              ? '오늘의 오전 리포트 Top 종목'
              : `총 ${stocks.length}개 종목`}
          </p>
        </div>

        {/* Filter Type Tabs */}
        <div className="flex gap-2 mb-4">
          {(['ALL', 'TRIGGER', 'REPORT'] as FilterType[]).map((type) => (
            <button
              key={type}
              onClick={() => handleFilterTypeChange(type)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                filterType === type
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {type === 'ALL' ? '전체' : type === 'TRIGGER' ? '급등주' : '리포트'}
            </button>
          ))}
        </div>

        {/* Search and Filters */}
        {filterType === 'ALL' && (
          <div className="bg-white rounded-lg p-4 mb-6 space-y-4">
            {/* Search Bar */}
            <div className="flex items-center gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-600" size={20} />
                <input
                  type="text"
                  value={searchKeyword}
                  onChange={(e) => setSearchKeyword(e.target.value)}
                  placeholder="종목명 또는 코드 검색..."
                  className="w-full pl-10 pr-4 py-2.5 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                />
              </div>
              <button
                onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
                  showAdvancedFilters || activeFilterCount > 0
                    ? 'bg-emerald-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 border border-gray-200'
                }`}
              >
                <SlidersHorizontal size={18} />
                <span>필터</span>
                {activeFilterCount > 0 && (
                  <span className="bg-white text-emerald-600 text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {activeFilterCount}
                  </span>
                )}
                {showAdvancedFilters ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>
            </div>

            {/* Advanced Filters */}
            {showAdvancedFilters && (
              <div className="pt-4 border-t border-gray-200 space-y-4">
                {/* Row 1: Market & Sector */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-gray-600 text-sm mb-1">시장</label>
                    <select
                      value={filters.market || ''}
                      onChange={(e) => handleFilterChange('market', e.target.value)}
                      className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    >
                      <option value="">전체</option>
                      <option value="KOSPI">KOSPI</option>
                      <option value="KOSDAQ">KOSDAQ</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-gray-600 text-sm mb-1">시가총액 (억원)</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={filters.minMarketCap}
                        onChange={(e) => handleFilterChange('minMarketCap', e.target.value)}
                        placeholder="최소"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                      <input
                        type="number"
                        value={filters.maxMarketCap}
                        onChange={(e) => handleFilterChange('maxMarketCap', e.target.value)}
                        placeholder="최대"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                    </div>
                  </div>
                </div>

                {/* Row 2: Financial Ratios */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-gray-600 text-sm mb-1">PER</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={filters.minPer}
                        onChange={(e) => handleFilterChange('minPer', e.target.value)}
                        placeholder="최소"
                        step="0.1"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                      <input
                        type="number"
                        value={filters.maxPer}
                        onChange={(e) => handleFilterChange('maxPer', e.target.value)}
                        placeholder="최대"
                        step="0.1"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-600 text-sm mb-1">PBR</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={filters.minPbr}
                        onChange={(e) => handleFilterChange('minPbr', e.target.value)}
                        placeholder="최소"
                        step="0.1"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                      <input
                        type="number"
                        value={filters.maxPbr}
                        onChange={(e) => handleFilterChange('maxPbr', e.target.value)}
                        placeholder="최대"
                        step="0.1"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-600 text-sm mb-1">ROE (%)</label>
                    <div className="flex gap-2">
                      <input
                        type="number"
                        value={filters.minRoe}
                        onChange={(e) => handleFilterChange('minRoe', e.target.value)}
                        placeholder="최소"
                        step="1"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                      <input
                        type="number"
                        value={filters.maxRoe}
                        onChange={(e) => handleFilterChange('maxRoe', e.target.value)}
                        placeholder="최대"
                        step="1"
                        className="w-full px-3 py-2 bg-white text-gray-900 rounded-lg border border-gray-300 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      />
                    </div>
                  </div>
                </div>

                {/* Reset Button */}
                {activeFilterCount > 0 && (
                  <div className="flex justify-end">
                    <button
                      onClick={resetFilters}
                      className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
                    >
                      <X size={16} />
                      필터 초기화
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Sort Options */}
            <div className="flex items-center gap-3 pt-2 border-t border-gray-200">
              <span className="text-gray-600 text-sm flex items-center gap-1">
                <ArrowUpDown size={14} />
                정렬:
              </span>
              {[
                { field: 'market_cap' as SortField, label: '시가총액' },
                { field: 'per' as SortField, label: 'PER' },
                { field: 'pbr' as SortField, label: 'PBR' },
                { field: 'roe' as SortField, label: 'ROE' },
                { field: 'name' as SortField, label: '종목명' },
              ].map(({ field, label }) => (
                <button
                  key={field}
                  onClick={() => handleSortChange(field)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1 ${
                    sortBy === field
                      ? 'bg-emerald-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  {label}
                  {sortBy === field && (
                    <span className="text-xs">
                      {sortOrder === 'asc' ? '↑' : '↓'}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {isLoading && !isInitialLoad ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="animate-spin text-emerald-600" size={40} />
            <span className="ml-3 text-gray-600">검색 중...</span>
          </div>
        ) : stocks.length === 0 ? (
          <Card className="bg-white border-gray-200">
            <div className="p-12 text-center">
              <Search className="mx-auto mb-4 text-gray-600" size={48} />
              <p className="text-gray-600 text-lg">
                {filterType === 'TRIGGER'
                  ? '오늘의 급등주 트리거가 아직 생성되지 않았습니다.'
                  : filterType === 'REPORT'
                  ? '오늘의 오전 리포트가 아직 생성되지 않았습니다.'
                  : '조건에 맞는 종목이 없습니다.'}
              </p>
              {filterType === 'ALL' && activeFilterCount > 0 && (
                <button
                  onClick={resetFilters}
                  className="mt-4 text-emerald-600 hover:text-emerald-700 transition-colors"
                >
                  필터 초기화하기
                </button>
              )}
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stocks.map((stock: Stock) => (
              <Card
                key={stock.ticker}
                className="bg-white border-gray-200 hover:border-emerald-400 hover:shadow-lg hover:shadow-emerald-200/50 transition-all cursor-pointer group"
                onClick={() => navigate(`/analysis/${stock.ticker}`)}
              >
                <div className="p-5">
                  {/* Header */}
                  <div className="mb-3">
                    <div className="flex items-start justify-between mb-1">
                      <h3 className="text-lg font-bold text-gray-900 group-hover:text-emerald-600 transition-colors truncate flex-1 mr-2">
                        {stock.name}
                      </h3>
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-semibold flex-shrink-0 ${
                          stock.market === 'KOSPI'
                            ? 'bg-blue-100 text-blue-700 border border-blue-300'
                            : stock.market === 'KOSDAQ'
                            ? 'bg-purple-100 text-purple-700 border border-purple-300'
                            : 'bg-gray-100 text-gray-600 border border-gray-300'
                        }`}
                      >
                        {stock.market || 'N/A'}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-600 text-sm">{stock.ticker}</span>
                    </div>
                  </div>

                  {/* Divider */}
                  <div className="border-t border-gray-200 my-3"></div>

                  {/* Financial Data */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-gray-100 rounded px-2 py-1.5">
                      <span className="text-gray-500 text-xs block">시가총액</span>
                      <span className="text-gray-900 font-semibold text-sm">
                        {stock.market_cap > 0 ? formatMarketCap(stock.market_cap) : 'N/A'}
                      </span>
                    </div>
                    <div className="bg-gray-100 rounded px-2 py-1.5">
                      <span className="text-gray-500 text-xs block">PER</span>
                      <span
                        className={`font-semibold text-sm ${
                          stock.per && stock.per > 0 && stock.per < 15
                            ? 'text-emerald-600'
                            : 'text-gray-900'
                        }`}
                      >
                        {stock.per === 0 || !stock.per ? 'N/A' : stock.per.toFixed(2)}
                      </span>
                    </div>
                    <div className="bg-gray-100 rounded px-2 py-1.5">
                      <span className="text-gray-500 text-xs block">PBR</span>
                      <span
                        className={`font-semibold text-sm ${
                          stock.pbr && stock.pbr > 0 && stock.pbr < 1
                            ? 'text-emerald-600'
                            : 'text-gray-900'
                        }`}
                      >
                        {stock.pbr === 0 || !stock.pbr ? 'N/A' : stock.pbr.toFixed(2)}
                      </span>
                    </div>
                    <div className="bg-gray-100 rounded px-2 py-1.5">
                      <span className="text-gray-500 text-xs block">ROE</span>
                      <span
                        className={`font-semibold text-sm ${
                          stock.roe && stock.roe > 15 ? 'text-emerald-600' : 'text-gray-900'
                        }`}
                      >
                        {stock.roe === 0 || !stock.roe ? 'N/A' : `${stock.roe.toFixed(2)}%`}
                      </span>
                    </div>
                  </div>

                  {/* Action */}
                  <div className="mt-4 pt-3 border-t border-gray-200">
                    <div className="flex items-center justify-center text-emerald-600 text-sm font-medium group-hover:text-emerald-700 transition-colors">
                      <span>상세 분석 보기</span>
                      <TrendingUp size={16} className="ml-1" />
                    </div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
