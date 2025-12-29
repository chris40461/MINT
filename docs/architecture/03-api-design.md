# REST API 설계

## 📌 문서 목적

SKKU-INSIGHT의 전체 REST API 엔드포인트를 정의하고, Request/Response 형식, 에러 핸들링, Rate Limiting 전략을 설명합니다.

---

## 🌐 API 기본 정보

### Base URL
```
개발: http://localhost:8000/api/v1
프로덕션: https://api.skku-insight.com/api/v1
```

### 버전 관리
- **현재 버전**: v1
- **하위 호환성**: v1은 최소 1년간 유지
- **신규 버전**: v2는 /api/v2로 제공

### 인증 (Phase 2)
```http
Authorization: Bearer {JWT_TOKEN}
```

### 공통 헤더
```http
Content-Type: application/json
Accept: application/json
X-Request-ID: {uuid}  # 요청 추적용
```

---

## 📋 API 엔드포인트 전체 목록

### 1. 급등주 트리거 (Triggers)
```
GET    /api/v1/triggers                  # 급등주 목록 조회
GET    /api/v1/triggers/{trigger_id}     # 특정 트리거 상세
GET    /api/v1/triggers/history           # 트리거 히스토리
```

### 2. 기업 분석 (Analysis)
```
GET    /api/v1/analysis/{ticker}          # 기업 분석 조회
POST   /api/v1/analysis/{ticker}/refresh  # 강제 재분석
GET    /api/v1/analysis/batch              # 여러 종목 분석 (쿼리)
```

### 3. 장 리포트 (Reports)
```
GET    /api/v1/reports/morning             # 장 시작 리포트
GET    /api/v1/reports/afternoon           # 장 마감 리포트
GET    /api/v1/reports/history             # 과거 리포트
```

### 4. 종목 정보 (Stocks)
```
GET    /api/v1/stocks/{ticker}             # 종목 기본 정보
GET    /api/v1/stocks/{ticker}/price       # 가격 히스토리
GET    /api/v1/stocks/search               # 종목 검색
```

### 5. 평가 시스템 (Evaluation)
```
POST   /api/v1/evaluation/feedback         # 사용자 피드백
GET    /api/v1/evaluation/metrics          # 평가 지표 조회
GET    /api/v1/evaluation/performance      # 성과 대시보드
```

### 6. 시스템 (System)
```
GET    /api/v1/health                      # 헬스 체크
GET    /api/v1/status                      # 시스템 상태
```

---

## 🔍 엔드포인트 상세 명세

## 1. 급등주 트리거 API

### 1.1 급등주 목록 조회
```http
GET /api/v1/triggers?session={session}&date={date}&type={type}
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|---------|------|------|------|------|
| session | string | X | 장 세션 (morning/afternoon) | morning |
| date | string | X | 날짜 (YYYY-MM-DD) | 2025-11-06 |
| type | string | X | 트리거 타입 | volume_surge |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "session": "morning",
    "date": "2025-11-06",
    "generated_at": "2025-11-06T09:15:23",
    "triggers": [
      {
        "type": "volume_surge",
        "type_name": "거래량 급증",
        "description": "전일 대비 거래량 30% 이상 증가",
        "stocks": [
          {
            "rank": 1,
            "ticker": "005930",
            "name": "삼성전자",
            "current_price": 75000,
            "change_rate": 3.45,
            "change_amount": 2500,
            "volume": 15000000,
            "volume_increase_rate": 45.2,
            "trading_value": 1125000000000,
            "market_cap": 450000000000000,
            "composite_score": 0.92,
            "indicators": {
              "volume_increase_norm": 0.95,
              "volume_norm": 0.88
            }
          },
          {
            "rank": 2,
            "ticker": "000660",
            "name": "SK하이닉스",
            "current_price": 150000,
            "change_rate": 2.8,
            "volume_increase_rate": 38.5,
            "composite_score": 0.87
          },
          {
            "rank": 3,
            "ticker": "035420",
            "name": "NAVER",
            "current_price": 250000,
            "change_rate": 1.9,
            "volume_increase_rate": 35.1,
            "composite_score": 0.81
          }
        ]
      },
      {
        "type": "gap_up",
        "type_name": "갭 상승 모멘텀",
        "stocks": [...]
      },
      {
        "type": "fund_inflow",
        "type_name": "시총 대비 자금유입",
        "stocks": [...]
      }
    ],
    "metadata": {
      "total_triggers": 3,
      "total_stocks": 9,
      "cache_hit": true,
      "ttl": 3600
    }
  }
}
```

**Response 404**:
```json
{
  "success": false,
  "error": {
    "code": "TRIGGERS_NOT_FOUND",
    "message": "해당 날짜의 트리거 데이터가 없습니다",
    "details": {
      "date": "2025-11-06",
      "session": "morning"
    }
  }
}
```

### 1.2 트리거 히스토리
```http
GET /api/v1/triggers/history?ticker={ticker}&days={days}
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|-------|
| ticker | string | O | 종목 코드 | - |
| days | integer | X | 조회 기간 (일) | 30 |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "period": {
      "start": "2025-10-07",
      "end": "2025-11-06"
    },
    "history": [
      {
        "date": "2025-11-06",
        "session": "morning",
        "trigger_type": "volume_surge",
        "rank": 1,
        "score": 0.92,
        "price_at_trigger": 75000,
        "d_plus_1_return": 2.3,  // D+1 수익률 (%)
        "d_plus_7_return": 5.8
      },
      {
        "date": "2025-10-28",
        "session": "afternoon",
        "trigger_type": "closing_strength",
        "rank": 2,
        "score": 0.85,
        "d_plus_1_return": -1.2
      }
    ],
    "statistics": {
      "total_appearances": 5,
      "avg_score": 0.87,
      "avg_d_plus_1_return": 1.8,
      "win_rate": 0.6  // 60%
    }
  }
}
```

---

## 2. 기업 분석 API

### 2.1 기업 분석 조회
```http
GET /api/v1/analysis/{ticker}?force_refresh={boolean}
```

**Path Parameters**:
| 파라미터 | 타입 | 설명 | 예시 |
|---------|------|------|------|
| ticker | string | 종목 코드 (6자리) | 005930 |

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|-------|
| force_refresh | boolean | X | 캐시 무시 재분석 | false |

**Response 200** (Cache Hit):
```json
{
  "success": true,
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "date": "2025-11-06",
    "source": "cache",
    "analysis": {
      "summary": {
        "investment_opinion": "매수",
        "investment_opinion_code": "BUY",  // STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
        "target_price": 85000,
        "current_price": 75000,
        "upside_potential": 13.33,
        "key_insights": [
          "반도체 슈퍼 사이클 진입으로 수익성 개선 전망",
          "HBM3 시장 점유율 확대로 프리미엄 확보",
          "배당 확대 정책으로 주주 가치 제고"
        ],
        "confidence_score": 0.85
      },
      "financial_analysis": {
        "profitability": {
          "summary": "매출 성장과 함께 영업이익률 개선 중",
          "metrics": {
            "revenue": 300000000000000,
            "revenue_growth_yoy": 12.5,
            "operating_margin": 15.2,
            "net_margin": 11.8,
            "roe": 14.2,
            "roa": 8.5
          },
          "evaluation": "양호"
        },
        "stability": {
          "summary": "견고한 재무 구조 유지",
          "metrics": {
            "debt_ratio": 45.3,
            "current_ratio": 2.1,
            "interest_coverage": 12.5
          },
          "evaluation": "우수"
        },
        "growth": {
          "summary": "지속적인 성장세",
          "metrics": {
            "revenue_cagr_3y": 8.5,
            "eps_growth_yoy": 15.2
          },
          "evaluation": "양호"
        },
        "valuation": {
          "summary": "업종 평균 대비 저평가",
          "metrics": {
            "per": 12.5,
            "pbr": 1.8,
            "industry_avg_per": 15.2,
            "industry_avg_pbr": 2.1
          },
          "evaluation": "저평가"
        }
      },
      "industry_analysis": {
        "sector": "IT/반도체",
        "industry_trend": "호황",
        "market_position": "글로벌 1위 (메모리 반도체)",
        "competitive_advantage": [
          "기술력: 최첨단 공정 기술 (3nm, 2nm)",
          "규모의 경제: 세계 최대 생산 능력",
          "브랜드: 글로벌 인지도"
        ],
        "competitors": [
          {
            "name": "SK하이닉스",
            "ticker": "000660",
            "market_share": 0.3,
            "comparison": "HBM 시장에서 경쟁 우위"
          }
        ]
      },
      "news_analysis": {
        "period": "2025-10-30 ~ 2025-11-06",
        "total_articles": 42,
        "sentiment": {
          "positive": 28,
          "neutral": 10,
          "negative": 4,
          "overall_score": 0.75
        },
        "key_topics": [
          {
            "topic": "HBM3 수주",
            "frequency": 15,
            "sentiment": "positive"
          },
          {
            "topic": "반도체 투자 확대",
            "frequency": 8,
            "sentiment": "positive"
          }
        ],
        "major_news": [
          {
            "date": "2025-11-05",
            "title": "삼성전자, HBM3 대량 수주 성공",
            "summary": "엔비디아향 HBM3 공급 계약 체결",
            "sentiment": "positive",
            "impact": "high"
          }
        ]
      },
      "technical_analysis": {
        "trend": "상승",
        "indicators": {
          "rsi": {
            "value": 62.3,
            "signal": "중립",
            "description": "과매수 진입 전 단계"
          },
          "macd": {
            "value": 120,
            "signal": 115,
            "histogram": 5,
            "signal_type": "골든크로스",
            "description": "상승 신호"
          },
          "moving_averages": {
            "ma_5": 74500,
            "ma_20": 73000,
            "ma_60": 71500,
            "current_vs_ma_20": "상회",
            "signal": "강세"
          },
          "bollinger_bands": {
            "upper": 78000,
            "middle": 73000,
            "lower": 68000,
            "current_position": "중상단",
            "signal": "상승 여력"
          }
        },
        "support_resistance": {
          "resistance_1": 77000,
          "resistance_2": 80000,
          "support_1": 72000,
          "support_2": 68000
        }
      },
      "risk_factors": [
        {
          "type": "시장 리스크",
          "description": "글로벌 반도체 경기 둔화 가능성",
          "severity": "중간",
          "mitigation": "다양한 제품 포트폴리오로 리스크 분산"
        },
        {
          "type": "환율 리스크",
          "description": "원화 강세 시 수출 경쟁력 약화",
          "severity": "중간",
          "mitigation": "환헤지 전략 운용"
        },
        {
          "type": "경쟁 리스크",
          "description": "중국 업체의 추격",
          "severity": "낮음",
          "mitigation": "기술 격차 유지 중"
        }
      ],
      "investment_strategy": {
        "short_term": {
          "horizon": "1-3개월",
          "strategy": "단기 차익 실현 목적 매수",
          "entry_price": "72,000원 이하 분할 매수",
          "target_price": 80000,
          "stop_loss": 68000,
          "position_size": "포트폴리오의 10-15%"
        },
        "medium_term": {
          "horizon": "3-12개월",
          "strategy": "실적 개선 기대 중장기 보유",
          "target_price": 90000,
          "monitoring_points": [
            "분기 실적 발표",
            "HBM 수주 현황",
            "반도체 업황 변화"
          ]
        },
        "long_term": {
          "horizon": "1년 이상",
          "strategy": "배당 수익 + 자본 차익 목적 장기 보유",
          "rationale": "글로벌 반도체 시장 성장 수혜",
          "rebalancing": "분기별 포트폴리오 재조정"
        }
      }
    },
    "metadata": {
      "generated_at": "2025-11-06T10:30:15",
      "cached_at": "2025-11-06T10:30:15",
      "ttl_remaining": 82800,  // 초 단위
      "expires_at": "2025-11-07T10:30:15",
      "model": "gemini-2.5-flash",
      "tokens_used": 1850,
      "processing_time_ms": 3250
    }
  }
}
```

**Response 202** (Processing - LLM 생성 중):
```json
{
  "success": true,
  "message": "분석이 진행 중입니다",
  "data": {
    "ticker": "005930",
    "status": "processing",
    "estimated_time": 5,  // 초
    "retry_after": 3
  }
}
```

**Response 400**:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_TICKER",
    "message": "잘못된 종목 코드입니다",
    "details": {
      "ticker": "00593",
      "expected_format": "6자리 숫자"
    }
  }
}
```

### 2.2 강제 재분석
```http
POST /api/v1/analysis/{ticker}/refresh
```

**Request Body**: 없음

**Response 200**:
```json
{
  "success": true,
  "message": "재분석이 요청되었습니다",
  "data": {
    "ticker": "005930",
    "previous_analysis_date": "2025-11-06T10:30:15",
    "estimated_completion": "2025-11-06T14:25:30"
  }
}
```

### 2.3 배치 분석 조회
```http
GET /api/v1/analysis/batch?tickers=005930,000660,035420
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 제약 |
|---------|------|------|------|------|
| tickers | string | O | 종목 코드 (쉼표 구분) | 최대 10개 |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "opinion": "BUY",
        "target_price": 85000,
        "current_price": 75000,
        "upside": 13.33
      },
      {
        "ticker": "000660",
        "name": "SK하이닉스",
        "opinion": "STRONG_BUY",
        "target_price": 180000,
        "current_price": 150000,
        "upside": 20.0
      }
    ],
    "metadata": {
      "requested": 3,
      "successful": 2,
      "failed": 1,
      "cache_hits": 2
    }
  }
}
```

---

## 3. 장 리포트 API

### 3.1 장 시작 리포트
```http
GET /api/v1/reports/morning?date={date}
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|-------|
| date | string | X | 날짜 (YYYY-MM-DD) | 오늘 |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "report_type": "morning",
    "date": "2025-11-06",
    "generated_at": "2025-11-06T08:32:15",
    "market_overview": {
      "previous_day": {
        "kospi": {
          "close": 2500.5,
          "change_rate": -0.45,
          "trading_value": 8500000000000
        },
        "kosdaq": {
          "close": 850.2,
          "change_rate": -0.3
        }
      },
      "us_market": {
        "sp500": {
          "close": 4500.2,
          "change_rate": 1.2
        },
        "nasdaq": {
          "close": 14000.5,
          "change_rate": 1.5
        }
      },
      "exchange_rate": {
        "usd_krw": 1320,
        "change": 5
      },
      "overnight_factors": [
        "미국 증시 강세로 위험자산 선호 심리 확대",
        "원화 약세로 수출주 수혜 기대",
        "유가 상승으로 정유주 주목"
      ]
    },
    "market_forecast": {
      "direction": "상승",
      "confidence": 0.75,
      "expected_range": {
        "kospi": {
          "low": 2485,
          "high": 2525
        }
      },
      "key_factors": [
        "미국 증시 상승 영향",
        "외국인 매수세 유입 기대",
        "반도체주 강세 전망"
      ],
      "summary": "미국 증시 상승과 원화 약세로 수출주 중심 강세 예상. KOSPI 2500선 상회 시도할 것으로 전망."
    },
    "top_stocks": [
      {
        "rank": 1,
        "ticker": "005930",
        "name": "삼성전자",
        "current_price": 75000,
        "total_score": 0.88,
        "scores": {
          "momentum": 0.85,
          "volume": 0.90,
          "sentiment": 0.92,
          "technical": 0.80,
          "financial": 0.85
        },
        "rationale": "HBM3 수주 모멘텀과 기술적 돌파 기대",
        "entry_strategy": "72,000원 이하 분할 매수",
        "target_price": 80000,
        "catalysts": [
          "미국 엔비디아 실적 호조 기대감",
          "HBM3 공급 계약 체결"
        ]
      },
      {
        "rank": 2,
        "ticker": "000660",
        "name": "SK하이닉스",
        "total_score": 0.85,
        "rationale": "HBM 시장 점유율 확대"
      },
      {
        "rank": 3,
        "ticker": "051910",
        "name": "LG화학",
        "total_score": 0.82
      },
      {
        "rank": 4,
        "ticker": "005380",
        "name": "현대차",
        "total_score": 0.79
      },
      {
        "rank": 5,
        "ticker": "035420",
        "name": "NAVER",
        "total_score": 0.77
      }
    ],
    "sector_analysis": {
      "strong_sectors": [
        {
          "sector": "IT/반도체",
          "expected_performance": "강세",
          "rationale": "미국 반도체주 상승 영향",
          "representative_stocks": ["005930", "000660"]
        },
        {
          "sector": "자동차",
          "expected_performance": "강세",
          "rationale": "원화 약세로 수출 경쟁력 강화"
        }
      ],
      "weak_sectors": [
        {
          "sector": "건설",
          "expected_performance": "약세",
          "rationale": "부동산 경기 둔화 우려"
        }
      ]
    },
    "investment_strategy": {
      "overall_stance": "공격적 매수",
      "risk_level": "중간",
      "recommendations": [
        "반도체주 중심 포트폴리오 구성",
        "장 초반 급등 시 분할 매수 전략",
        "2,500선 돌파 실패 시 관망"
      ],
      "caution_points": [
        "미국 금리 인상 우려",
        "중국 경제 둔화 리스크"
      ]
    },
    "key_events": [
      {
        "time": "09:00",
        "event": "삼성전자 공시 예정",
        "impact": "high"
      },
      {
        "time": "14:00",
        "event": "미국 고용지표 발표",
        "impact": "medium"
      }
    ],
    "metadata": {
      "model": "gemini-2.5-flash",
      "tokens_used": 2100,
      "processing_time_ms": 4500,
      "cache_ttl": 43200
    }
  }
}
```

### 3.2 장 마감 리포트
```http
GET /api/v1/reports/afternoon?date={date}
```

유사한 구조이지만 다음 추가:
- 당일 시장 요약
- 급등주 상세 분석
- 내일 전략

---

## 4. 종목 정보 API

### 4.1 종목 기본 정보
```http
GET /api/v1/stocks/{ticker}
```

**Response 200**:
```json
{
  "success": true,
  "data": {
    "ticker": "005930",
    "name": "삼성전자",
    "name_en": "Samsung Electronics",
    "market": "KOSPI",
    "sector": "IT/반도체",
    "industry": "메모리 반도체",
    "listed_date": "1975-06-11",
    "listing_shares": 5969782550,
    "market_cap": 450000000000000,
    "description": "세계 1위 메모리 반도체 제조사",
    "website": "https://www.samsung.com",
    "ceo": "한종희"
  }
}
```

### 4.2 가격 히스토리
```http
GET /api/v1/stocks/{ticker}/price?start={start}&end={end}&interval={interval}
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|-------|
| start | string | X | 시작일 (YYYY-MM-DD) | 30일 전 |
| end | string | X | 종료일 (YYYY-MM-DD) | 오늘 |
| interval | string | X | 간격 (day/week/month) | day |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "ticker": "005930",
    "period": {
      "start": "2025-10-07",
      "end": "2025-11-06"
    },
    "interval": "day",
    "prices": [
      {
        "date": "2025-11-06",
        "open": 73500,
        "high": 76000,
        "low": 73000,
        "close": 75000,
        "volume": 15000000,
        "trading_value": 1125000000000,
        "change_rate": 3.45
      },
      ...
    ],
    "statistics": {
      "avg_price": 72500,
      "high_52w": 82000,
      "low_52w": 62000,
      "volatility": 18.5
    }
  }
}
```

### 4.3 종목 검색
```http
GET /api/v1/stocks/search?q={query}&limit={limit}
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|-------|
| q | string | O | 검색어 (종목명/코드) | - |
| limit | integer | X | 결과 개수 | 10 |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "query": "삼성",
    "results": [
      {
        "ticker": "005930",
        "name": "삼성전자",
        "market": "KOSPI",
        "current_price": 75000,
        "match_score": 1.0
      },
      {
        "ticker": "005935",
        "name": "삼성전자우",
        "market": "KOSPI",
        "current_price": 65000,
        "match_score": 0.95
      },
      {
        "ticker": "028260",
        "name": "삼성물산",
        "market": "KOSPI",
        "current_price": 120000,
        "match_score": 0.8
      }
    ],
    "total": 15,
    "showing": 3
  }
}
```

---

## 5. 평가 시스템 API

### 5.1 사용자 피드백 제출
```http
POST /api/v1/evaluation/feedback
```

**Request Body**:
```json
{
  "type": "analysis",  // analysis / morning_report / afternoon_report
  "ticker": "005930",
  "date": "2025-11-06",
  "rating": 4,  // 1-5
  "comment": "분석이 정확했습니다",
  "helpful": true
}
```

**Response 200**:
```json
{
  "success": true,
  "message": "피드백이 제출되었습니다",
  "data": {
    "feedback_id": "fb_1234567890"
  }
}
```

### 5.2 평가 지표 조회
```http
GET /api/v1/evaluation/metrics?period={period}
```

**Query Parameters**:
| 파라미터 | 타입 | 필수 | 설명 | 기본값 |
|---------|------|------|------|-------|
| period | string | X | 기간 (7d/30d/90d) | 7d |

**Response 200**:
```json
{
  "success": true,
  "data": {
    "period": "7d",
    "start_date": "2025-10-30",
    "end_date": "2025-11-06",
    "quantitative": {
      "prediction_accuracy": {
        "total_recommendations": 42,
        "correct_predictions": 24,
        "win_rate": 0.571,
        "avg_return": 2.3,
        "sharpe_ratio": 1.25
      },
      "target_price_achievement": {
        "total": 30,
        "achieved": 12,
        "achievement_rate": 0.40,
        "avg_days_to_achieve": 8.5
      },
      "stop_loss_avoidance": {
        "total_holdings": 20,
        "avoided_stop_loss": 14,
        "avoidance_rate": 0.70
      }
    },
    "qualitative": {
      "analysis_depth": {
        "avg_score": 8.5,
        "metrics": {
          "financial_coverage": 0.95,
          "technical_coverage": 0.90,
          "news_coverage": 0.85
        }
      },
      "user_satisfaction": {
        "avg_rating": 4.2,
        "total_feedback": 150,
        "helpful_rate": 0.82
      }
    },
    "by_source": {
      "analysis": {
        "win_rate": 0.62,
        "count": 20
      },
      "morning_report": {
        "win_rate": 0.54,
        "count": 15
      },
      "afternoon_report": {
        "win_rate": 0.57,
        "count": 7
      }
    }
  }
}
```

---

## 6. 시스템 API

### 6.1 헬스 체크
```http
GET /api/v1/health
```

**Response 200**:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-06T14:30:00",
  "services": {
    "database": "up",
    "redis": "up",
    "llm": "up"
  }
}
```

### 6.2 시스템 상태
```http
GET /api/v1/status
```

**Response 200**:
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "uptime": 864000,  // 초
    "market_status": "open",  // open / closed / pre_market / after_market
    "last_trigger_run": {
      "morning": "2025-11-06T09:15:00",
      "afternoon": "2025-11-06T15:35:00"
    },
    "cache": {
      "hit_rate": 0.85,
      "memory_usage": 45.2  // %
    },
    "llm": {
      "requests_today": 150,
      "tokens_used_today": 280000,
      "estimated_cost_today": 2.8  // USD
    }
  }
}
```

---

## ⚠️ 에러 처리

### 에러 응답 형식
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "사용자 친화적 메시지",
    "details": {
      // 추가 정보
    },
    "request_id": "req_1234567890",
    "timestamp": "2025-11-06T14:30:00"
  }
}
```

### HTTP 상태 코드

| 코드 | 의미 | 예시 |
|------|------|------|
| 200 | 성공 | 정상 응답 |
| 202 | 처리 중 | LLM 분석 진행 중 |
| 400 | 잘못된 요청 | 유효하지 않은 ticker |
| 404 | 찾을 수 없음 | 데이터 없음 |
| 429 | 요청 제한 초과 | Rate Limit |
| 500 | 서버 에러 | 내부 오류 |
| 503 | 서비스 불가 | 유지보수 중 |

### 에러 코드 목록

```python
# 클라이언트 에러 (4xx)
INVALID_TICKER = "INVALID_TICKER"
INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
MISSING_REQUIRED_PARAM = "MISSING_REQUIRED_PARAM"
TRIGGERS_NOT_FOUND = "TRIGGERS_NOT_FOUND"
ANALYSIS_NOT_FOUND = "ANALYSIS_NOT_FOUND"
STOCK_NOT_FOUND = "STOCK_NOT_FOUND"

# 서버 에러 (5xx)
DATA_COLLECTION_FAILED = "DATA_COLLECTION_FAILED"
LLM_API_ERROR = "LLM_API_ERROR"
DATABASE_ERROR = "DATABASE_ERROR"
CACHE_ERROR = "CACHE_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Rate Limiting
RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
```

---

## 🚦 Rate Limiting

### 제한 정책
```python
# IP 기반 제한 (Phase 1)
RATE_LIMITS = {
    "default": "100/minute",
    "analysis": "20/minute",  # LLM 호출 비용 고려
    "triggers": "60/minute",
    "stocks": "100/minute"
}

# 사용자 기반 제한 (Phase 2)
USER_RATE_LIMITS = {
    "free": "50/minute",
    "premium": "200/minute"
}
```

### Rate Limit 헤더
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 85
X-RateLimit-Reset: 1699272000  # Unix timestamp
```

### Rate Limit 초과 응답
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "요청 한도를 초과했습니다",
    "details": {
      "limit": 100,
      "reset_at": "2025-11-06T14:35:00",
      "retry_after": 45  // 초
    }
  }
}
```

---

## 📊 페이지네이션

### 요청
```http
GET /api/v1/triggers/history?ticker=005930&page=2&per_page=20
```

### 응답
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "current_page": 2,
      "per_page": 20,
      "total_items": 150,
      "total_pages": 8,
      "has_next": true,
      "has_prev": true,
      "next_page": 3,
      "prev_page": 1
    }
  }
}
```

---

## 🔐 보안

### CORS 설정
```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # 개발
    "https://skku-insight.com"  # 프로덕션
]
```

### Request ID 추적
모든 요청은 고유 ID 생성:
```http
X-Request-ID: req_1234567890abcdef
```

로그에 기록하여 디버깅 용이

---

## 📚 참고 자료

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [REST API Best Practices](https://restfulapi.net/)
- [HTTP Status Codes](https://httpstatuses.com/)

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
