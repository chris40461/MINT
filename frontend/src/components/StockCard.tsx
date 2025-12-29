// 참고: docs/frontend/04-components.md

/**
 * 종목 카드 컴포넌트
 */

import { Stock } from '@/types'

interface StockCardProps {
  stock: Stock
  showDetails?: boolean
  onClick?: () => void
}

export function StockCard({ stock, showDetails = false, onClick }: StockCardProps) {
  return (
    <div
      className="card-hover"
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{stock.name}</h3>
          <p className="text-sm text-gray-500">{stock.ticker}</p>
        </div>
        <span className="badge bg-gray-100 text-gray-800">{stock.market}</span>
      </div>

      {showDetails && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-500">시가총액</p>
              <p className="text-sm font-medium">
                {(stock.market_cap / 1_000_000_000_000).toFixed(2)}조원
              </p>
            </div>
            {stock.sector && (
              <div>
                <p className="text-xs text-gray-500">업종</p>
                <p className="text-sm font-medium">{stock.sector}</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
