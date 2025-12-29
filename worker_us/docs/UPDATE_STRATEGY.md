# Backend_US 테이블별 업데이트 전략

## 📊 테이블 분류 (9개 테이블)

### 🟢 **매일 업데이트 (Daily)** - 5개

| 테이블 | 주기 | 시간 | 데이터량 | 이유 |
|--------|------|------|----------|------|
| **fred_macro** | 매일 | 08:00 | 1 row | 금리는 매일 변동, 가벼움 |
| **price_daily** | 매일 | 16:00 | 3,343 rows | OHLCV는 매 거래일 필수 |
| **news** | 매일 2회 | 08:00, 16:00 | ~67K rows | 실시간 뉴스 중요 |
| **fundamentals** | 매일 | 16:00 | 3,343 rows | PE/PB 등 투자지표 (급등락 우선) |
| **options_summary** | 매일 | 16:00 | 3,343 rows | PCR, IV 요약 통계 |

### 🟡 **주간 업데이트 (Weekly)** - 1개

| 테이블 | 주기 | 시간 | 데이터량 | 이유 |
|--------|------|------|----------|------|
| **stocks** | 주 1회 | 일요일 00:00 | 3,343 rows | 종목명/섹터 거의 불변 |

### 🔵 **분기 업데이트 (Quarterly)** - 3개

| 테이블 | 주기 | 시간 | 데이터량 | 이유 |
|--------|------|------|----------|------|
| **income_statement** | 분기 1회 | 실적 발표 후 | ~16,715 rows | 분기 실적 |
| **balance_sheet** | 분기 1회 | 실적 발표 후 | ~16,715 rows | 분기 재무상태 |
| **cash_flow** | 분기 1회 | 실적 발표 후 | ~16,715 rows | 분기 현금흐름 |

### ❌ **삭제 (Realtime API 대체)** - 1개

| 테이블 | 삭제 이유 | 대체 방안 |
|--------|----------|----------|
| **options** | 데이터 양 과다 (수백만 rows), 실시간성 중요 | 사용자 요청 시 CBOE API 실시간 조회 |

---

## 🔄 일일 업데이트 스케줄

```
08:00 (장 시작 전)
├─ fred_macro (FRED API)
├─ news 수집 (전체 종목, 종목당 10건)
└─ (선택) 주요 종목 options_summary

16:00 (장 마감 후)
├─ price_daily (D-1 OHLCV 추가)
├─ news 재수집 (장중 뉴스)
├─ fundamentals (급등락 5%↑ 종목 우선)
├─ options_summary (전체 종목)
└─ 오래된 뉴스 삭제 (30일 이상)
```

---

## 💾 데이터 보관 정책

### 영구 보관
- stocks, price_daily, 재무제표 3종

### Rolling Window
- **news**: 최근 30일
- **fundamentals**: 최근 90일 (주간 스냅샷)
- **options_summary**: 최근 90일
- **fred_macro**: 최근 5년

### 삭제
- **options**: DB에 저장 안 함 (실시간 조회)

---

## 📋 최종 권장 구성

```python
# 매일 업데이트 (5개)
daily_tables = [
    'fred_macro',       # 거시경제
    'price_daily',      # 가격
    'news',             # 뉴스
    'fundamentals',     # 펀더멘탈
    'options_summary'   # 옵션 요약
]

# 주간 업데이트 (1개)
weekly_tables = ['stocks']

# 분기 업데이트 (3개)
quarterly_tables = [
    'income_statement',
    'balance_sheet',
    'cash_flow'
]

# 삭제 (실시간 API)
deleted_tables = ['options']
```

---

**총 테이블 수**: 9개 (options 제거)
**매일 업데이트 필수**: 5개
**작성일**: 2025-11-20
