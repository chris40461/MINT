/**
 * 포맷팅 유틸리티 함수
 */

/**
 * 시가총액 포맷팅
 * @param marketCapInEok - 시가총액 (억원 단위, Backend에서 받은 그대로)
 * @returns 포맷팅된 문자열 (예: "5조", "500억원")
 */
export function formatMarketCap(marketCapInEok: number): string {
  if (marketCapInEok === 0 || marketCapInEok === null || marketCapInEok === undefined) {
    return '-'
  }

  // 1조 = 10000억
  const trillion = 10000

  if (marketCapInEok >= trillion) {
    // 조 단위 변환
    const trillionValue = marketCapInEok / trillion

    // 소수점 1자리까지 표시 (단, .0이면 정수로)
    if (trillionValue % 1 === 0) {
      return `${trillionValue.toLocaleString()}조`
    } else {
      return `${trillionValue.toFixed(1)}조`
    }
  } else {
    // 억원 단위 (소수점 버림)
    return `${Math.floor(marketCapInEok).toLocaleString()}억원`
  }
}

/**
 * 가격 포맷팅
 * @param price - 가격 (원 단위)
 * @returns 포맷팅된 문자열 (예: "72,000원")
 */
export function formatPrice(price: number | undefined): string {
  if (price === undefined || price === null) {
    return '-'
  }
  return `${price.toLocaleString()}원`
}

/**
 * 등락률 포맷팅
 * @param changeRate - 등락률 (%)
 * @returns 포맷팅된 문자열 (예: "+2.50%", "-1.23%")
 */
export function formatChangeRate(changeRate: number | undefined): string {
  if (changeRate === undefined || changeRate === null) {
    return '-'
  }
  const sign = changeRate >= 0 ? '+' : ''
  return `${sign}${changeRate.toFixed(2)}%`
}
