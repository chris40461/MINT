// 참고: docs/frontend/02-routing.md
// 참고: docs/frontend/04-components.md

/**
 * MINT 대시보드 페이지
 *
 * MINT: 주식시장을 시원하고 빠르게!
 */

import { Link } from 'react-router-dom'
import { TrendingUp, BarChart3, Brain, Leaf } from 'lucide-react'
import { Card } from '@/components'

export function Dashboard() {
  return (
    <div className="min-h-screen bg-white">
      {/* Hero Section - Mint Theme */}
      <section className="relative bg-gradient-to-br from-emerald-600 via-emerald-500 to-teal-400 text-white overflow-hidden">
        {/* Background Pattern - Animated blobs - Mint Theme */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-20 left-10 w-72 h-72 bg-emerald-300 rounded-full mix-blend-lighten filter blur-xl animate-blob" />
          <div className="absolute top-40 right-10 w-72 h-72 bg-teal-300 rounded-full mix-blend-lighten filter blur-xl animate-blob animation-delay-2000" />
          <div className="absolute bottom-20 left-40 w-72 h-72 bg-green-300 rounded-full mix-blend-lighten filter blur-xl animate-blob animation-delay-4000" />
        </div>

        {/* Hero Content */}
        <div className="relative container mx-auto px-4 py-24 md:py-32">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-8">
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-emerald-100">
                  <Leaf className="h-6 w-6" />
                  <span className="text-lg font-medium">주식시장을 시원하고 빠르게!</span>
                </div>
                <h1 className="text-5xl md:text-6xl font-bold leading-tight">
                  AI 기반<br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-emerald-100">
                    한국 주식 컨설팅
                  </span>
                </h1>
                <p className="text-xl text-emerald-50 leading-relaxed">
                  급등주 포착부터 AI 분석까지, 데이터 기반 투자 의사결정을 지원합니다
                </p>
              </div>

              {/* Stats */}
              <div className="flex gap-8 pt-4">
                <div>
                  <div className="text-3xl font-bold text-white">100+</div>
                  <div className="text-emerald-100 text-sm">분석 종목</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white">6</div>
                  <div className="text-emerald-100 text-sm">트리거 알고리즘</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-white">2회/일</div>
                  <div className="text-emerald-100 text-sm">AI 리포트</div>
                </div>
              </div>
            </div>

            {/* Right - Logo and Graphics */}
            <div className="hidden md:flex justify-center items-center">
              <img
                src="/mint-logo.png"
                alt="MINT Logo"
                className="w-80 h-auto drop-shadow-2xl animate-float"
              />
            </div>
          </div>
        </div>

        {/* Wave Bottom Divider */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 120" fill="none" className="w-full h-auto">
            <path
              d="M0 120L60 110C120 100 240 80 360 70C480 60 600 60 720 65C840 70 960 80 1080 85C1200 90 1320 90 1380 90L1440 90V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
              fill="rgb(249, 250, 251)"
            />
          </svg>
        </div>
      </section>

      {/* Features Section - Light Theme */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              MINT 란?
            </h2>
            <div className="w-24 h-1 bg-emerald-500 mx-auto"></div>
            <p className="mt-4 text-gray-600 max-w-2xl mx-auto">
              MINT는 AI 기술을 활용하여 한국 주식 투자자를 위한 의사결정 지원 플랫폼입니다.<br />
              복잡한 시장 데이터를 분석하여 투자에 필요한 핵심 정보를 제공합니다.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 - 급등주 */}
            <Link to="/triggers" className="block">
              <Card hoverable className="group bg-white border-gray-200 hover:border-emerald-300 hover:shadow-lg transition-all cursor-pointer h-full">
                <div className="text-center space-y-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-100 text-emerald-600 rounded-lg group-hover:bg-emerald-500 group-hover:text-white transition-colors">
                    <TrendingUp className="h-8 w-8" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900">급등주 포착</h3>
                  <p className="text-gray-600">
                    6개 트리거 알고리즘으로 실시간 급등 가능성 종목을 자동 탐지합니다.
                  </p>
                </div>
              </Card>
            </Link>

            {/* Feature 2 - 리포트 */}
            <Link to="/reports" className="block">
              <Card hoverable className="group bg-white border-gray-200 hover:border-emerald-300 hover:shadow-lg transition-all cursor-pointer h-full">
                <div className="text-center space-y-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-teal-100 text-teal-600 rounded-lg group-hover:bg-teal-500 group-hover:text-white transition-colors">
                    <BarChart3 className="h-8 w-8" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900">장 시작/마감 리포트</h3>
                  <p className="text-gray-600">
                    AI가 하루 2회 시장 분석 리포트를 제공하여 투자 전략을 세울 수 있습니다.
                  </p>
                </div>
              </Card>
            </Link>

            {/* Feature 3 - AI 분석 */}
            <Link to="/analysis" className="block">
              <Card hoverable className="group bg-white border-gray-200 hover:border-emerald-300 hover:shadow-lg transition-all cursor-pointer h-full">
                <div className="text-center space-y-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 text-green-600 rounded-lg group-hover:bg-green-500 group-hover:text-white transition-colors">
                    <Brain className="h-8 w-8" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900">AI 기업 분석</h3>
                  <p className="text-gray-600">
                    재무제표, 뉴스, 기술적 지표를 종합하여 상세한 기업 분석을 제공합니다.
                  </p>
                </div>
              </Card>
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
