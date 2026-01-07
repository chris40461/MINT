# ML 기반 Presurge 감지 시스템 - 상세 설계 문서

## 목차
1. [개요](#1-개요)
2. [KIS API 분석](#2-kis-api-분석)
3. [Feature 설계](#3-feature-설계)
4. [시스템 아키텍처](#4-시스템-아키텍처)
5. [ML 핵심 과제 및 최신 연구 반영](#5-ml-핵심-과제-및-최신-연구-반영)
   - 5.8 [수익률 기반 평가 지표](#58-수익률-기반-평가-지표--new) ⭐ NEW
   - 5.9 [레이블 기준 최적화](#59-레이블-기준-최적화--new) ⭐ NEW
6. [구현 계획](#6-구현-계획)
   - 6.1.1 [WebSocket 재연결/장애 복구 전략](#611-websocket-재연결장애-복구-전략--new) ⭐ NEW
7. [모니터링 및 평가 시스템](#7-모니터링-및-평가-시스템)
8. [학술 레퍼런스](#8-학술-레퍼런스)

---

## 1. 개요

### 1.1 목표
- price-poller를 리팩토링하여 ML 기반 Presurge 감지 시스템 구축
- Daily Learning 파이프라인 구현
- REST API + WebSocket 병행 사용으로 최적의 실시간 데이터 수집

### 1.2 핵심 결정사항
| 항목 | 결정 |
|------|------|
| 레이블 기준 | 1시간 내 5% 이상 상승 |
| 학습 데이터 | 실시간 수집 (6개월 목표) |
| 학습 주기 | Daily (장 마감 후) |
| 작업 방식 | 새 branch에서 price-poller 리팩토링 |

---

## 2. KIS API 분석

### 2.1 API 유량 제한

```
┌─────────────────────────────────────────────────────┐
│                    REST API                          │
├─────────────────────────────────────────────────────┤
│ 실전투자: 1초당 20건 (계좌 단위)                     │
│ 모의투자: 1초당 2건                                  │
│ 토큰발급: 1초당 1건                                  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                    WebSocket                         │
├─────────────────────────────────────────────────────┤
│ 1세션, 총 41건 등록 가능                             │
│ (체결가 + 호가 + 예상체결 + 체결통보 합산)          │
│ ※ 2025년 9월 이후 60건으로 확대 예정                │
└─────────────────────────────────────────────────────┘
```

### 2.2 REST API 상세

#### 2.2.1 멀티종목 시세조회 (intstock_multprice)
```python
# TR ID: FHKST11300006
# Endpoint: /uapi/domestic-stock/v1/quotations/intstock-multprice
# 최대 30종목 동시 조회

응답 필드:
├── inter2_prpr         # 현재가
├── prdy_ctrt           # 전일대비율 (%)
├── acml_vol            # 누적 거래량
├── acml_tr_pbmn        # 누적 거래대금
├── inter2_oprc         # 시가
├── inter2_hgpr         # 고가
├── inter2_lwpr         # 저가
├── inter2_askp         # 매도호가
├── inter2_bidp         # 매수호가
├── total_askp_rsqn     # 총 매도호가 잔량
├── total_bidp_rsqn     # 총 매수호가 잔량
├── intr_antc_cntg_vrss # 예상 체결 대비 (동시호가)
└── intr_antc_vol       # 예상 거래량 (동시호가)
```

#### 2.2.2 호가/예상체결 조회 (inquire_asking_price_exp_ccn)
```python
# TR ID: FHKST01010200
# Endpoint: /uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn
# 1종목씩 조회 (10호가 상세)

응답 필드 (output1 - 호가정보):
├── askp1~askp10        # 매도호가 1~10차
├── bidp1~bidp10        # 매수호가 1~10차
├── askp_rsqn1~10       # 매도호가 잔량 1~10차
├── bidp_rsqn1~10       # 매수호가 잔량 1~10차
├── askp_rsqn_icdc1~10  # 매도호가 잔량 증감 1~10차
├── bidp_rsqn_icdc1~10  # 매수호가 잔량 증감 1~10차
├── total_askp_rsqn     # 총 매도호가 잔량
├── total_bidp_rsqn     # 총 매수호가 잔량
├── total_askp_rsqn_icdc # 총 매도호가 잔량 증감
└── total_bidp_rsqn_icdc # 총 매수호가 잔량 증감
```

### 2.3 WebSocket API 상세

#### 2.3.1 실시간 체결가 (H0STCNT0)
```python
# TR ID: H0STCNT0
# 구독: tr_type="1", 해제: tr_type="0"

응답 필드 (46개):
├── STCK_PRPR           # 주식 현재가
├── PRDY_CTRT           # 전일 대비율
├── CNTG_VOL            # 체결 거래량 (틱)
├── ACML_VOL            # 누적 거래량
├── ACML_TR_PBMN        # 누적 거래대금
├── CTTR                # ★ 체결강도
├── SELN_CNTG_CSNU      # 매도 체결 건수
├── SHNU_CNTG_CSNU      # 매수 체결 건수
├── NTBY_CNTG_CSNU      # 순매수 체결 건수
├── SELN_CNTG_SMTN      # 총 매도 수량
├── SHNU_CNTG_SMTN      # 총 매수 수량
├── CCLD_DVSN           # 체결구분 (1:매수, 5:매도)
├── SHNU_RATE           # ★ 매수비율
├── ASKP_RSQN1          # 매도호가 잔량1
├── BIDP_RSQN1          # 매수호가 잔량1
├── TOTAL_ASKP_RSQN     # 총 매도호가 잔량
├── TOTAL_BIDP_RSQN     # 총 매수호가 잔량
├── PRDY_VOL_VRSS_ACML_VOL_RATE  # 전일 거래량 대비율
└── PRDY_SMNS_HOUR_ACML_VOL_RATE # 전일 동시간 누적 거래량 비율
```

#### 2.3.2 실시간 호가 (H0STASP0)
```python
# TR ID: H0STASP0

응답 필드:
├── ASKP1~ASKP10        # 매도호가 1~10차
├── BIDP1~BIDP10        # 매수호가 1~10차
├── ASKP_RSQN1~10       # 매도호가 잔량 1~10차
├── BIDP_RSQN1~10       # 매수호가 잔량 1~10차
├── TOTAL_ASKP_RSQN     # 총 매도호가 잔량
├── TOTAL_BIDP_RSQN     # 총 매수호가 잔량
├── TOTAL_ASKP_RSQN_ICDC # 총 매도호가 잔량 증감
├── TOTAL_BIDP_RSQN_ICDC # 총 매수호가 잔량 증감
├── ANTC_CNPR           # 예상 체결가
├── ANTC_CNQN           # 예상 체결량
└── ANTC_VOL            # 예상 거래량
```

---

## 3. Feature 설계

### 3.1 Feature 매핑 (API → Feature)

| Feature | 공식 | 데이터 소스 | 우선순위 |
|---------|------|------------|----------|
| **OFI** | `(TOTAL_BIDP - TOTAL_ASKP) / (TOTAL_BIDP + TOTAL_ASKP)` | WS:H0STASP0 또는 REST:호가 | ★★★ |
| **체결강도** | `CTTR` (API 제공) | WS:H0STCNT0 | ★★★ |
| **Volume Ratio** | `현재거래량 / 5일평균거래량` | REST:multprice + 과거 계산 | ★★★ |
| **매수비율** | `SHNU_RATE` (API 제공) | WS:H0STCNT0 | ★★☆ |
| **순매수체결** | `SHNU_CNTG_SMTN - SELN_CNTG_SMTN` | WS:H0STCNT0 | ★★☆ |
| **전일동시간대비** | `PRDY_SMNS_HOUR_ACML_VOL_RATE` | WS:H0STCNT0 | ★★☆ |
| **호가잔량증감** | `TOTAL_BIDP_RSQN_ICDC` | WS:H0STASP0 | ★☆☆ |
| **Bid/Ask Spread** | `(ASKP1 - BIDP1) / BIDP1 * 100` | WS 또는 REST | ★☆☆ |

### 3.2 기술적 지표 (계산 필요)

| Feature | 공식 | Window |
|---------|------|--------|
| RSI_14 | 표준 RSI | 14일 |
| MACD_hist | MACD - Signal | 26일 |
| BB_position | (Price - Lower) / (Upper - Lower) | 20일 |
| MA20_distance | (Price - MA20) / MA20 * 100 | 20일 |
| Volume_acceleration | 후반5분 / 전반5분 | 10분 |
| Price_momentum_5m | 5분간 가격 변화율 | 5분 |

### 3.3 Feature 수집 전략

```
┌─────────────────────────────────────────────────────────────────┐
│                      데이터 수집 전략                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   REST API (전체 종목 커버리지)                                  │
│   ├── intstock_multprice: 30종목/호출, 0.5초 간격               │
│   ├── 300종목 = 10회 호출 = 5초 사이클                          │
│   └── 수집: 현재가, 거래량, 호가 총잔량, 등락률                  │
│                                                                  │
│   WebSocket (상위 종목 정밀 감시)                                │
│   ├── 상위 20종목 H0STCNT0 (체결가)                             │
│   ├── 상위 20종목 H0STASP0 (호가)                               │
│   └── 체결통보 1건 (총 41건 사용)                               │
│                                                                  │
│   동적 종목 교체                                                 │
│   ├── 5분마다 volume_ratio 상위 20종목 재선정                   │
│   └── 구독 해지 → 0.1초 대기 → 신규 구독                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 시스템 아키텍처

### 4.1 서비스 구조

```
price-poller/  (리팩토링 후)
├── app/
│   ├── main.py                    # 서비스 엔트리포인트
│   ├── config.py                  # 설정 (API 키, 임계값 등)
│   │
│   ├── clients/
│   │   ├── kis_rest_client.py     # REST API 클라이언트 (기존 유지)
│   │   ├── kis_websocket.py       # ★ WebSocket 클라이언트 (신규)
│   │   └── pykrx_client.py        # pykrx 래퍼 (기술적 지표용)
│   │
│   ├── collectors/
│   │   ├── rest_collector.py      # REST 데이터 수집기
│   │   ├── websocket_collector.py # ★ WebSocket 데이터 수집기 (신규)
│   │   └── feature_collector.py   # Feature 통합 수집기
│   │
│   ├── features/
│   │   ├── feature_store.py       # ★ 실시간 Feature 저장소 (신규)
│   │   ├── calculators/
│   │   │   ├── ofi.py             # OFI 계산
│   │   │   ├── volume.py          # 거래량 지표
│   │   │   └── technical.py       # 기술적 지표
│   │   └── pipeline.py            # Feature 계산 파이프라인
│   │
│   ├── ml/
│   │   ├── models/
│   │   │   ├── xgboost_model.py
│   │   │   ├── lightgbm_model.py
│   │   │   └── random_forest_model.py
│   │   ├── ensemble.py            # 앙상블 모델
│   │   ├── inference.py           # 실시간 추론
│   │   └── trainer.py             # 학습 파이프라인
│   │
│   ├── detection/
│   │   └── presurge_detector.py   # Presurge 감지 + 알림
│   │
│   ├── storage/
│   │   ├── feature_logger.py      # ★ Feature 히스토리 저장 (학습용)
│   │   └── database.py            # DB 연결
│   │
│   └── training/
│       ├── daily_labeler.py       # Daily 레이블링
│       └── daily_trainer.py       # Daily 학습 스케줄러
│
├── models/                        # 학습된 모델 저장
└── data/                          # Feature 히스토리 (Parquet)
```

### 4.2 데이터 흐름

```
                    ┌──────────────────────────────────────┐
                    │           KIS API 서버               │
                    └──────────────────────────────────────┘
                              │            │
              ┌───────────────┘            └───────────────┐
              ▼                                            ▼
    ┌─────────────────────┐                 ┌─────────────────────┐
    │     REST API        │                 │     WebSocket       │
    │  (전체 종목 폴링)   │                 │  (상위 20종목)      │
    │  30종목/0.5초       │                 │  실시간 Push        │
    └─────────┬───────────┘                 └─────────┬───────────┘
              │                                       │
              └───────────────┬───────────────────────┘
                              ▼
              ┌───────────────────────────────┐
              │        Feature Store          │
              │   (메모리 캐시 + Rolling)     │
              │   ┌─────────────────────────┐ │
              │   │ ticker → TickerFeature  │ │
              │   │ - current_price         │ │
              │   │ - volume                │ │
              │   │ - ofi                   │ │
              │   │ - cttr (체결강도)       │ │
              │   │ - feature_vector        │ │
              │   └─────────────────────────┘ │
              └───────────────┬───────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │ ML 추론    │    │ Feature     │    │ DB 저장    │
  │ (매 사이클) │    │ Logger      │    │ (realtime  │
  │            │    │ (학습용)    │    │  _prices)   │
  └──────┬──────┘    └─────────────┘    └─────────────┘
         │
         ▼
  ┌─────────────────────────────────┐
  │        Presurge Detector        │
  │   threshold >= 0.7 → 알림      │
  └─────────────────────────────────┘
```

### 4.3 Daily Learning 파이프라인

```
┌─────────────────────────────────────────────────────────────────┐
│                    Daily Learning Cycle                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   09:00-15:30 (장중)                                            │
│   ├── REST Polling + WebSocket 수신                              │
│   ├── Feature 계산 및 저장 (feature_history.parquet)            │
│   ├── ML 추론 (기존 모델 사용)                                   │
│   └── Presurge 감지 시 알림                                      │
│                                                                  │
│   15:30-16:00 (장 마감 후)                                       │
│   ├── 당일 Feature 데이터 확정                                   │
│   └── 레이블링 준비                                              │
│                                                                  │
│   16:00-17:00 (Labeling + Training)                             │
│   ├── 1시간 전 데이터에 대해 레이블 확정                         │
│   │   └── 1시간 후 최고가 >= 5% 상승? → label=1                 │
│   ├── 최근 30일 데이터 로드 (Sliding Window)                    │
│   ├── XGBoost + LightGBM + RandomForest 학습                    │
│   ├── 앙상블 가중치 최적화                                       │
│   ├── 모델 평가 (AUC, Precision, Recall)                        │
│   └── 새 모델 저장 (models/presurge_vN/)                        │
│                                                                  │
│   17:00 (모델 배포)                                              │
│   └── 다음 날 장 시작 전 새 모델 로드                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. ML 핵심 과제 및 최신 연구 반영

### 5.0 주요 도전 과제 (2024-2025 최신 연구 기반)

#### 5.0.1 Class Imbalance 문제

Presurge는 희소 이벤트(예상 5-10%)로 심각한 클래스 불균형 발생.

**최신 해결책** ([Comparative Analysis of Resampling Techniques, 2024](https://www.mdpi.com/2227-7390/13/13/2186)):
```python
# 권장 전략: SMOTE-Tomek 또는 Dirichlet ExtSMOTE
from imblearn.combine import SMOTETomek
from imblearn.over_sampling import SMOTE

class ImbalanceHandler:
    """
    Class Imbalance 처리 전략
    - SMOTE: F1 0.73, MCC 0.70 달성 (XGBoost 기준)
    - SMOTE-Tomek: Recall 향상, Precision 소폭 감소
    - Borderline-SMOTE: 경계선 샘플 집중 생성
    """
    def __init__(self, strategy='smote_tomek'):
        self.strategy = strategy

    def resample(self, X, y):
        if self.strategy == 'smote_tomek':
            sampler = SMOTETomek(random_state=42)
        elif self.strategy == 'borderline':
            sampler = SMOTE(kind='borderline1', random_state=42)
        else:
            sampler = SMOTE(random_state=42)
        return sampler.fit_resample(X, y)

# 주의: 변수 선택 후 SMOTE 적용 권장 (고차원 데이터)
```

#### 5.0.2 Concept Drift 대응

주식 시장은 비정상적(non-stationary)이며 시간에 따라 패턴이 변화함.

**최신 해결책** ([Proceed Framework, KDD 2025](https://arxiv.org/html/2412.08435), [MetaDA, 2024](https://arxiv.org/html/2401.03865)):
```python
class ConceptDriftHandler:
    """
    Concept Drift 대응 전략

    1. Proceed 방식: 테스트 샘플 도착 전 proactive하게 파라미터 조정
    2. MetaDA 방식: 메타러닝 기반 점진적 학습 (예측/비예측 드리프트 모두 처리)
    3. Time Weight: 최근 데이터에 더 높은 가중치 부여
    """
    def __init__(self, decay_factor=0.95):
        self.decay_factor = decay_factor
        self.drift_detector = None

    def apply_time_weight(self, X, y, timestamps):
        """시간 가중치 적용 - 최근 데이터 강조"""
        days_ago = (timestamps.max() - timestamps).dt.days
        weights = self.decay_factor ** days_ago
        return weights

    def detect_drift(self, recent_metrics, historical_metrics):
        """드리프트 감지 - ADWIN 또는 성능 저하 기반"""
        performance_drop = historical_metrics['auc'] - recent_metrics['auc']
        if performance_drop > 0.05:  # 5% 이상 성능 저하
            return True, 'performance_degradation'
        return False, None
```

#### 5.0.3 Simulation-to-Reality Gap

최신 연구에서 LOB 기반 DL 모델들이 시뮬레이션에서 **F1 88%+** 달성하지만, 실제 시장에서는 성능 저하 발생 ([LOBCAST Benchmark, 2024](https://arxiv.org/html/2308.01915)).

**대응 전략**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│                  Simulation-to-Reality Gap 대응                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. Walk-Forward Validation                                            │
│      └── 시간 순서 유지, 미래 데이터 누출 방지                            │
│                                                                          │
│   2. 거래 비용 반영                                                      │
│      ├── 슬리피지 (0.1% 가정)                                           │
│      ├── 수수료 (0.015% 가정)                                           │
│      └── 호가 스프레드 영향                                              │
│                                                                          │
│   3. 실시간 지연 시뮬레이션                                              │
│      └── API 응답 지연 (평균 50ms) 반영                                  │
│                                                                          │
│   4. 점진적 모델 도입                                                    │
│      ├── Shadow Mode: 실거래 없이 예측만 기록                            │
│      ├── Paper Trading: 가상 자금으로 시뮬레이션                         │
│      └── Live Trading: 소액으로 시작 후 확대                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 5.0.4 Deep Learning 모델 고려 (선택적 확장)

최신 LOB 기반 딥러닝 모델들 ([DeepLOB](https://arxiv.org/pdf/2308.01915), [TLOB](https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/)):

| 모델 | 특징 | 장점 | 단점 |
|------|------|------|------|
| **DeepLOB** | CNN + LSTM | 시공간 패턴 캡처 | 학습 시간 길음 |
| **TLOB** | Transformer + Dual Attention | 장기 의존성, 변동성 대응 | GPU 필요 |
| **현재 선택: 앙상블** | XGBoost + LightGBM + RF | 빠른 학습, 해석 가능 | 시계열 패턴 제한적 |

**권장**: 1단계는 앙상블로 시작, 데이터 축적 후 DeepLOB/TLOB 도입 검토

---

## 5.1 ML 최적화 대상 (What ML Actually Learns)

### 5.1 최적화 대상 요약

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ML이 학습/최적화하는 것들                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Level 1: 개별 모델 파라미터 (Hyperparameter Tuning)                   │
│   ├── XGBoost: n_estimators, max_depth, learning_rate, subsample, ...  │
│   ├── LightGBM: num_leaves, max_depth, learning_rate, ...              │
│   └── RandomForest: n_estimators, max_depth, min_samples_split, ...    │
│                                                                          │
│   Level 2: 앙상블 가중치 최적화                                          │
│   ├── 방법 A: Grid Search over weight combinations                      │
│   └── 방법 B: Stacking Meta-learner (LogisticRegression/XGBoost)       │
│                                                                          │
│   Level 3: Decision Threshold 최적화                                    │
│   ├── Precision-Recall Curve 분석                                       │
│   ├── F1-score 최대화 지점 탐색                                         │
│   └── 사용자 정의 목표 (예: Precision ≥ 0.7)                            │
│                                                                          │
│   Level 4: Feature Selection (선택적)                                   │
│   ├── Feature Importance 기반 선택                                      │
│   └── Recursive Feature Elimination (RFE)                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Level 1: 개별 모델 하이퍼파라미터

#### XGBoost 탐색 범위
```python
xgb_param_space = {
    'n_estimators': [100, 200, 300, 500],
    'max_depth': [3, 5, 7, 9],
    'learning_rate': [0.01, 0.05, 0.1, 0.2],
    'min_child_weight': [1, 3, 5],
    'subsample': [0.7, 0.8, 0.9, 1.0],
    'colsample_bytree': [0.7, 0.8, 0.9, 1.0],
    'gamma': [0, 0.1, 0.2],
    'scale_pos_weight': [1, 5, 10, 20],  # Class imbalance 처리
}
```

#### LightGBM 탐색 범위
```python
lgb_param_space = {
    'n_estimators': [100, 200, 300, 500],
    'num_leaves': [15, 31, 63, 127],
    'max_depth': [-1, 5, 7, 10],
    'learning_rate': [0.01, 0.05, 0.1],
    'min_child_samples': [10, 20, 30, 50],
    'subsample': [0.7, 0.8, 0.9],
    'colsample_bytree': [0.7, 0.8, 0.9],
    'class_weight': ['balanced', None],
}
```

#### RandomForest 탐색 범위
```python
rf_param_space = {
    'n_estimators': [100, 200, 300],
    'max_depth': [5, 10, 15, 20, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2', 0.5],
    'class_weight': ['balanced', 'balanced_subsample', None],
}
```

### 5.3 Level 2: 앙상블 가중치 최적화

#### 방법 A: Grid Search (가중치 직접 탐색)
```python
def optimize_ensemble_weights(models: dict, X_val, y_val):
    """
    가중치 조합 탐색 (합 = 1.0)
    """
    best_weights = None
    best_auc = 0

    # 0.1 단위로 모든 조합 탐색
    for w_xgb in np.arange(0.1, 0.9, 0.1):
        for w_lgb in np.arange(0.1, 0.9 - w_xgb, 0.1):
            w_rf = round(1.0 - w_xgb - w_lgb, 1)
            if w_rf < 0.1:
                continue

            weights = {'xgboost': w_xgb, 'lightgbm': w_lgb, 'random_forest': w_rf}

            # 가중 평균 확률 계산
            proba = sum(
                models[name].predict_proba(X_val)[:, 1] * w
                for name, w in weights.items()
            )

            auc = roc_auc_score(y_val, proba)
            if auc > best_auc:
                best_auc = auc
                best_weights = weights

    return best_weights  # 예: {'xgboost': 0.5, 'lightgbm': 0.3, 'random_forest': 0.2}
```

#### 방법 B: Stacking Meta-learner (더 정교한 방법)
```python
class StackingEnsemble:
    """
    Meta-learner가 개별 모델 출력을 학습하여 최종 예측
    """
    def __init__(self):
        self.base_models = {
            'xgboost': XGBClassifier(...),
            'lightgbm': LGBMClassifier(...),
            'random_forest': RandomForestClassifier(...)
        }
        # Meta-learner: 개별 모델 확률을 입력으로 받아 최종 예측
        self.meta_learner = LogisticRegression()

    def fit(self, X_train, y_train):
        # Step 1: K-Fold로 base model 학습 및 OOF 예측 생성
        oof_predictions = np.zeros((len(X_train), len(self.base_models)))

        kfold = StratifiedKFold(n_splits=5)
        for fold_idx, (train_idx, val_idx) in enumerate(kfold.split(X_train, y_train)):
            for model_idx, (name, model) in enumerate(self.base_models.items()):
                model.fit(X_train[train_idx], y_train[train_idx])
                oof_predictions[val_idx, model_idx] = model.predict_proba(X_train[val_idx])[:, 1]

        # Step 2: 전체 데이터로 base model 재학습
        for model in self.base_models.values():
            model.fit(X_train, y_train)

        # Step 3: Meta-learner 학습 (OOF 예측 → 실제 레이블)
        self.meta_learner.fit(oof_predictions, y_train)

    def predict_proba(self, X):
        # 각 모델의 확률 예측
        base_preds = np.column_stack([
            model.predict_proba(X)[:, 1]
            for model in self.base_models.values()
        ])
        # Meta-learner로 최종 확률 예측
        return self.meta_learner.predict_proba(base_preds)[:, 1]
```

### 5.4 Level 3: Decision Threshold 최적화

```python
def optimize_threshold(y_true, y_proba, strategy='f1_max'):
    """
    최적 임계값 탐색

    strategy:
    - 'f1_max': F1-score 최대화 (Balanced)
    - 'precision_target': 목표 Precision 달성 (예: ≥0.7)
    - 'recall_target': 목표 Recall 달성 (예: ≥0.8)
    - 'youden_j': Youden's J statistic (TPR - FPR 최대화)
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_proba)

    if strategy == 'f1_max':
        # F1 = 2 * (precision * recall) / (precision + recall)
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
        best_idx = np.argmax(f1_scores)
        best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5

    elif strategy == 'precision_target':
        target_precision = 0.7
        # Precision >= target인 최소 threshold
        valid_idx = np.where(precisions >= target_precision)[0]
        if len(valid_idx) > 0:
            best_idx = valid_idx[-1]  # 가장 낮은 threshold (highest recall)
            best_threshold = thresholds[best_idx] if best_idx < len(thresholds) else 0.5
        else:
            best_threshold = 0.9  # Fallback

    elif strategy == 'youden_j':
        fpr, tpr, roc_thresholds = roc_curve(y_true, y_proba)
        youden_j = tpr - fpr
        best_idx = np.argmax(youden_j)
        best_threshold = roc_thresholds[best_idx]

    return best_threshold  # 예: 0.65, 0.72, etc.
```

### 5.5 전체 최적화 파이프라인

```python
class DailyTrainer:
    def train(self, X, y):
        """
        Daily Learning: 모든 레벨 최적화 수행
        """
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, stratify=y
        )

        # ============================================
        # Level 1: 개별 모델 하이퍼파라미터 튜닝
        # ============================================
        print("Level 1: Hyperparameter Tuning...")

        # Optuna 또는 RandomizedSearchCV 사용
        best_xgb = self._tune_xgboost(X_train, y_train)
        best_lgb = self._tune_lightgbm(X_train, y_train)
        best_rf = self._tune_random_forest(X_train, y_train)

        models = {
            'xgboost': best_xgb,
            'lightgbm': best_lgb,
            'random_forest': best_rf
        }

        # ============================================
        # Level 2: 앙상블 가중치 최적화
        # ============================================
        print("Level 2: Ensemble Weight Optimization...")

        best_weights = optimize_ensemble_weights(models, X_val, y_val)
        # 결과 예: {'xgboost': 0.5, 'lightgbm': 0.3, 'random_forest': 0.2}

        # ============================================
        # Level 3: Decision Threshold 최적화
        # ============================================
        print("Level 3: Threshold Optimization...")

        # 앙상블 확률 계산
        ensemble_proba = sum(
            models[name].predict_proba(X_val)[:, 1] * w
            for name, w in best_weights.items()
        )

        best_threshold = optimize_threshold(y_val, ensemble_proba, strategy='f1_max')
        # 결과 예: 0.68

        # ============================================
        # 모델 저장 (학습된 모든 파라미터 포함)
        # ============================================
        model_artifact = {
            'models': models,
            'weights': best_weights,        # 학습된 앙상블 가중치
            'threshold': best_threshold,    # 학습된 임계값
            'feature_names': self.feature_names,
            'metrics': {
                'auc': roc_auc_score(y_val, ensemble_proba),
                'precision': precision_score(y_val, ensemble_proba >= best_threshold),
                'recall': recall_score(y_val, ensemble_proba >= best_threshold),
                'f1': f1_score(y_val, ensemble_proba >= best_threshold),
            },
            'trained_at': datetime.now().isoformat(),
        }

        self.save_model(model_artifact, f"models/presurge_{date.today()}/")

        return model_artifact
```

### 5.6 최적화 방법론 선택

| 탐색 방법 | 장점 | 단점 | 사용 시기 |
|-----------|------|------|-----------|
| **GridSearchCV** | 철저함, 재현 가능 | 시간 오래 걸림 | 파라미터 범위 좁을 때 |
| **RandomizedSearchCV** | 빠름, 넓은 범위 탐색 | 최적해 놓칠 수 있음 | 초기 탐색, 빠른 실험 |
| **Optuna (Bayesian)** | 효율적, 자동 조기종료 | 설정 복잡 | 프로덕션 Daily Learning |
| **Hyperopt** | TPE 알고리즘 | Optuna보다 느림 | 대안적 Bayesian 탐색 |

### 5.7 권장 구현 순서

```
1. 초기 (Cold Start) - 수동 설정
   ├── 모델 파라미터: 합리적인 기본값 사용
   ├── 앙상블 가중치: 균등 (0.33, 0.33, 0.34)
   └── Threshold: 0.5

2. 데이터 축적 후 (1-2주) - 자동 최적화 시작
   ├── RandomizedSearchCV로 빠른 탐색
   ├── 가중치 Grid Search
   └── Threshold F1 최적화

3. 안정화 후 (1개월+) - Optuna 전환
   ├── Bayesian Optimization으로 정교한 튜닝
   ├── 이전 모델 파라미터를 prior로 활용
   └── 시장 변화에 적응
```

### 5.8 수익률 기반 평가 지표 ⭐ NEW

분류 성능(AUC, Precision, Recall) 외에 **실제 거래 성과**를 측정하는 지표 추가.

**핵심 지표** ([Top 7 Metrics for Backtesting Results](https://www.luxalgo.com/blog/top-7-metrics-for-backtesting-results/), [QuantStart Sharpe Ratio](https://www.quantstart.com/articles/Sharpe-Ratio-for-Algorithmic-Trading-Performance-Measurement/)):

| 지표 | 공식 | 기준값 | 설명 |
|------|------|--------|------|
| **Profit Factor** | Gross Profit / Gross Loss | > 1.5 | 수익/손실 비율, 2.0+ 우수 |
| **Sharpe Ratio** | (Return - Rf) / σ | > 1.0 | 위험조정 수익률, 2.0+ 기관 수준 |
| **Max Drawdown** | Peak-to-Trough 최대 하락 | < 15% | 자본 보존 능력 |
| **Calmar Ratio** | Annual Return / MDD | > 2.0 | 하방 위험 대비 수익 |
| **Win Rate** | 수익 거래 / 전체 거래 | > 50% | 승률 (단독 사용 주의) |

```python
class TradingMetrics:
    """
    Presurge 감지 후 실제 성과 측정

    평가 시점: 감지 후 1시간 경과 시
    수익 계산: 감지가 시점 → 1시간 후 최고가 기준
    """
    def __init__(self):
        self.trades = []  # {ticker, entry_price, max_price_1h, return_pct}

    def add_trade(self, ticker, entry_price, max_price_1h):
        """감지 건 추가"""
        return_pct = (max_price_1h - entry_price) / entry_price * 100
        self.trades.append({
            'ticker': ticker,
            'entry_price': entry_price,
            'max_price_1h': max_price_1h,
            'return_pct': return_pct,
            'is_win': return_pct >= 5.0  # 목표 수익률 달성 여부
        })

    def profit_factor(self):
        """Profit Factor 계산"""
        profits = sum(t['return_pct'] for t in self.trades if t['return_pct'] > 0)
        losses = abs(sum(t['return_pct'] for t in self.trades if t['return_pct'] < 0))
        return profits / losses if losses > 0 else float('inf')

    def sharpe_ratio(self, risk_free_rate=0.035):
        """Sharpe Ratio 계산 (연율화)"""
        returns = [t['return_pct'] for t in self.trades]
        if len(returns) < 2:
            return 0.0
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        # 일간 → 연율화 (거래일 252일 기준)
        trades_per_day = len(returns) / 30  # 30일 기준
        annual_factor = np.sqrt(252 * trades_per_day)
        return (mean_return - risk_free_rate/252) / std_return * annual_factor if std_return > 0 else 0.0

    def max_drawdown(self):
        """Maximum Drawdown 계산"""
        cumulative = np.cumsum([t['return_pct'] for t in self.trades])
        peak = np.maximum.accumulate(cumulative)
        drawdown = (peak - cumulative)
        return np.max(drawdown) if len(drawdown) > 0 else 0.0

    def win_rate(self):
        """승률 계산"""
        wins = sum(1 for t in self.trades if t['is_win'])
        return wins / len(self.trades) if self.trades else 0.0

    def summary(self):
        """전체 성과 요약"""
        return {
            'total_trades': len(self.trades),
            'win_rate': f"{self.win_rate():.1%}",
            'profit_factor': f"{self.profit_factor():.2f}",
            'sharpe_ratio': f"{self.sharpe_ratio():.2f}",
            'max_drawdown': f"{self.max_drawdown():.1f}%",
            'avg_return': f"{np.mean([t['return_pct'] for t in self.trades]):.2f}%"
        }
```

**실시간 평가 + Daily Report에 통합**:
```python
# 7.3 AlertSystem의 send_daily_report 확장
async def send_daily_report(self, metrics, trading_metrics):
    message = f"""
📊 **일간 모델 리포트**
━━━━━━━━━━━━━━━━━━
[분류 성능]
오늘 감지: {metrics['detections']}건
정확도: {metrics['accuracy']:.1%}
AUC: {metrics['auc']:.3f}

[거래 성과]
승률: {trading_metrics['win_rate']}
Profit Factor: {trading_metrics['profit_factor']}
Sharpe Ratio: {trading_metrics['sharpe_ratio']}
Max Drawdown: {trading_metrics['max_drawdown']}
━━━━━━━━━━━━━━━━━━
    """
```

---

### 5.9 레이블 기준 최적화 ⭐ NEW

레이블 기준(5% 상승)의 적정성을 검증하고 최적화하는 방법.

**문제**: 레이블 기준이 너무 높으면 Positive 샘플 부족, 너무 낮으면 노이즈 포함.

**최신 연구** ([N-Period Volatility Labeling, 2024](https://onlinelibrary.wiley.com/doi/10.1155/2024/5036389), [GHOST Threshold Optimization](https://pubs.acs.org/doi/10.1021/acs.jcim.1c00160)):

```python
class LabelThresholdOptimizer:
    """
    레이블 기준 민감도 분석 및 최적화

    목표: 모델 성능과 샘플 수의 균형점 찾기
    """
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.results = []

    def analyze_thresholds(self, thresholds=[2.0, 3.0, 4.0, 5.0, 7.0, 10.0]):
        """다양한 threshold에서 레이블 분포 분석"""
        for threshold in thresholds:
            labels = self._create_labels(threshold)
            positive_ratio = labels.mean()
            positive_count = labels.sum()

            self.results.append({
                'threshold': threshold,
                'positive_ratio': positive_ratio,
                'positive_count': positive_count,
                'imbalance_ratio': f"1:{int(1/positive_ratio) if positive_ratio > 0 else 'inf'}"
            })

        return pd.DataFrame(self.results)

    def _create_labels(self, threshold_pct):
        """1시간 내 threshold% 이상 상승 시 label=1"""
        # max_price_1h와 current_price 컬럼 필요
        surge_rate = (self.data['max_price_1h'] - self.data['current_price']) / self.data['current_price'] * 100
        return (surge_rate >= threshold_pct).astype(int)

    def cross_validate_thresholds(self, thresholds, model_class):
        """
        각 threshold에서 모델 성능 교차 검증
        최적 threshold = AUC * sqrt(positive_count) 최대화
        """
        cv_results = []

        for threshold in thresholds:
            labels = self._create_labels(threshold)
            X = self.data[self.feature_columns]

            # 5-fold CV
            cv_scores = cross_val_score(
                model_class, X, labels,
                cv=StratifiedKFold(5),
                scoring='roc_auc'
            )

            cv_results.append({
                'threshold': threshold,
                'auc_mean': cv_scores.mean(),
                'auc_std': cv_scores.std(),
                'positive_count': labels.sum(),
                # 샘플 수와 성능의 균형 점수
                'balance_score': cv_scores.mean() * np.sqrt(labels.sum() / 1000)
            })

        return pd.DataFrame(cv_results)

    def recommend_threshold(self, cv_results):
        """최적 threshold 추천"""
        # balance_score 최대화
        best_idx = cv_results['balance_score'].idxmax()
        recommended = cv_results.loc[best_idx]

        print(f"권장 Threshold: {recommended['threshold']}%")
        print(f"  - AUC: {recommended['auc_mean']:.3f} ± {recommended['auc_std']:.3f}")
        print(f"  - Positive 샘플: {recommended['positive_count']}개")
        print(f"  - Balance Score: {recommended['balance_score']:.3f}")

        return recommended['threshold']
```

**권장 기준**:
| Positive Ratio | Imbalance | 권장 대응 |
|----------------|-----------|----------|
| > 10% | 1:9 | Threshold 상향 검토 (노이즈 가능성) |
| 5-10% | 1:10~20 | 적정 범위 |
| 2-5% | 1:20~50 | SMOTE 적용 필수 |
| < 2% | 1:50+ | Threshold 하향 또는 더 많은 데이터 수집 |

---

## 6. 구현 계획

### 6.1 Phase 1: WebSocket 클라이언트 구현

**목표**: KIS WebSocket API 연동

**파일**: `app/clients/kis_websocket.py`

```python
# 핵심 기능
class KISWebSocketClient:
    async def connect(self)                    # WebSocket 연결
    async def subscribe_ccnl(self, tickers)    # H0STCNT0 구독
    async def subscribe_asking(self, tickers)  # H0STASP0 구독
    async def unsubscribe(self, tickers)       # 구독 해제
    async def listen(self)                     # 메시지 수신 루프

# 콜백
    on_ccnl(ticker, data)      # 체결 데이터 수신
    on_asking_price(ticker, data)  # 호가 데이터 수신
```

**참조 코드**:
- `ccnl_krx.py` - H0STCNT0 구독 예제
- `asking_price_krx.py` - H0STASP0 구독 예제

#### 6.1.1 WebSocket 재연결/장애 복구 전략 ⭐ NEW

**문제**: 네트워크 끊김, 서버 오류 시 데이터 유실 및 서비스 중단 위험.

**최신 패턴** ([Exponential Backoff with Jitter](https://dev.to/hexshift/robust-websocket-reconnection-strategies-in-javascript-with-exponential-backoff-40n1), [Circuit Breaker Pattern](https://www.thebasictechinfo.com/node-js-frameworks/resilient-node-js-microservices-with-circuit-breakers-retries-and-rate-limiting-production-guide/)):

```python
from enum import Enum
import asyncio
import random

class CircuitState(Enum):
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 장애 감지, 연결 차단
    HALF_OPEN = "half_open"  # 복구 시도 중

class ResilientWebSocketClient:
    """
    Circuit Breaker + Exponential Backoff을 적용한 WebSocket 클라이언트

    참조: Helius CircuitBreakerWebSocket, DEV Community Best Practices
    """
    def __init__(self):
        # 재연결 설정
        self.base_delay = 1.0           # 초기 대기 시간 (초)
        self.max_delay = 60.0           # 최대 대기 시간
        self.max_retries = 10           # 최대 재시도 횟수
        self.jitter_factor = 0.3        # 랜덤 지터 (30%)

        # Circuit Breaker 설정
        self.failure_threshold = 5      # 연속 실패 시 회로 개방
        self.recovery_timeout = 30.0    # 복구 대기 시간 (초)

        # 상태
        self.circuit_state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_failure_time = None
        self.current_subscriptions = set()  # 구독 중인 종목

    async def connect_with_retry(self):
        """Exponential Backoff + Jitter 재연결"""
        retries = 0

        while retries < self.max_retries:
            try:
                if self.circuit_state == CircuitState.OPEN:
                    await self._check_circuit_recovery()

                await self._connect()
                self.consecutive_failures = 0
                self.circuit_state = CircuitState.CLOSED
                await self._resubscribe_all()  # 재구독
                return True

            except Exception as e:
                retries += 1
                self.consecutive_failures += 1
                self._update_circuit_state()

                # Exponential Backoff with Jitter
                delay = min(self.base_delay * (2 ** retries), self.max_delay)
                jitter = delay * self.jitter_factor * random.random()
                wait_time = delay + jitter

                logger.warning(
                    f"WebSocket 연결 실패 ({retries}/{self.max_retries}): {e}"
                    f" - {wait_time:.1f}초 후 재시도"
                )

                await asyncio.sleep(wait_time)

        logger.error("WebSocket 재연결 실패 - 최대 재시도 횟수 초과")
        return False

    def _update_circuit_state(self):
        """Circuit Breaker 상태 업데이트"""
        if self.consecutive_failures >= self.failure_threshold:
            self.circuit_state = CircuitState.OPEN
            self.last_failure_time = time.time()
            logger.warning("Circuit Breaker OPEN - WebSocket 연결 일시 중단")

    async def _check_circuit_recovery(self):
        """회로 복구 가능 여부 확인"""
        if self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.circuit_state = CircuitState.HALF_OPEN
                logger.info("Circuit Breaker HALF_OPEN - 복구 시도 중")

    async def _resubscribe_all(self):
        """연결 복구 후 이전 구독 복원"""
        if self.current_subscriptions:
            logger.info(f"재구독 시작: {len(self.current_subscriptions)}개 종목")
            for ticker in self.current_subscriptions:
                await self.subscribe_ccnl([ticker])
                await asyncio.sleep(0.1)  # Rate limit 준수
            logger.info("재구독 완료")

    async def graceful_degradation(self):
        """
        WebSocket 장애 시 REST API로 폴백

        전략:
        1. WebSocket 장애 감지
        2. REST API 폴링 간격 단축 (5초 → 1초)
        3. WebSocket 복구 시 원래 모드로 복귀
        """
        logger.warning("Graceful Degradation: REST API 폴백 모드 활성화")
        self.fallback_mode = True

        # REST API 폴링 간격 단축
        self.rest_polling_interval = 1.0  # 1초

        # 백그라운드에서 WebSocket 재연결 시도
        asyncio.create_task(self._background_reconnect())

    async def _background_reconnect(self):
        """백그라운드에서 주기적으로 재연결 시도"""
        while self.fallback_mode:
            await asyncio.sleep(self.recovery_timeout)
            if await self.connect_with_retry():
                self.fallback_mode = False
                self.rest_polling_interval = 5.0  # 원래 간격 복구
                logger.info("WebSocket 복구 완료 - 정상 모드 복귀")
                break
```

**Reconnection Storm 방지**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Reconnection Storm 방지 전략                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. Exponential Backoff                                                │
│      └── 1초 → 2초 → 4초 → 8초 → ... → 최대 60초                       │
│                                                                          │
│   2. Random Jitter (30%)                                                │
│      └── 동시 재연결 방지: delay * (1 + random(0, 0.3))                 │
│                                                                          │
│   3. Circuit Breaker                                                    │
│      ├── 5회 연속 실패 → OPEN (연결 시도 차단)                          │
│      ├── 30초 대기 → HALF_OPEN (복구 시도)                              │
│      └── 성공 → CLOSED (정상 운영)                                      │
│                                                                          │
│   4. Graceful Degradation                                               │
│      └── WebSocket 장애 시 REST API 폴백                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**구독 상태 관리**:
```python
# 연결 끊김 시 구독 상태 보존
self.current_subscriptions.add(ticker)

# 재연결 후 자동 재구독
await self._resubscribe_all()
```

### 6.2 Phase 2: Feature Store 구현

**목표**: 실시간 Feature 관리

**파일**: `app/features/feature_store.py`

```python
@dataclass
class TickerFeature:
    ticker: str
    # REST 데이터
    current_price: int
    volume: int
    change_rate: float
    total_bid_rsqn: int
    total_ask_rsqn: int

    # WebSocket 데이터 (상위 종목만)
    cttr: float = 0.0           # 체결강도
    shnu_rate: float = 0.0      # 매수비율
    bid_rsqn_list: List[int]    # 10호가 매수잔량
    ask_rsqn_list: List[int]    # 10호가 매도잔량

    # 계산된 Feature
    ofi: float = 0.0
    volume_ratio: float = 1.0

    # Rolling Window
    price_history_5m: deque
    volume_history_5m: deque
```

### 6.3 Phase 3: Feature Calculator 구현

**목표**: 논문 기반 Feature 계산

**파일**: `app/features/calculators/ofi.py`

```python
def calculate_ofi(total_bid: int, total_ask: int) -> float:
    """Order Flow Imbalance 계산"""
    if total_bid + total_ask == 0:
        return 0.0
    return (total_bid - total_ask) / (total_bid + total_ask)

# 범위: -1.0 (매도 우세) ~ +1.0 (매수 우세)
```

### 6.4 Phase 4: Feature Logger 구현

**목표**: 학습용 Feature 히스토리 저장

**파일**: `app/storage/feature_logger.py`

```python
# 저장 포맷: Parquet (압축, 빠른 읽기)
# 저장 주기: 매 10초 (폴링 사이클마다)
# 보관 기간: 30일 (Sliding Window)

columns = [
    'timestamp', 'ticker',
    'current_price', 'volume', 'change_rate',
    'ofi', 'cttr', 'volume_ratio', 'shnu_rate',
    'rsi_14', 'macd_hist', 'bb_position',
    # ... 기타 features
]
```

### 6.5 Phase 5: Daily Labeler 구현

**목표**: 자동 레이블링

**파일**: `app/training/daily_labeler.py`

```python
def label_presurge(df: pd.DataFrame,
                   time_window_hours: float = 1.0,
                   surge_threshold: float = 5.0) -> pd.DataFrame:
    """
    각 시점에서 1시간 후 최고가 확인
    최고가 상승률 >= 5% → label = 1
    """
```

### 6.6 Phase 6: ML 앙상블 구현

**목표**: Daily 학습 파이프라인

**파일**: `app/ml/ensemble.py`, `app/training/daily_trainer.py`

```python
# 앙상블 구성
models = {
    'xgboost': XGBClassifier(...),
    'lightgbm': LGBMClassifier(...),
    'random_forest': RandomForestClassifier(...)
}

# 가중치 (Grid Search로 최적화)
weights = {'xgboost': 0.4, 'lightgbm': 0.4, 'random_forest': 0.2}
```

### 6.7 Phase 7: 통합 및 테스트

**목표**: 전체 시스템 통합

```python
# main.py 구조
async def main():
    # 1. 인증
    await rest_client.get_access_token()
    await ws_client.connect()

    # 2. 모델 로드
    ensemble.load("models/presurge_v1/")

    # 3. 초기화
    await preload_avg_volumes()  # 5일 평균 거래량

    # 4. WebSocket 구독 (상위 20종목)
    top_tickers = await select_top_tickers()
    await ws_client.subscribe_ccnl(top_tickers)
    await ws_client.subscribe_asking(top_tickers)

    # 5. 메인 루프
    asyncio.gather(
        rest_polling_loop(),      # REST 폴링
        ws_client.listen(),       # WebSocket 수신
        inference_loop(),         # ML 추론
        dynamic_subscription(),   # 동적 구독 관리
    )
```

---

## 부록: 수정 대상 파일

### 기존 파일 (수정)
- `price-poller/app/main.py` - 통합 서비스로 확장
- `price-poller/app/config.py` - 설정 추가
- `price-poller/app/kis_rest_client.py` - 유지

### 신규 파일
- `price-poller/app/clients/kis_websocket.py`
- `price-poller/app/features/feature_store.py`
- `price-poller/app/features/pipeline.py`
- `price-poller/app/features/calculators/*.py`
- `price-poller/app/ml/ensemble.py`
- `price-poller/app/ml/inference.py`
- `price-poller/app/storage/feature_logger.py`
- `price-poller/app/training/daily_labeler.py`
- `price-poller/app/training/daily_trainer.py`
- `price-poller/app/detection/presurge_detector.py`

---

## 7. 모니터링 및 평가 시스템

### 7.1 실시간 모델 모니터링

```python
class ModelMonitor:
    """
    실시간 모델 성능 모니터링

    추적 지표:
    - 예측 분포 변화 (PSI: Population Stability Index)
    - Feature 분포 변화 (각 feature의 통계량)
    - 실시간 정확도 (1시간 후 평가)
    """
    def __init__(self, alert_threshold=0.05):
        self.alert_threshold = alert_threshold
        self.prediction_history = []
        self.accuracy_history = []

    def check_prediction_shift(self, recent_preds, baseline_preds):
        """PSI 계산 - 예측 분포 안정성 확인"""
        psi = self._calculate_psi(baseline_preds, recent_preds)
        if psi > 0.25:  # 큰 변화
            return 'ALERT', f'PSI={psi:.3f}'
        elif psi > 0.10:  # 중간 변화
            return 'WARNING', f'PSI={psi:.3f}'
        return 'OK', f'PSI={psi:.3f}'

    def track_accuracy(self, predicted, actual, timestamp):
        """정확도 추적 및 트렌드 분석"""
        accuracy = (predicted == actual).mean()
        self.accuracy_history.append({
            'timestamp': timestamp,
            'accuracy': accuracy,
            'n_samples': len(predicted)
        })

        # 7일 이동평균 vs 30일 이동평균 비교
        if len(self.accuracy_history) >= 30:
            recent_7d = np.mean([h['accuracy'] for h in self.accuracy_history[-7:]])
            baseline_30d = np.mean([h['accuracy'] for h in self.accuracy_history[-30:]])
            if baseline_30d - recent_7d > self.alert_threshold:
                return 'DEGRADATION', f'7d={recent_7d:.3f}, 30d={baseline_30d:.3f}'
        return 'OK', f'accuracy={accuracy:.3f}'
```

### 7.2 Walk-Forward Backtesting

```python
class WalkForwardBacktester:
    """
    Walk-Forward 백테스팅
    - 시간 순서 유지
    - 미래 데이터 누출 방지
    - 롤링 윈도우 재학습
    """
    def __init__(self, train_window=20, test_window=5):
        self.train_window = train_window  # 20 거래일
        self.test_window = test_window    # 5 거래일

    def run_backtest(self, data, model_class):
        results = []

        for start in range(0, len(data) - self.train_window - self.test_window,
                          self.test_window):
            # Train window
            train_end = start + self.train_window
            train_data = data[start:train_end]

            # Test window
            test_end = train_end + self.test_window
            test_data = data[train_end:test_end]

            # 모델 학습
            model = model_class()
            model.fit(train_data['X'], train_data['y'])

            # 예측 및 평가
            predictions = model.predict_proba(test_data['X'])
            metrics = self._evaluate(test_data['y'], predictions)

            results.append({
                'train_period': (start, train_end),
                'test_period': (train_end, test_end),
                **metrics
            })

        return pd.DataFrame(results)

    def _evaluate(self, y_true, y_proba):
        from sklearn.metrics import roc_auc_score, precision_score, recall_score
        threshold = 0.5  # 또는 최적화된 threshold
        y_pred = (y_proba >= threshold).astype(int)
        return {
            'auc': roc_auc_score(y_true, y_proba),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
        }
```

### 7.3 알림 시스템

```python
class AlertSystem:
    """
    텔레그램 기반 알림 시스템

    알림 유형:
    1. Presurge 감지 알림 (실시간)
    2. 모델 성능 저하 알림 (일간)
    3. Concept Drift 감지 알림 (일간)
    4. 시스템 오류 알림 (즉시)
    """
    ALERT_TYPES = {
        'presurge': '🚀 Presurge 감지',
        'model_degradation': '⚠️ 모델 성능 저하',
        'concept_drift': '🔄 Concept Drift 감지',
        'system_error': '🔴 시스템 오류',
    }

    async def send_presurge_alert(self, ticker, probability, features):
        message = f"""
🚀 **Presurge 감지**
━━━━━━━━━━━━━━━━━━
종목: {ticker}
확률: {probability:.1%}
체결강도: {features.get('cttr', 'N/A')}
OFI: {features.get('ofi', 'N/A'):.3f}
거래량비율: {features.get('volume_ratio', 'N/A'):.1f}x
━━━━━━━━━━━━━━━━━━
        """
        await self.telegram_bot.send_message(message)

    async def send_daily_report(self, metrics):
        message = f"""
📊 **일간 모델 리포트**
━━━━━━━━━━━━━━━━━━
오늘 감지: {metrics['detections']}건
정확도: {metrics['accuracy']:.1%}
AUC: {metrics['auc']:.3f}
드리프트 상태: {metrics['drift_status']}
━━━━━━━━━━━━━━━━━━
        """
        await self.telegram_bot.send_message(message)
```

---

## 8. 학술 레퍼런스

### 8.1 핵심 논문

| 주제 | 논문 | 연도 | 핵심 기여 |
|------|------|------|----------|
| **OFI** | Cont et al. "The Price Impact of Order Book Events" | 2014 | OFI가 가격 변동의 65% 설명력 |
| **LOB Deep Learning** | [LOB-Based Deep Learning Models Benchmark](https://arxiv.org/html/2308.01915) | 2024 | 15개 DL 모델 비교, LOBCAST 프레임워크 |
| **DeepLOB** | Zhang et al. "DeepLOB: Deep Convolutional Neural Networks for Limit Order Books" | 2019 | CNN+LSTM 기반 LOB 예측 |
| **TLOB** | [Deep Limit Order Book Forecasting](https://pmc.ncbi.nlm.nih.gov/articles/PMC12315853/) | 2025 | Transformer 기반 호가창 예측 |
| **Class Imbalance** | [Comparative Analysis of Resampling Techniques](https://www.mdpi.com/2227-7390/13/13/2186) | 2024 | SMOTE-Tomek 최적 성능 |
| **Concept Drift** | [Proceed: Proactive Model Adaptation](https://arxiv.org/html/2412.08435) | 2025 | 시계열 드리프트 선제 대응 |
| **MetaDA** | [Incremental Learning of Stock Trends](https://arxiv.org/html/2401.03865) | 2024 | 메타러닝 기반 점진적 학습 |
| **Anomaly Detection** | [Deep Unsupervised Anomaly Detection in HF Markets](https://www.sciencedirect.com/science/article/pii/S240591882400014X) | 2024 | 고빈도 시장 이상 탐지 |

### 8.2 Feature 이론적 근거

| Feature | 이론적 근거 | 선행 연구 |
|---------|------------|----------|
| **OFI (Order Flow Imbalance)** | 매수/매도 호가 불균형이 가격 방향성 예측 | Cont et al. (2014): R² = 0.65 |
| **체결강도 (CTTR)** | 매수 체결량 비율이 수급 우위 반영 | 한국시장 기술적 분석 지표 |
| **Volume Ratio** | 평균 대비 거래량 증가가 급등 선행 | Llorente et al. (2002) |
| **Bid/Ask Spread** | 유동성 지표, 좁을수록 거래 활발 | Market Microstructure Theory |
| **RSI** | 과매수/과매도 구간에서 반전 가능성 | Wilder (1978) |

### 8.3 한국시장 특수성

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    한국 주식시장 특수 고려사항                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   1. 거래시간                                                            │
│      ├── 정규시장: 09:00 - 15:30 (6.5시간)                              │
│      ├── 동시호가: 08:30-09:00, 15:20-15:30                             │
│      └── 시간외: 15:40-18:00                                            │
│                                                                          │
│   2. 가격제한폭                                                          │
│      └── ±30% (전일 종가 대비)                                          │
│                                                                          │
│   3. 공매도 제한                                                         │
│      └── 개인투자자 공매도 제한 → 상승 편향                             │
│                                                                          │
│   4. 외국인/기관 수급                                                    │
│      └── 대형주 영향력 큼 → 수급 Feature 중요                           │
│                                                                          │
│   5. VI (Volatility Interruption)                                       │
│      └── ±10% 변동 시 2분 거래 정지 → 급등 전 패턴 주의                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 부록: KIS API TR ID 정리

| 기능 | TR ID | 방식 |
|------|-------|------|
| REST 토큰 발급 | - | POST /oauth2/tokenP |
| WebSocket 접속키 | - | POST /oauth2/Approval |
| 멀티종목 시세 | FHKST11300006 | REST |
| 호가/예상체결 | FHKST01010200 | REST |
| 실시간 체결가 | H0STCNT0 | WebSocket |
| 실시간 호가 | H0STASP0 | WebSocket |
| 실시간 체결통보 | H0STCNI0 | WebSocket |

---

## 부록: 버전 히스토리

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2025-01-06 | 초기 설계 문서 작성 |
| v1.1 | 2025-01-06 | ML 최적화 대상 섹션 추가 |
| v1.2 | 2025-01-06 | 최신 연구 반영 (Class Imbalance, Concept Drift, LOB DL 모델) |
| v1.3 | 2025-01-06 | 모니터링/백테스팅 시스템, 학술 레퍼런스 추가 |
| v1.4 | 2025-01-06 | 수익률 기반 평가 지표(Sharpe, Profit Factor), 레이블 기준 최적화, WebSocket 재연결/Circuit Breaker 추가 |
