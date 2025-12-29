// 참고: docs/frontend/02-routing.md
// 참고: docs/frontend/04-components.md

/**
 * 대시보드 페이지 (Divi 스타일)
 *
 * 디자인 참고: Cryptocurrency Divi Template
 */

import { Link } from 'react-router-dom'
import { TrendingUp, BarChart3, Brain, ArrowRight } from 'lucide-react'
import { Button, Card } from '@/components'

export function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Hero Section - Full Width - Dark Mode */}
      <section className="relative bg-gradient-to-br from-gray-900 via-blue-950 to-black text-white overflow-hidden">
        {/* Background Pattern - Animated blobs - Dark Mode */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-20 left-10 w-72 h-72 bg-blue-500 rounded-full mix-blend-lighten filter blur-xl animate-blob" />
          <div className="absolute top-40 right-10 w-72 h-72 bg-cyan-500 rounded-full mix-blend-lighten filter blur-xl animate-blob animation-delay-2000" />
          <div className="absolute bottom-20 left-40 w-72 h-72 bg-indigo-500 rounded-full mix-blend-lighten filter blur-xl animate-blob animation-delay-4000" />
        </div>

        {/* Hero Content */}
        <div className="relative container mx-auto px-4 py-24 md:py-32">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-8">
              <div className="space-y-4">
                <h1 className="text-5xl md:text-6xl font-bold leading-tight">
                  AI 기반<br />
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-200 to-cyan-200">
                    한국 주식 컨설팅
                  </span>
                </h1>
                <p className="text-xl text-blue-100 leading-relaxed">
                  급등주 포착부터 AI 분석까지, 데이터 기반 투자 의사결정을 지원합니다
                </p>
              </div>

              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link to="/triggers">
                  <Button size="lg" className="w-full sm:w-auto bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800">
                    급등주 보기
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Link to="/reports">
                  <Button size="lg" variant="outline" className="w-full sm:w-auto border-blue-400 text-blue-400 hover:bg-blue-600 hover:text-white hover:border-blue-600">
                    시장 리포트
                  </Button>
                </Link>
              </div>

              {/* Stats */}
              <div className="flex gap-8 pt-4">
                <div>
                  <div className="text-3xl font-bold text-cyan-400">100+</div>
                  <div className="text-gray-400 text-sm">분석 종목</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-cyan-400">6</div>
                  <div className="text-gray-400 text-sm">트리거 알고리즘</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-cyan-400">2회/일</div>
                  <div className="text-gray-400 text-sm">AI 리포트</div>
                </div>
              </div>
            </div>

            {/* Right - 3D SVG Graphics */}
            <div className="hidden md:block">
              <svg viewBox="0 0 400 400" className="w-full h-auto drop-shadow-2xl">
                <g className="animate-float">
                  {/* Isometric blocks representing stock charts */}
                  <path d="M200 80 L280 120 L280 200 L200 160 Z" fill="rgba(96, 165, 250, 0.9)" />
                  <path d="M200 80 L200 160 L120 120 Z" fill="rgba(59, 130, 246, 0.7)" />
                  <path d="M200 160 L280 200 L200 240 L120 200 Z" fill="rgba(96, 165, 250, 0.8)" />

                  <path d="M240 140 L300 170 L300 230 L240 200 Z" fill="rgba(147, 197, 253, 0.9)" />
                  <path d="M240 140 L240 200 L180 170 Z" fill="rgba(96, 165, 250, 0.7)" />
                  <path d="M240 200 L300 230 L240 260 L180 230 Z" fill="rgba(147, 197, 253, 0.8)" />

                  {/* Floating elements */}
                  <circle cx="100" cy="100" r="8" fill="rgba(255, 255, 255, 0.3)" />
                  <circle cx="320" cy="280" r="6" fill="rgba(255, 255, 255, 0.4)" />
                  <circle cx="350" cy="120" r="5" fill="rgba(255, 255, 255, 0.3)" />
                </g>
              </svg>
            </div>
          </div>
        </div>

        {/* Wave Bottom Divider */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 120" fill="none" className="w-full h-auto">
            <path
              d="M0 120L60 110C120 100 240 80 360 70C480 60 600 60 720 65C840 70 960 80 1080 85C1200 90 1320 90 1380 90L1440 90V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
              fill="rgb(17, 24, 39)"
            />
          </svg>
        </div>
      </section>

      {/* Features Section - Dark Mode */}
      <section className="py-20 bg-gray-900">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">
              SKKU-INSIGHT 란?
            </h2>
            <div className="w-24 h-1 bg-cyan-500 mx-auto"></div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <Card hoverable className="group bg-gray-800 border-gray-700 hover:bg-gray-750">
              <div className="text-center space-y-4">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-900 text-blue-400 rounded-lg group-hover:bg-blue-600 group-hover:text-white transition-colors">
                  <TrendingUp className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-bold text-white">급등주 포착</h3>
                <p className="text-gray-400">
                  6개 트리거 알고리즘으로 실시간 급등 가능성 종목을 자동 탐지합니다.
                </p>
              </div>
            </Card>

            {/* Feature 2 */}
            <Card hoverable className="group bg-gray-800 border-gray-700 hover:bg-gray-750">
              <div className="text-center space-y-4">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-green-900 text-green-400 rounded-lg group-hover:bg-green-600 group-hover:text-white transition-colors">
                  <BarChart3 className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-bold text-white">장 시작/마감 리포트</h3>
                <p className="text-gray-400">
                  AI가 하루 2회 시장 분석 리포트를 제공하여 투자 전략을 세울 수 있습니다.
                </p>
              </div>
            </Card>

            {/* Feature 3 */}
            <Card hoverable className="group bg-gray-800 border-gray-700 hover:bg-gray-750">
              <div className="text-center space-y-4">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-900 text-purple-400 rounded-lg group-hover:bg-purple-600 group-hover:text-white transition-colors">
                  <Brain className="h-8 w-8" />
                </div>
                <h3 className="text-xl font-bold text-white">AI 기업 분석</h3>
                <p className="text-gray-400">
                  재무제표, 뉴스, 기술적 지표를 종합하여 상세한 기업 분석을 제공합니다.
                </p>
              </div>
            </Card>
          </div>
        </div>
      </section>
    </div>
  )
}
