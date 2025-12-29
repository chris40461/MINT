# 단기 주식 예측 학술 연구 요약

## Executive Summary

본 문서는 "오늘 당일 주목할 만한 종목" 예측을 위한 학술적 근거를 수집한 결과입니다. 10개 이상의 학술 논문 및 연구를 검토하여 단기 주가 예측에 중요한 요소들의 상대적 중요도와 가중치를 도출했습니다.

**핵심 발견:**
- 단기 예측(1-10일)에서는 **가격 기반 특성(Price-based features)**이 가장 중요
- **모멘텀(Momentum)**과 **거래량 패턴(Volume Patterns)**이 단기 예측의 핵심
- 기술적 지표는 보조적 역할이며, 과도한 사용 시 과적합(overfitting) 위험
- 뉴스 센티먼트는 기술적 지표와 결합할 때 5-10% 정확도 향상
- 펀더멘털 분석은 단기 예측보다 중장기 예측에 효과적

---

## 1. 핵심 발견 (Top 5 Papers)

### Paper 1: Assessing the Impact of Technical Indicators on Machine Learning Models for Stock Price Prediction
**저자/출처**: arXiv 2412.15448v1 (2024)

**주요 발견:**
- **가격 기반 특성이 기술적 지표보다 일관되게 우수한 성능** 발휘
- 기본 모델(지표 없음) Feature Importance:
  - Close price: **21.7%**
  - Open price: **21.2%**
  - High price: **20.2%**
  - Low price: **19.6%**
  - Volume: **17.4%**

- RSI 추가 시 Feature Importance:
  - Close: 18.7%
  - RSI: **15.5%**
  - Volume: 14.4%

**핵심 교훈:**
- 기술적 지표는 훈련 정확도를 높이지만 **실제 예측(out-of-sample)에서는 성능 저하**
- Training R²: 0.812 → Testing R²: **-0.020** (심각한 과적합)
- 고빈도 거래 맥락에서 기술적 지표의 **유용성은 제한적**

**시간 프레임**: 1일 단위 예측

---

### Paper 2: Short-term Stock Market Price Trend Prediction Using Deep Learning
**저자/출처**: Journal of Big Data (2020), DOI: 10.1186/s40537-020-00333-6

**주요 발견:**
- **포괄적 특성 공학(Comprehensive Feature Engineering)**이 성능 향상의 핵심
- 19개 기술적 지표를 확장 특성(extended features)과 결합
- **거래량은 S&P 500과 DJI 데이터셋에서 예측 성능 향상에 효과 없음**

**Feature Selection 방법:**
- RFE(Recursive Feature Elimination)로 상위 i개 특성 선정
- 단일 지표보다 **조합된 특성(combined features)**이 효과적

**시간 프레임**: 1-10 거래일 앞 예측

**핵심 교훈:**
- 단순 기술적 지표보다 **도메인 지식 기반 특성 공학**이 중요
- 거래량 단독으로는 미국 시장에서 효과 제한적

---

### Paper 3: Deep Learning for Stock Market Prediction (PMC 7517440)
**저자/출처**: PMC 7517440 (2020)

**주요 발견:**
- **LSTM이 시간적 의존성(temporal dependencies) 포착에 최우수**
- 10개 기술적 지표 사용:
  1. Simple Moving Average (SMA)
  2. Weighted Moving Average (WMA)
  3. **Momentum (MOM)**
  4. Stochastic K%, D%
  5. **RSI**
  6. MACD Signal
  7. Larry Williams' R%
  8. A/D Oscillator
  9. CCI

**예측 정확도 (LSTM MAPE):**
- **1일 예측: 0.43%** (매우 높은 정확도)
- 30일 예측: 0.77%

**핵심 교훈:**
- 단기 예측(1-7일)에서 딥러닝 모델이 전통적 시계열 모델보다 우수
- **예측 기간이 길어질수록 오차 증가** (단기 예측에 집중해야)

**시간 프레임**: 1-30일

---

### Paper 4: Stock Return Prediction with Multiple Measures Using Neural Network Models
**저자/출처**: Financial Innovation (2023), DOI: 10.1186/s40854-023-00608-w

**주요 발견:**
- **이상 수익률(Abnormal Returns) 예측 시 중요 요소:**
  1. **Momentum 변수** (가장 중요)
  2. **Trading Fractions 변수** (거래량 패턴)
  3. 거시경제 변수는 상대적으로 덜 중요

- **초과 수익률(Excess Returns) 예측 시:**
  1. 거시경제 변수 (특히 **Investor Sentiment**)
  2. Momentum은 2순위

**단기 반전(Short-term Reversal):**
- **STreversal**이 모든 수익률 측정치에서 **가장 강력한 단변량 예측 변수**

**거시경제 변수 추가 시 성과 향상:**
- 금융 시장 변수 추가: R² **89.6% 증가**
- 실물 경제 변수 추가: R² **2배 이상 증가**
- 투자자 심리 변수 추가: 최종 R² **5.474%**

**핵심 교훈:**
- 예측 목표(이상수익 vs 초과수익)에 따라 중요 변수가 다름
- 단기 예측에서는 **Momentum + Trading Patterns** 조합이 핵심

**시간 프레임**: 월간 수익률 예측

---

### Paper 5: Stock Trend Prediction Using Sentiment Analysis (PMC 10403218)
**저자/출처**: PMC 10403218 (2023)

**주요 발견:**
- **센티먼트 단독 정확도: 59.18% (K-NN)**
- **센티먼트 + 과거 주가 데이터: 89.80% (K-NN)** - 30.62%p 향상

**다른 연구 결과 (가중치 명시):**
- 센티먼트 가중치: **α = 0.25 (25%)**
- 기술적/과거 데이터 가중치: **1-α = 0.75 (75%)**

**비교 연구:**
- 기술적 요소만 사용: **더 나은 결과**
- 센티먼트 추가: 일부 기업에서 **1.5% 정확도 향상**

**핵심 교훈:**
- 센티먼트는 **단독으로는 약하지만 기술적 지표와 결합 시 효과적**
- 적절한 가중치: 센티먼트 **20-30%**, 기술적 요소 **70-80%**

**시간 프레임**: 1일 예측

---

## 2. 단기 예측 요소 종합

### A. Feature Category별 중요도 랭킹

| 순위 | 요소 | 중요도 | 근거 논문 | 시간 프레임 | 비고 |
|-----|------|-------|---------|-----------|------|
| 1 | **Price-based Features** | 매우 높음 | Paper 1 | D-1 | Close/Open/High/Low 가격 (합계 ~83%) |
| 2 | **Momentum Indicators** | 높음 | Paper 2, 4 | D-1, D-7, D-30 | STreversal, 수익률 추세 |
| 3 | **Volume & Trading Patterns** | 높음 | Paper 1, 4 | D-1, Intraday | Trading Fractions, Volume z-score |
| 4 | **Volatility Measures** | 중간 | Paper 3 | D-7, D-20 | Bollinger Bands, ATR |
| 5 | **Technical Indicators** | 중간 | Paper 1, 3 | D-5, D-20 | RSI, MACD, Stochastic |
| 6 | **Sentiment Analysis** | 중간-낮음 | Paper 5 | D-1 | 뉴스/SNS 센티먼트 (보조 지표) |
| 7 | **Fundamental Factors** | 낮음 | Paper 2 | D-30+ | PER/PBR 등 (단기 예측에 부적합) |

### B. 시간 프레임별 Feature 효과성

| 시간 프레임 | 가장 중요한 Feature | 두 번째 중요한 Feature | 비고 |
|-----------|-------------------|---------------------|------|
| **당일 (Intraday)** | 시가/고가/저가 | Volume patterns | 고빈도 거래 맥락 |
| **D+1 (익일)** | Close price, Momentum | Volume z-score | 가장 많이 연구된 시간 프레임 |
| **D+1 ~ D+7** | Momentum indicators | STreversal | 단기 반전 효과 |
| **D+7 ~ D+30** | Volatility measures | Investor Sentiment | 정확도 하락 시작 |
| **D+30+** | Fundamental factors | Macroeconomic vars | 중장기 예측 영역 |

### C. 거래량(Volume) 관련 중요 발견

**Paper 2 (2020):**
- 미국 시장(S&P 500, DJI): 거래량이 **예측 성능 향상에 효과 없음**

**Paper 1 (2024):**
- 기본 모델에서 Volume z-score: **17.4%** 중요도
- RSI 추가 시 Volume 중요도: **14.4%**로 감소

**Paper 4 (2023):**
- Trading Fractions(거래량 패턴): Momentum과 함께 **가장 중요한 변수** 중 하나

**결론:**
- 단순 거래량보다 **거래량 패턴(Trading Fractions, Volume z-score)**이 효과적
- 시장 및 예측 목표에 따라 효과성이 다름
- **한국 시장에서는 거래량이 더 중요할 가능성** (유동성 차이)

---

## 3. 권장 점수 체계

### A. Morning Report용 가중치 (단기 예측 최적화)

학술 연구 결과를 종합하여 다음 가중치를 권장합니다:

| 요소 | 가중치 | 근거 | 세부 지표 |
|-----|-------|------|---------|
| **Momentum** | **35%** | Paper 1, 4에서 가격 변화율이 가장 중요 | - D-1 수익률 (15%)<br>- D-5 수익률 (10%)<br>- D-20 수익률 (10%) |
| **Volume & Trading Patterns** | **25%** | Paper 1의 17.4%, Paper 4의 Trading Fractions | - 거래량 증가율 (10%)<br>- 거래대금/시총 비율 (8%)<br>- Volume z-score (7%) |
| **Technical Indicators** | **20%** | Paper 1의 RSI 15.5%, 보조 지표로 활용 | - RSI (7%)<br>- MACD (7%)<br>- Stochastic (6%) |
| **Volatility** | **10%** | Paper 3, 리스크 관리 목적 | - Bollinger Bands %B (5%)<br>- ATR (5%) |
| **Sentiment** | **10%** | Paper 5의 25% 가중치, 보조적 활용 | - 뉴스 센티먼트 (5%)<br>- 공시 이벤트 (5%) |
| **Fundamental** | **0%** | 단기 예측에 부적합 | Morning Report에서 제외 |

**Total:** 100%

### B. Company Analysis용 가중치 (중장기 투자)

Morning Report와 차별화를 위해 다음 가중치를 권장합니다:

| 요소 | 가중치 | 근거 | 세부 지표 |
|-----|-------|------|---------|
| **Fundamental Analysis** | **40%** | 중장기에서는 펀더멘털이 핵심 | - 재무제표 분석 (20%)<br>- 밸류에이션 (PER/PBR) (15%)<br>- 성장성 (5%) |
| **Industry & Competition** | **20%** | 업종 트렌드, 경쟁 우위 | - 업종 동향 (10%)<br>- 시장 점유율 (5%)<br>- 경쟁사 비교 (5%) |
| **Momentum (장기)** | **15%** | 중기 추세 | - D-60 수익률 (8%)<br>- D-120 수익률 (7%) |
| **Sentiment** | **15%** | 중장기 심리 변화 | - 애널리스트 의견 (8%)<br>- 뉴스 트렌드 (7%) |
| **Technical Indicators** | **10%** | 보조 지표 | - 이동평균선 (5%)<br>- 추세선 (5%) |

**Total:** 100%

### C. 가중치 적용 예시 (Morning Report)

**종목: 삼성전자 (005930)**

| 요소 | 지표 | 측정값 | 정규화 점수 (0-1) | 가중치 | 최종 점수 |
|-----|------|--------|----------------|-------|---------|
| Momentum | D-1 수익률 | +3.2% | 0.85 | 15% | 0.1275 |
| | D-5 수익률 | +8.5% | 0.92 | 10% | 0.0920 |
| | D-20 수익률 | -2.1% | 0.35 | 10% | 0.0350 |
| **Momentum 소계** | | | | **35%** | **0.2545** |
| Volume | 거래량 증가율 | +45% | 0.78 | 10% | 0.0780 |
| | 거래대금/시총 | 2.3% | 0.65 | 8% | 0.0520 |
| | Volume z-score | 1.8 | 0.70 | 7% | 0.0490 |
| **Volume 소계** | | | | **25%** | **0.1790** |
| Technical | RSI | 68 | 0.58 | 7% | 0.0406 |
| | MACD | 긍정 크로스 | 0.75 | 7% | 0.0525 |
| | Stochastic | 72 | 0.60 | 6% | 0.0360 |
| **Technical 소계** | | | | **20%** | **0.1291** |
| Volatility | BB %B | 0.68 | 0.68 | 5% | 0.0340 |
| | ATR | 4.2% | 0.55 | 5% | 0.0275 |
| **Volatility 소계** | | | | **10%** | **0.0615** |
| Sentiment | 뉴스 센티먼트 | 긍정 70% | 0.70 | 5% | 0.0350 |
| | 공시 이벤트 | 신제품 발표 | 0.80 | 5% | 0.0400 |
| **Sentiment 소계** | | | | **10%** | **0.0750** |
| | | | | | |
| **전체 종합 점수** | | | | **100%** | **0.6991** |

**최종 점수: 69.91점 (100점 만점)**

---

## 4. Morning Report vs Company Analysis 차별화

### A. 핵심 차이점

| 구분 | Morning Report (단기 예측) | Company Analysis (중장기) |
|------|--------------------------|-------------------------|
| **목적** | "오늘/이번 주" 주목할 종목 발굴 | 투자 가치 판단, 목표가 설정 |
| **핵심 요소** | Momentum (35%) + Volume (25%) | Fundamental (40%) + Industry (20%) |
| **시간 프레임** | D-1, D-5, D-20 | D-60, D-120, 분기/연간 |
| **데이터 소스** | pykrx (실시간 시세, 거래량) | DART (재무제표), 애널리스트 리포트 |
| **기술적 지표** | 20% (RSI, MACD, Stochastic) | 10% (장기 이동평균, 추세선) |
| **센티먼트** | 10% (당일 뉴스, 공시 이벤트) | 15% (애널리스트 의견, 뉴스 트렌드) |
| **펀더멘털** | 0% (제외) | 40% (핵심) |
| **출력 형식** | Top 5-10 종목 리스트 + 간단한 사유 | 상세 분석 보고서 (5-10페이지) |
| **LLM 호출** | 1일 1회 (오전 8:30) | 요청 시 또는 배치 (캐싱 24시간) |
| **평가 기준** | D+1, D+7 수익률 | 목표가 달성률 (3-12개월) |

### B. 프롬프트 전략 차별화

#### Morning Report 프롬프트 구조

```python
MORNING_REPORT_PROMPT = """
당신은 한국 주식 시장의 **단기 트레이딩** 전문가입니다.

**오늘(2025-11-14) 장 시작 전, 투자자가 주목해야 할 종목 Top 5를 선정하세요.**

## 입력 데이터

### 1. 모멘텀 지표 (가중치 35%)
{momentum_data}

### 2. 거래량 패턴 (가중치 25%)
{volume_data}

### 3. 기술적 지표 (가중치 20%)
{technical_data}

### 4. 변동성 지표 (가중치 10%)
{volatility_data}

### 5. 당일 뉴스/공시 (가중치 10%)
{sentiment_data}

## 출력 형식

### 오늘의 주목 종목 Top 5

**1. [종목명] (종목코드)**
- **종합 점수**: XX점 / 100점
- **핵심 근거 (3가지)**:
  1. 모멘텀: ...
  2. 거래량: ...
  3. 기타: ...
- **진입 전략**: 시가 기준 ±X% 매수/매도
- **목표 수익률**: +X% (단기)
- **손절가**: -X%

(나머지 종목도 동일 형식)

## 주의사항
- 펀더멘털 분석은 **제외**하세요 (단기 예측에 부적합)
- **단기 모멘텀**과 **거래량 패턴**에 집중하세요
- 오늘/이번 주 이내 수익 실현 가능성이 높은 종목을 선정하세요
"""
```

#### Company Analysis 프롬프트 구조

```python
COMPANY_ANALYSIS_PROMPT = """
당신은 한국 주식 시장의 **장기 투자** 전문 애널리스트입니다.

**[{company_name}]의 투자 가치를 평가하고, 목표가를 제시하세요.**

## 입력 데이터

### 1. 재무 분석 (가중치 40%)
{financial_data}

### 2. 산업 및 경쟁 분석 (가중치 20%)
{industry_data}

### 3. 장기 모멘텀 (가중치 15%)
{longterm_momentum_data}

### 4. 애널리스트 의견 & 뉴스 트렌드 (가중치 15%)
{sentiment_data}

### 5. 기술적 분석 (가중치 10%)
{technical_data}

## 출력 형식

### 1. 투자 의견 요약
- **투자의견**: 강력 매수 / 매수 / 중립 / 매도 / 강력 매도
- **목표가**: XX,XXX원 (현재가 대비 +XX%)
- **투자 기간**: 3개월 / 6개월 / 12개월

### 2. 재무 분석 (40점)
- **수익성**: ROE XX%, 영업이익률 XX%
- **성장성**: 매출 YoY +XX%, 영업이익 YoY +XX%
- **안정성**: 부채비율 XX%, 유동비율 XX%
- **밸류에이션**: PER XX배 (업종 평균 대비), PBR XX배

### 3. 산업 및 경쟁 분석 (20점)
- **업종 전망**: ...
- **경쟁 우위**: ...
- **시장 점유율**: ...

### 4. 리스크 요인 (3가지)
1. ...
2. ...
3. ...

### 5. 투자 전략
- **단기 (1-3개월)**: ...
- **중기 (3-6개월)**: ...
- **장기 (6-12개월)**: ...

## 주의사항
- 단기 모멘텀보다 **장기 펀더멘털**에 집중하세요
- 재무제표와 업종 트렌드를 **깊이 있게** 분석하세요
- 3-12개월 관점의 **목표가**를 제시하세요
"""
```

### C. 평가 지표 차별화

| 지표 | Morning Report | Company Analysis |
|-----|---------------|------------------|
| **D+1 수익률** | 주요 지표 (가중치 40%) | 참고 지표 |
| **D+7 수익률** | 주요 지표 (가중치 30%) | 참고 지표 |
| **D+30 수익률** | 참고 지표 | 보조 지표 (가중치 20%) |
| **목표가 달성률** | 측정 안 함 | 주요 지표 (가중치 50%) |
| **승률 (Win Rate)** | 목표: 55%+ | 목표: 65%+ |
| **평균 수익률** | 목표: +3% (1주일) | 목표: +15% (6개월) |
| **샤프 비율** | 목표: 1.5+ | 목표: 1.2+ |
| **최대 손실** | -5% 이내 | -10% 이내 |

---

## 5. 추가 학술 연구 인사이트

### A. SHAP (SHapley Additive exPlanations) 활용

최신 연구(2024)에서는 SHAP 값을 사용하여 **해석 가능한 Feature Importance**를 측정합니다.

**주요 발견:**
- FinBERT 기반 센티먼트 특성이 **변동성 체제(volatility regime)**에 따라 중요도 변화
- 단기 예측에서 **상위 10개 특성**만으로도 충분한 성능
- 나머지 특성 제거 시 과적합 감소

**SKKU-INSIGHT 적용:**
- Morning Report 점수 계산 시 SHAP 값 활용 고려
- 특성 개수를 **10-15개로 제한**하여 과적합 방지

### B. 시장별 차이점

**미국 시장 (S&P 500, NASDAQ):**
- 거래량 단독으로는 효과 제한적
- 펀더멘털이 상대적으로 더 중요

**한국 시장 (KOSPI, KOSDAQ):**
- **거래량이 더 중요할 가능성** (유동성 차이)
- **개인/외국인/기관 순매수** 정보 활용 가능
- 뉴스 센티먼트가 더 즉각적으로 반영

**권장사항:**
- 한국 시장에서는 Volume 가중치를 **25% → 30%**로 상향 조정 고려
- 외국인/기관 순매수 데이터를 Volume 항목에 포함

### C. 과적합(Overfitting) 방지 전략

**Paper 1의 핵심 교훈:**
- Training R²: 0.812
- Testing R²: **-0.020** (실전에서 오히려 악화)

**원인:**
- 과도한 기술적 지표 사용
- 복잡한 모델 (Random Forest, XGBoost)

**SKKU-INSIGHT 적용:**
1. **특성 개수 제한**: 15개 이내
2. **단순한 가중 평균**: 복잡한 ML 모델 대신 Rule-based 점수화
3. **Out-of-sample 테스트**: 과거 데이터로 백테스팅 필수
4. **적응형 모델링**: 시장 체제(상승장/하락장/횡보장)별로 가중치 조정

### D. 거래량 관련 Best Practice

**효과적인 거래량 지표:**
1. **Volume z-score**: 평균 대비 표준편차 배수
   ```python
   z_score = (volume_today - volume_mean_20d) / volume_std_20d
   ```

2. **Trading Fractions**: 거래대금/시가총액 비율
   ```python
   trading_fraction = (price * volume) / market_cap
   ```

3. **On-Balance Volume (OBV)**: 누적 거래량
   ```python
   obv = obv_prev + (volume if close > close_prev else -volume)
   ```

**효과가 없는 지표:**
- 단순 절대 거래량 (시총 고려 안 함)
- 거래량 이동평균 단독

---

## 6. 실무 적용 가이드

### A. Morning Report 구현 체크리스트

- [ ] **데이터 수집** (오전 8:00)
  - [ ] pykrx로 D-1, D-5, D-20 종가 수집
  - [ ] 당일 시가, 거래량 수집 (09:05)
  - [ ] 네이버 금융 뉴스 크롤링 (전일 18:00 ~ 당일 08:00)

- [ ] **Metric 계산** (08:00-08:20)
  - [ ] Momentum 점수 (35%)
    - [ ] D-1 수익률 정규화
    - [ ] D-5 수익률 정규화
    - [ ] D-20 수익률 정규화
  - [ ] Volume 점수 (25%)
    - [ ] 거래량 증가율 계산
    - [ ] Volume z-score 계산
    - [ ] Trading Fraction 계산
  - [ ] Technical 점수 (20%)
    - [ ] RSI 계산
    - [ ] MACD 계산
    - [ ] Stochastic 계산
  - [ ] Volatility 점수 (10%)
    - [ ] Bollinger Bands %B 계산
    - [ ] ATR 계산
  - [ ] Sentiment 점수 (10%)
    - [ ] 뉴스 센티먼트 분석 (LLM)
    - [ ] 공시 이벤트 점수화

- [ ] **종합 점수 계산** (08:20-08:25)
  - [ ] 각 요소별 가중 평균
  - [ ] 상위 10개 종목 선정

- [ ] **LLM 리포트 생성** (08:25-08:30)
  - [ ] Morning Report 프롬프트에 데이터 입력
  - [ ] Gemini 2.5 Pro API 호출
  - [ ] 리포트 텍스트 생성

- [ ] **캐싱 및 저장** (08:30)
  - [ ] Redis에 리포트 저장 (TTL: 24시간)
  - [ ] DB에 추천 종목 기록 (평가용)

### B. 평가 시스템 구현

```python
# evaluation/morning_report_evaluator.py

class MorningReportEvaluator:
    def __init__(self, db_session):
        self.db = db_session

    def evaluate_daily_performance(self, report_date):
        """
        D+1 성과 평가

        Returns:
            {
                "date": "2025-11-14",
                "top5_avg_return": 0.032,  # 평균 3.2% 수익
                "win_rate": 0.60,  # 60% 승률
                "sharpe_ratio": 1.45,
                "max_loss": -0.038  # 최대 -3.8% 손실
            }
        """
        recommendations = self.db.query(
            DailyRecommendation
        ).filter_by(report_date=report_date).all()

        returns = []
        for rec in recommendations:
            # D+1 수익률 계산
            next_day_price = self.get_next_day_close(rec.ticker, report_date)
            return_rate = (next_day_price / rec.entry_price - 1)
            returns.append(return_rate)

        avg_return = np.mean(returns)
        win_rate = sum(1 for r in returns if r > 0) / len(returns)
        sharpe = self._calculate_sharpe(returns)
        max_loss = min(returns)

        return {
            "date": report_date,
            "top5_avg_return": avg_return,
            "win_rate": win_rate,
            "sharpe_ratio": sharpe,
            "max_loss": max_loss
        }

    def evaluate_weekly_performance(self, report_date):
        """
        D+7 성과 평가
        """
        # 유사한 로직으로 D+7 수익률 계산
        pass

    def evaluate_feature_importance(self, period_days=30):
        """
        각 Feature의 실제 예측력 평가

        Returns:
            {
                "momentum": {
                    "correlation": 0.45,  # 실제 수익률과 상관계수
                    "importance_rank": 1
                },
                "volume": {
                    "correlation": 0.32,
                    "importance_rank": 2
                },
                ...
            }
        """
        # 과거 30일 추천 종목의 Feature vs 실제 수익률 분석
        pass
```

### C. 가중치 자동 조정 (Adaptive Weighting)

```python
# backend/app/services/adaptive_weighting.py

class AdaptiveWeightingService:
    def __init__(self, evaluator):
        self.evaluator = evaluator
        self.base_weights = {
            "momentum": 0.35,
            "volume": 0.25,
            "technical": 0.20,
            "volatility": 0.10,
            "sentiment": 0.10
        }

    def adjust_weights_by_performance(self, lookback_days=30):
        """
        과거 성과 기반 가중치 자동 조정

        Args:
            lookback_days: 평가 기간 (일)

        Returns:
            adjusted_weights: 조정된 가중치 딕셔너리
        """
        # 각 Feature의 실제 예측력 평가
        feature_performance = self.evaluator.evaluate_feature_importance(
            period_days=lookback_days
        )

        # 상관계수 기반 가중치 재조정
        total_correlation = sum(
            abs(perf["correlation"])
            for perf in feature_performance.values()
        )

        adjusted_weights = {}
        for feature, base_weight in self.base_weights.items():
            correlation = abs(feature_performance[feature]["correlation"])
            # 기본 가중치 70% + 성과 기반 30%
            adjusted_weights[feature] = (
                base_weight * 0.7 +
                (correlation / total_correlation) * 0.3
            )

        # 정규화 (합계 1.0)
        total_weight = sum(adjusted_weights.values())
        adjusted_weights = {
            k: v / total_weight
            for k, v in adjusted_weights.items()
        }

        return adjusted_weights

    def adjust_weights_by_market_regime(self, market_regime):
        """
        시장 체제별 가중치 조정

        Args:
            market_regime: "bull" / "bear" / "sideways"

        Returns:
            regime_weights: 시장 체제에 맞는 가중치
        """
        if market_regime == "bull":
            # 상승장: 모멘텀 증가
            return {
                "momentum": 0.40,
                "volume": 0.25,
                "technical": 0.15,
                "volatility": 0.10,
                "sentiment": 0.10
            }
        elif market_regime == "bear":
            # 하락장: 변동성, 센티먼트 증가
            return {
                "momentum": 0.25,
                "volume": 0.20,
                "technical": 0.20,
                "volatility": 0.20,
                "sentiment": 0.15
            }
        else:  # sideways
            # 횡보장: 밸런스
            return self.base_weights
```

---

## 7. 결론 및 권장사항

### A. 핵심 요약

1. **단기 예측(D+1 ~ D+7)에서 가장 중요한 요소:**
   - **Momentum (35%)**: 가격 변화율이 가장 강력한 예측 변수
   - **Volume Patterns (25%)**: 거래량 패턴이 두 번째로 중요
   - **Technical Indicators (20%)**: 보조 지표로 활용

2. **기술적 지표의 한계:**
   - 과도한 사용 시 **과적합** 발생
   - 단순한 가격 기반 특성이 더 효과적

3. **센티먼트의 역할:**
   - 단독으로는 약하지만 기술적 지표와 결합 시 **5-10% 향상**
   - 적절한 가중치: **10-25%**

4. **거래량의 미묘한 역할:**
   - 미국 시장에서는 효과 제한적
   - 한국 시장에서는 더 중요할 가능성
   - **Volume z-score, Trading Fractions** 활용 권장

### B. SKKU-INSIGHT 적용 전략

#### Morning Report (단기 예측)
- Momentum (35%) + Volume (25%) 중심
- LLM 호출 최소화 (1일 1회)
- Rule-based 점수 계산 (과적합 방지)
- D+1, D+7 수익률로 평가

#### Company Analysis (중장기 투자)
- Fundamental (40%) + Industry (20%) 중심
- LLM 깊이 있는 분석 (캐싱 24시간)
- 목표가 달성률로 평가

#### 차별화 포인트
- 두 리포트의 **가중치가 정반대**
- 평가 기준이 명확히 다름
- 사용자가 단기/장기 관점을 선택 가능

### C. 다음 단계

1. **프로토타입 구현** (1-2주)
   - Rule-based 점수 계산 로직
   - Morning Report 프롬프트
   - 평가 시스템

2. **백테스팅** (2-3주)
   - 과거 6개월 데이터로 시뮬레이션
   - 가중치 최적화
   - 승률/샤프 비율 검증

3. **Adaptive Weighting** (3-4주)
   - 성과 기반 가중치 자동 조정
   - 시장 체제별 가중치 변경
   - A/B 테스트

4. **프론트엔드 통합** (4주)
   - 대시보드 UI
   - 리포트 뷰어
   - 성과 차트

---

## 8. 참고 문헌

### 주요 학술 논문

1. **Assessing the Impact of Technical Indicators on Machine Learning Models for Stock Price Prediction** (2024)
   - arXiv: 2412.15448v1
   - 핵심: 가격 기반 특성 > 기술적 지표

2. **Short-term Stock Market Price Trend Prediction Using Deep Learning** (2020)
   - Journal of Big Data, DOI: 10.1186/s40537-020-00333-6
   - 핵심: Feature Engineering의 중요성

3. **Deep Learning for Stock Market Prediction** (2020)
   - PMC: 7517440
   - 핵심: LSTM + 10개 기술적 지표

4. **Stock Return Prediction with Multiple Measures Using Neural Network Models** (2023)
   - Financial Innovation, DOI: 10.1186/s40854-023-00608-w
   - 핵심: Momentum + Trading Fractions

5. **Stock Trend Prediction Using Sentiment Analysis** (2023)
   - PMC: 10403218
   - 핵심: 센티먼트 25%, 기술적 75%

### 추가 참고 자료

6. **Survey of Feature Selection and Extraction Techniques for Stock Market Prediction** (2022)
   - Financial Innovation, DOI: 10.1186/s40854-022-00441-7

7. **Stock Market Prediction Using Machine Learning and Deep Learning Techniques: A Review** (2024)
   - MDPI: 2673-9909/5/3/76

8. **Random Forest and XGBoost for Stock Prediction** (2023)
   - ResearchGate: 369427968

9. **Ensemble Classifier for Stock Trading Recommendation** (2021)
   - Taylor & Francis: 10.1080/08839514.2021.2001178

10. **Stock Prediction Using SHAP and FinBERT** (2024)
    - MDPI Mathematics: 2227-7390/13/17/2747

---

**문서 작성일**: 2025-11-14
**작성자**: SKKU-INSIGHT Research Team
**버전**: 1.0
**다음 업데이트**: 백테스팅 결과 반영 (2025-11-28 예정)
