// 참고: docs/frontend/02-routing.md
// 참고: docs/frontend/04-components.md

/**
 * 기업 분석 상세 페이지
 *
 * 종목의 재무 지표 및 AI 분석 결과를 표시합니다.
 * - 기본 정보: 시가총액, PER, PBR, ROE
 * - 재무 지표: EPS, BPS, 부채비율, 매출 성장률, 배당
 * - AI 분석: 투자의견, 목표가, 재무/기술적/뉴스/산업 분석, 리스크, 투자 전략
 */

import { useParams, useNavigate } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { useGetStock } from '@/hooks/api/useStocks'
import { useRefreshAnalysis, useGetCacheStatus, analysisKeys } from '@/hooks/api/useAnalysis'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/services/api/client'
import { Card } from '@/components'
import type { CompanyAnalysis } from '@/types'
import { ArrowLeft, TrendingUp, Building2, BarChart3, AlertCircle, Info, Target, Shield, Newspaper, Activity, RefreshCw, Sparkles, Clock, Zap } from 'lucide-react'
import { formatMarketCap } from '@/utils/format'
import type { InvestmentOpinion } from '@/types'

/**
 * 분석 상태 타입
 */
type AnalysisViewState = 'initial' | 'loading' | 'loaded' | 'error'

/**
 * 분석 생성 타입
 */
type GenerationType = 'cached' | 'new' | 'refresh'

/**
 * 정보 툴팁 컴포넌트
 */
interface InfoTooltipProps {
  label: string
  description: string
}

function InfoTooltip({ label, description }: InfoTooltipProps) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div className="relative inline-flex items-center gap-1.5">
      <span>{label}</span>
      <div
        className="relative"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <Info size={14} className="text-emerald-600 cursor-help" />
        {isHovered && (
          <div className="absolute left-0 top-6 z-50 w-64 p-3 bg-white border border-gray-200 rounded-lg shadow-lg">
            <p className="text-xs text-gray-700 leading-relaxed">{description}</p>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * 투자 의견 뱃지 색상 및 텍스트
 */
function getOpinionStyle(opinion: InvestmentOpinion) {
  switch (opinion) {
    case 'strong_buy':
      return { bg: 'bg-red-100', text: 'text-red-700', label: '강력 매수' }
    case 'buy':
      return { bg: 'bg-orange-100', text: 'text-orange-700', label: '매수' }
    case 'hold':
      return { bg: 'bg-yellow-100', text: 'text-yellow-700', label: '보유' }
    case 'sell':
      return { bg: 'bg-blue-100', text: 'text-blue-700', label: '매도' }
    case 'strong_sell':
      return { bg: 'bg-purple-100', text: 'text-purple-700', label: '강력 매도' }
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-600', label: '분석 중' }
  }
}

/**
 * 센티먼트 스타일
 */
function getSentimentStyle(sentiment: 'positive' | 'neutral' | 'negative') {
  switch (sentiment) {
    case 'positive':
      return { bg: 'bg-green-100', text: 'text-green-700', label: '긍정적' }
    case 'negative':
      return { bg: 'bg-red-100', text: 'text-red-700', label: '부정적' }
    default:
      return { bg: 'bg-gray-100', text: 'text-gray-600', label: '중립' }
  }
}

export function AnalysisDetailPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // 분석 보기 상태 관리
  const [viewState, setViewState] = useState<AnalysisViewState>('initial')
  const [generationType, setGenerationType] = useState<GenerationType | null>(null)
  const [statusMessage, setStatusMessage] = useState<string>('')

  // 종목 기본 정보
  const { data: stock, isLoading: isStockLoading, error: stockError } = useGetStock(ticker || '')

  // 캐시 상태 조회 (페이지 로드 시 자동)
  const { data: cacheStatus } = useGetCacheStatus(ticker || '')

  // 로컬에서 분석 데이터 상태 관리 (직접 API 호출 사용)
  const [localAnalysis, setLocalAnalysis] = useState<CompanyAnalysis | null>(null)
  const [isAnalysisLoading, setIsAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState<Error | null>(null)

  // 분석 강제 재생성 mutation
  const { mutate: refreshAnalysis, isPending: isRefreshing } = useRefreshAnalysis({
    onSuccess: (data) => {
      console.log('[DEBUG] refreshAnalysis success:', data)
      // 성공 시 캐시 무효화 및 상태 업데이트
      queryClient.invalidateQueries({ queryKey: analysisKeys.list(ticker || '') })
      queryClient.setQueryData(analysisKeys.list(ticker || '', undefined), data)
      setLocalAnalysis(data)
      setViewState('loaded')
    },
    onError: (err) => {
      console.error('[DEBUG] refreshAnalysis error:', err)
      setViewState('error')
      setStatusMessage('분석 생성에 실패했습니다. 다시 시도해주세요.')
    }
  })

  // AI 분석 보기 버튼 클릭 핸들러
  const handleViewAnalysis = useCallback(async () => {
    if (!ticker) return

    setViewState('loading')
    setAnalysisError(null)

    // 캐시 상태에 따라 분기
    if (cacheStatus?.cache_exists && cacheStatus.ttl_seconds && cacheStatus.ttl_seconds > 0) {
      // 캐시 유효 → 직접 API 호출로 조회
      setGenerationType('cached')
      setStatusMessage('저장된 분석 결과를 불러오는 중...')
      setIsAnalysisLoading(true)
      try {
        // 직접 API 호출 (refetch 대신)
        const response = await api.get<CompanyAnalysis>(`/analysis/${ticker}`)
        console.log('[DEBUG] API response:', response)
        const data = response.data
        console.log('[DEBUG] API data:', data)

        if (data) {
          // 로컬 상태에 데이터 저장
          setLocalAnalysis(data)
          queryClient.setQueryData(analysisKeys.list(ticker, undefined), data)
          setViewState('loaded')
        } else {
          // 캐시가 있다고 했는데 데이터가 없으면 새로 생성
          console.log('[DEBUG] No data in response, generating new analysis')
          setGenerationType('new')
          setStatusMessage('AI가 종목을 분석하고 있습니다... ')
          refreshAnalysis({ ticker })
        }
      } catch (err) {
        console.error('[DEBUG] API call error:', err)
        setAnalysisError(err as Error)
        setViewState('error')
        setStatusMessage('분석 결과를 불러오는데 실패했습니다.')
      } finally {
        setIsAnalysisLoading(false)
      }
    } else if (!cacheStatus?.cache_exists) {
      // 캐시 없음 → 새로 생성
      setGenerationType('new')
      setStatusMessage('AI가 종목을 분석하고 있습니다...')
      refreshAnalysis({ ticker })
    } else {
      // 캐시 만료 또는 급등/급락 등으로 재생성 필요
      setGenerationType('refresh')
      setStatusMessage('최신 데이터로 분석을 재생성하고 있습니다...')
      refreshAnalysis({ ticker })
    }
  }, [ticker, cacheStatus, refreshAnalysis, queryClient])

  const isLoading = isStockLoading
  const error = stockError
  const isGenerating = isRefreshing || isAnalysisLoading

  // 로컬 상태에서 분석 데이터 사용
  const displayAnalysis = localAnalysis
  console.log('[DEBUG] displayAnalysis:', displayAnalysis)

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
          <p className="text-gray-600">종목 정보를 불러오는 중...</p>
        </div>
      </div>
    )
  }

  if (error || !stock) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-8">
          <button
            onClick={() => navigate('/analysis')}
            className="flex items-center gap-2 text-emerald-600 hover:text-emerald-700 mb-6 transition-colors"
          >
            <ArrowLeft size={20} />
            <span>목록으로 돌아가기</span>
          </button>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <p className="text-red-700">
              종목 정보를 불러오는 중 오류가 발생했습니다: {(error as Error)?.message || '종목을 찾을 수 없습니다'}
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* Back Button */}
        <button
          onClick={() => navigate('/analysis')}
          className="flex items-center gap-2 text-emerald-600 hover:text-emerald-300 mb-6 transition-colors"
        >
          <ArrowLeft size={20} />
          <span>목록으로 돌아가기</span>
        </button>

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Building2 className="text-emerald-600" size={40} />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">{stock.name}</h1>
              <div className="flex items-center gap-3 mt-2 flex-wrap">
                <span className="text-gray-600 text-lg">{stock.ticker}</span>
                <span className={`px-3 py-1 rounded text-sm font-semibold ${
                  stock.market === 'KOSPI'
                    ? 'bg-blue-100 text-blue-700 border border-blue-300'
                    : stock.market === 'KOSDAQ'
                    ? 'bg-purple-100 text-purple-700 border border-purple-300'
                    : 'bg-gray-100 text-gray-600 border border-gray-300'
                }`}>
                  {stock.market || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Stock Info Card */}
        <Card className="bg-white border-gray-200 mb-6">
          <div className="p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="text-emerald-600" />
              기본 정보
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {stock.market_cap > 0 && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="시가총액"
                      description="회사의 전체 주식 가치입니다. 현재 주가에 발행주식수를 곱한 값으로, 회사의 시장 규모를 나타냅니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {formatMarketCap(stock.market_cap)}
                  </div>
                </div>
              )}
              {stock.per !== undefined && stock.per !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="PER"
                      description="주가수익비율로, 주가를 주당순이익(EPS)으로 나눈 값입니다. 낮을수록 저평가 상태를 의미하며, 동종 업계와 비교하여 판단합니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.per === 0 ? 'N/A' : stock.per.toFixed(2)}
                  </div>
                </div>
              )}
              {stock.pbr !== undefined && stock.pbr !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="PBR"
                      description="주가순자산비율로, 주가를 주당순자산(BPS)으로 나눈 값입니다. 1 미만이면 주가가 순자산보다 낮아 저평가 상태로 볼 수 있습니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.pbr === 0 ? 'N/A' : stock.pbr.toFixed(2)}
                  </div>
                </div>
              )}
              {stock.roe !== undefined && stock.roe !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="ROE"
                      description="자기자본이익률로, 기업이 자기자본으로 얼마나 효율적으로 이익을 내는지 측정합니다. 높을수록 수익성이 좋으며, 일반적으로 10% 이상이면 우수합니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.roe === 0 ? 'N/A' : `${stock.roe.toFixed(2)}%`}
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>

        {/* Financial Metrics Card */}
        <Card className="bg-white border-gray-200 mb-6">
          <div className="p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp className="text-emerald-600" />
              재무 지표
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {stock.eps !== undefined && stock.eps !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="EPS (주당순이익)"
                      description="1주당 벌어들인 순이익입니다. 기업의 수익성을 나타내는 핵심 지표로, 높을수록 주주에게 더 많은 이익을 제공합니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.eps === 0 ? 'N/A' : `${stock.eps.toLocaleString()}원`}
                  </div>
                </div>
              )}
              {stock.bps !== undefined && stock.bps !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="BPS (주당순자산)"
                      description="1주당 순자산 가치입니다. 회사가 청산될 경우 주주에게 돌아갈 수 있는 1주당 금액을 나타냅니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.bps === 0 ? 'N/A' : `${stock.bps.toLocaleString()}원`}
                  </div>
                </div>
              )}
              {stock.debt_ratio !== undefined && stock.debt_ratio !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="부채비율"
                      description="자기자본 대비 부채의 비율입니다. 100% 이하면 안정적이며, 높을수록 재무 위험이 크다는 의미입니다."
                    />
                  </div>
                  <div className={`text-xl font-bold ${
                    stock.debt_ratio === 0 ? 'text-gray-900' : stock.debt_ratio > 100 ? 'text-orange-400' : 'text-green-400'
                  }`}>
                    {stock.debt_ratio === 0 ? 'N/A' : `${stock.debt_ratio.toFixed(2)}%`}
                  </div>
                </div>
              )}
              {stock.revenue_growth_yoy !== undefined && stock.revenue_growth_yoy !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="매출 성장률 (YoY)"
                      description="전년 동기 대비 매출 증가율입니다. 기업의 성장성을 나타내며, 양수일수록 사업이 확장되고 있음을 의미합니다."
                    />
                  </div>
                  <div className={`text-xl font-bold ${
                    stock.revenue_growth_yoy === 0 ? 'text-gray-900' : stock.revenue_growth_yoy > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {stock.revenue_growth_yoy === 0 ? 'N/A' : `${stock.revenue_growth_yoy >= 0 ? '+' : ''}${stock.revenue_growth_yoy.toFixed(2)}%`}
                  </div>
                </div>
              )}
              {stock.div !== undefined && stock.div !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="배당수익률"
                      description="주가 대비 배당금 비율입니다. 주식을 보유하면 얻을 수 있는 배당 수익률을 의미하며, 높을수록 배당 투자에 유리합니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.div === 0 ? 'N/A' : `${stock.div.toFixed(2)}%`}
                  </div>
                </div>
              )}
              {stock.dps !== undefined && stock.dps !== null && (
                <div className="bg-gray-50/90 rounded-lg p-4">
                  <div className="text-sm text-gray-600 mb-1">
                    <InfoTooltip
                      label="주당배당금"
                      description="1주당 지급되는 배당금입니다. 주주에게 현금으로 돌려주는 금액으로, 기업의 주주 친화성을 나타냅니다."
                    />
                  </div>
                  <div className="text-xl font-bold text-gray-900">
                    {stock.dps === 0 ? 'N/A' : `${stock.dps.toLocaleString()}원`}
                  </div>
                </div>
              )}
            </div>
            {stock.updated_at && (
              <div className="mt-4 text-xs text-gray-500 text-right">
                데이터 업데이트: {new Date(stock.updated_at).toLocaleDateString('ko-KR')}
              </div>
            )}
          </div>
        </Card>

        {/* TODO: Related Companies - sector 기능 구현 후 추가 예정 */}

        {/* AI 분석 결과 */}
        {viewState === 'initial' ? (
          <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200 mb-6">
            <div className="p-12 text-center">
              <div className="flex justify-center gap-4 mb-6">
                <div className="p-4 bg-emerald-100 rounded-full">
                  <Sparkles className="text-emerald-600" size={40} />
                </div>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">AI 종합 분석</h2>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                재무제표, 기술적 지표, 뉴스 센티먼트를 종합 분석하여<br/>
                투자의견과 목표가를 제시합니다.
              </p>

              {/* 캐시 상태에 따른 안내 메시지 */}
              {cacheStatus && (
                <div className="mb-6">
                  {cacheStatus.cache_exists && cacheStatus.ttl_seconds && cacheStatus.ttl_seconds > 0 ? (
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-green-100 border border-green-300 rounded-lg">
                      <Clock className="text-green-700" size={16} />
                      <span className="text-green-700 text-sm">
                        저장된 분석 결과 있음 (즉시 조회 가능)
                      </span>
                    </div>
                  ) : cacheStatus.cache_exists ? (
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-100 border border-yellow-300 rounded-lg">
                      <Zap className="text-yellow-700" size={16} />
                      <span className="text-yellow-700 text-sm">
                        최신 데이터로 재분석이 필요합니다
                      </span>
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100 border border-blue-300 rounded-lg">
                      <Sparkles className="text-blue-700" size={16} />
                      <span className="text-blue-700 text-sm">
                        새로운 분석을 생성합니다
                      </span>
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={handleViewAnalysis}
                className="px-8 py-4 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white rounded-xl font-bold text-lg transition-all transform hover:scale-105 shadow-lg shadow-emerald-300/50 flex items-center gap-3 mx-auto"
              >
                <Sparkles size={22} />
                AI 상세 분석 보기
              </button>
            </div>
          </Card>
        ) : viewState === 'loading' || isGenerating ? (
          <Card className="bg-white border-gray-200 mb-6">
            <div className="p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-400 mx-auto mb-4"></div>
              <p className="text-gray-700 text-lg mb-2">{statusMessage}</p>
              {generationType === 'new' && (
                <p className="text-gray-500 text-sm">
                  LLM이 재무/기술적/뉴스 데이터를 분석하고 있습니다
                </p>
              )}
              {generationType === 'refresh' && (
                <p className="text-gray-500 text-sm">
                  급등/급락 또는 캐시 만료로 인해 최신 분석을 생성합니다
                </p>
              )}
              {generationType === 'cached' && (
                <p className="text-gray-500 text-sm">
                  저장된 분석 결과를 불러오고 있습니다
                </p>
              )}
            </div>
          </Card>
        ) : viewState === 'error' || analysisError || !displayAnalysis || !displayAnalysis.summary || !displayAnalysis.financial_analysis || !displayAnalysis.technical_analysis || !displayAnalysis.news_analysis || !displayAnalysis.industry_analysis || !displayAnalysis.investment_strategy || !displayAnalysis.risk_factors ? (
          <Card className="bg-white border-gray-200 mb-6">
            <div className="p-12 text-center">
              <div className="flex justify-center gap-4 mb-6">
                <AlertCircle className="text-red-400" size={48} />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">분석 생성 실패</h2>
              <p className="text-gray-600 text-lg mb-6">
                {statusMessage || '분석 생성 중 오류가 발생했습니다.'}
              </p>
              <button
                onClick={handleViewAnalysis}
                disabled={isGenerating}
                className="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-400 text-white rounded-lg font-semibold transition-colors flex items-center gap-2 mx-auto"
              >
                <RefreshCw size={18} className={isGenerating ? 'animate-spin' : ''} />
                {isGenerating ? '분석 생성 중...' : '다시 시도'}
              </button>
            </div>
          </Card>
        ) : (
          <>
            {/* AI 종합 평가 */}
            <Card className="bg-white border-gray-200 mb-6">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                    <Target className="text-emerald-600" />
                    AI 종합 평가
                  </h2>
                  <span className={`px-4 py-2 rounded-lg text-lg font-bold ${getOpinionStyle(displayAnalysis.summary.opinion).bg} ${getOpinionStyle(displayAnalysis.summary.opinion).text}`}>
                    {getOpinionStyle(displayAnalysis.summary.opinion).label}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">현재가</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {displayAnalysis.summary.current_price.toLocaleString()}원
                    </div>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">예상가</div>
                    <div className="text-2xl font-bold text-emerald-600">
                      {displayAnalysis.summary.target_price.toLocaleString()}원
                    </div>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <div className="text-sm text-gray-600 mb-1">상승/하강 여력</div>
                    <div className={`text-2xl font-bold ${displayAnalysis.summary.upside >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {displayAnalysis.summary.upside >= 0 ? '+' : ''}{displayAnalysis.summary.upside.toFixed(1)}%
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50/90 rounded-lg p-4">
                  <h3 className="text-sm text-gray-600 mb-3">핵심 투자 포인트</h3>
                  <ul className="space-y-2">
                    {(displayAnalysis.summary.key_points || []).map((point, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-gray-700">
                        <span className="text-emerald-600 mt-1">•</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </Card>

            {/* 재무 분석 */}
            <Card className="bg-white border-gray-200 mb-6">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <BarChart3 className="text-emerald-600" />
                  재무 분석
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">수익성</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.financial_analysis.profitability}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">성장성</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.financial_analysis.growth}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">안정성</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.financial_analysis.stability}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">밸류에이션</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.financial_analysis.valuation}</p>
                  </div>
                </div>
              </div>
            </Card>

            {/* 기술적 분석 + 뉴스 분석 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* 기술적 분석 */}
              <Card className="bg-white border-gray-200">
                <div className="p-6">
                  <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Activity className="text-emerald-600" />
                    기술적 분석
                  </h2>
                  <div className="space-y-4">
                    <div className="bg-gray-50/90 rounded-lg p-4">
                      <h3 className="text-sm text-emerald-600 font-semibold mb-2">추세</h3>
                      <p className="text-gray-700 text-sm">{displayAnalysis.technical_analysis.trend}</p>
                    </div>
                    <div className="bg-gray-50/90 rounded-lg p-4">
                      <h3 className="text-sm text-emerald-600 font-semibold mb-2">지지/저항</h3>
                      <p className="text-gray-700 text-sm">{displayAnalysis.technical_analysis.support_resistance}</p>
                    </div>
                    <div className="bg-gray-50/90 rounded-lg p-4">
                      <h3 className="text-sm text-emerald-600 font-semibold mb-2">지표 분석</h3>
                      <p className="text-gray-700 text-sm">{displayAnalysis.technical_analysis.indicators}</p>
                    </div>
                  </div>
                </div>
              </Card>

              {/* 뉴스 분석 */}
              <Card className="bg-white border-gray-200">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                      <Newspaper className="text-emerald-600" />
                      뉴스 분석
                    </h2>
                    <span className={`px-3 py-1 rounded text-sm font-semibold ${getSentimentStyle(displayAnalysis.news_analysis.sentiment).bg} ${getSentimentStyle(displayAnalysis.news_analysis.sentiment).text}`}>
                      {getSentimentStyle(displayAnalysis.news_analysis.sentiment).label}
                    </span>
                  </div>
                  <div className="space-y-4">
                    <div className="bg-gray-50/90 rounded-lg p-4">
                      <h3 className="text-sm text-emerald-600 font-semibold mb-2">주요 뉴스</h3>
                      <ul className="space-y-1">
                        {(displayAnalysis.news_analysis.key_news || []).map((news, idx) => (
                          <li key={idx} className="text-gray-700 text-sm flex items-start gap-2">
                            <span className="text-gray-500">•</span>
                            <span>{news}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="bg-gray-50/90 rounded-lg p-4">
                      <h3 className="text-sm text-emerald-600 font-semibold mb-2">영향 분석</h3>
                      <p className="text-gray-700 text-sm">{displayAnalysis.news_analysis.impact}</p>
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* 산업 분석 */}
            <Card className="bg-white border-gray-200 mb-6">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Building2 className="text-emerald-600" />
                  산업 및 경쟁 분석
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">업종 트렌드</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.industry_analysis.industry_trend}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">경쟁 우위</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.industry_analysis.competitive_advantage}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">시장 지위</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.industry_analysis.market_position}</p>
                  </div>
                </div>
              </div>
            </Card>

            {/* 리스크 요인 */}
            <Card className="bg-white border-gray-200 mb-6">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <Shield className="text-red-400" />
                  리스크 요인
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {(displayAnalysis.risk_factors || []).map((risk, idx) => (
                    <div key={idx} className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <div className="flex items-start gap-2">
                        <AlertCircle className="text-red-400 mt-0.5 flex-shrink-0" size={16} />
                        <p className="text-gray-700 text-sm">{risk}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            {/* 투자 전략 */}
            <Card className="bg-white border-gray-200 mb-6">
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingUp className="text-emerald-600" />
                  투자 전략
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">단기 (1주-1개월)</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.investment_strategy.short_term}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">중기 (1-3개월)</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.investment_strategy.mid_term}</p>
                  </div>
                  <div className="bg-gray-50/90 rounded-lg p-4">
                    <h3 className="text-sm text-emerald-600 font-semibold mb-2">장기 (3개월+)</h3>
                    <p className="text-gray-700 text-sm">{displayAnalysis.investment_strategy.long_term}</p>
                  </div>
                </div>
              </div>
            </Card>

            {/* 메타데이터 및 재분석 버튼 */}
            <div className="flex items-center justify-between">
              <button
                onClick={() => {
                  setGenerationType('refresh')
                  setStatusMessage('최신 데이터로 분석을 재생성하고 있습니다...')
                  setViewState('loading')
                  refreshAnalysis({ ticker: ticker || '' })
                }}
                disabled={isGenerating}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 disabled:bg-gray-50 text-gray-600 hover:text-gray-900 rounded-lg text-sm transition-colors flex items-center gap-2"
              >
                <RefreshCw size={14} className={isGenerating ? 'animate-spin' : ''} />
                {isGenerating ? '재분석 중...' : '재분석'}
              </button>
              <div className="text-xs text-gray-500">
                분석일: {new Date(displayAnalysis.generated_at).toLocaleString('ko-KR')} | 모델: {displayAnalysis.model_name}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
