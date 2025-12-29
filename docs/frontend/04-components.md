# 재사용 가능한 컴포넌트 (Reusable Components)

## 📌 문서 목적

프로젝트 전반에서 재사용 가능한 공통 UI 컴포넌트 라이브러리를 정의합니다.

---

## 📁 디렉토리 구조

```
frontend/src/components/
├── common/                     # 공통 컴포넌트
│   ├── Button/
│   ├── Input/
│   ├── Card/
│   ├── Badge/
│   ├── Modal/
│   ├── Loading/
│   └── Error/
├── stock/                      # 주식 관련 컴포넌트
│   ├── StockCard/
│   ├── PriceDisplay/
│   ├── ChangeRate/
│   └── VolumeDisplay/
└── chart/                      # 차트 컴포넌트
    ├── LineChart/
    ├── CandlestickChart/
    └── BarChart/
```

---

## 🔘 Button 컴포넌트

```typescript
// components/common/Button/Button.tsx

import React from 'react';
import './Button.css';

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  className?: string;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  onClick,
  className = ''
}) => {
  return (
    <button
      className={`btn btn-${variant} btn-${size} ${className}`}
      disabled={disabled || loading}
      onClick={onClick}
    >
      {loading ? <Spinner /> : children}
    </button>
  );
};

const Spinner: React.FC = () => (
  <span className="spinner">⏳</span>
);
```

```css
/* Button.css */
.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary {
  background: #2196F3;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1976D2;
}

.btn-secondary {
  background: #757575;
  color: white;
}

.btn-danger {
  background: #FF4444;
  color: white;
}

.btn-success {
  background: #00C851;
  color: white;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 14px;
}

.btn-md {
  padding: 8px 16px;
  font-size: 16px;
}

.btn-lg {
  padding: 12px 24px;
  font-size: 18px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## 📇 Card 컴포넌트

```typescript
// components/common/Card/Card.tsx

interface CardProps {
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  children,
  footer,
  className = '',
  onClick
}) => {
  return (
    <div
      className={`card ${className} ${onClick ? 'clickable' : ''}`}
      onClick={onClick}
    >
      {(title || subtitle) && (
        <div className="card-header">
          {title && <h3 className="card-title">{title}</h3>}
          {subtitle && <p className="card-subtitle">{subtitle}</p>}
        </div>
      )}

      <div className="card-body">
        {children}
      </div>

      {footer && (
        <div className="card-footer">
          {footer}
        </div>
      )}
    </div>
  );
};
```

```css
/* Card.css */
.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}

.card.clickable {
  cursor: pointer;
}

.card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.card-subtitle {
  margin: 4px 0 0 0;
  font-size: 14px;
  color: #666;
}

.card-body {
  padding: 16px;
}

.card-footer {
  padding: 12px 16px;
  background: #f5f5f5;
  border-top: 1px solid #eee;
}
```

---

## 🏷️ Badge 컴포넌트

```typescript
// components/common/Badge/Badge.tsx

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md' | 'lg';
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md'
}) => {
  return (
    <span className={`badge badge-${variant} badge-${size}`}>
      {children}
    </span>
  );
};
```

```css
/* Badge.css */
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
  text-align: center;
}

.badge-default {
  background: #e0e0e0;
  color: #333;
}

.badge-success {
  background: #00C851;
  color: white;
}

.badge-warning {
  background: #FFBB33;
  color: #333;
}

.badge-danger {
  background: #FF4444;
  color: white;
}

.badge-info {
  background: #33B5E5;
  color: white;
}

.badge-sm {
  padding: 2px 8px;
  font-size: 12px;
}

.badge-md {
  padding: 4px 12px;
  font-size: 14px;
}

.badge-lg {
  padding: 6px 16px;
  font-size: 16px;
}
```

---

## 💰 StockCard 컴포넌트

```typescript
// components/stock/StockCard/StockCard.tsx

interface StockCardProps {
  ticker: string;
  name: string;
  currentPrice: number;
  changeRate: number;
  volume?: number;
  onClick?: () => void;
}

export const StockCard: React.FC<StockCardProps> = ({
  ticker,
  name,
  currentPrice,
  changeRate,
  volume,
  onClick
}) => {
  const isPositive = changeRate > 0;

  return (
    <Card className="stock-card" onClick={onClick}>
      <div className="stock-info">
        <div className="stock-name-section">
          <h3 className="stock-name">{name}</h3>
          <span className="stock-ticker">{ticker}</span>
        </div>

        <PriceDisplay
          price={currentPrice}
          changeRate={changeRate}
        />

        {volume && (
          <div className="volume-info">
            거래량: <VolumeDisplay volume={volume} />
          </div>
        )}
      </div>
    </Card>
  );
};
```

---

## 💵 PriceDisplay 컴포넌트

```typescript
// components/stock/PriceDisplay/PriceDisplay.tsx

interface PriceDisplayProps {
  price: number;
  changeRate?: number;
  changeAmount?: number;
  size?: 'sm' | 'md' | 'lg';
}

export const PriceDisplay: React.FC<PriceDisplayProps> = ({
  price,
  changeRate,
  changeAmount,
  size = 'md'
}) => {
  const isPositive = changeRate ? changeRate > 0 : changeAmount ? changeAmount > 0 : false;

  return (
    <div className={`price-display price-display-${size}`}>
      <div className="price-value">
        {price.toLocaleString()}원
      </div>

      {(changeRate !== undefined || changeAmount !== undefined) && (
        <div className={`price-change ${isPositive ? 'positive' : 'negative'}`}>
          {changeAmount !== undefined && (
            <span className="change-amount">
              {isPositive ? '+' : ''}{changeAmount.toLocaleString()}
            </span>
          )}
          {changeRate !== undefined && (
            <span className="change-rate">
              ({isPositive ? '+' : ''}{changeRate.toFixed(2)}%)
            </span>
          )}
          <span className="change-arrow">
            {isPositive ? '▲' : '▼'}
          </span>
        </div>
      )}
    </div>
  );
};
```

```css
/* PriceDisplay.css */
.price-display {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.price-value {
  font-weight: 700;
  color: #333;
}

.price-display-sm .price-value {
  font-size: 16px;
}

.price-display-md .price-value {
  font-size: 20px;
}

.price-display-lg .price-value {
  font-size: 28px;
}

.price-change {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
}

.price-change.positive {
  color: #FF4444;
}

.price-change.negative {
  color: #2196F3;
}
```

---

## 📊 VolumeDisplay 컴포넌트

```typescript
// components/stock/VolumeDisplay/VolumeDisplay.tsx

interface VolumeDisplayProps {
  volume: number;
  format?: 'short' | 'full';
}

export const VolumeDisplay: React.FC<VolumeDisplayProps> = ({
  volume,
  format = 'short'
}) => {
  const formatVolume = (vol: number): string => {
    if (format === 'full') {
      return vol.toLocaleString();
    }

    // 단위 변환 (M, K)
    if (vol >= 1_000_000) {
      return `${(vol / 1_000_000).toFixed(1)}M`;
    } else if (vol >= 1_000) {
      return `${(vol / 1_000).toFixed(1)}K`;
    }
    return vol.toString();
  };

  return (
    <span className="volume-display">
      {formatVolume(volume)}
    </span>
  );
};
```

---

## ⏳ Loading 컴포넌트

```typescript
// components/common/Loading/Loading.tsx

interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export const Loading: React.FC<LoadingProps> = ({
  size = 'md',
  text = '로딩 중...'
}) => {
  return (
    <div className={`loading loading-${size}`}>
      <div className="spinner" />
      {text && <p className="loading-text">{text}</p>}
    </div>
  );
};
```

```css
/* Loading.css */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.spinner {
  border: 4px solid #f3f3f3;
  border-top: 4px solid #2196F3;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-sm .spinner {
  width: 24px;
  height: 24px;
  border-width: 2px;
}

.loading-md .spinner {
  width: 40px;
  height: 40px;
  border-width: 4px;
}

.loading-lg .spinner {
  width: 60px;
  height: 60px;
  border-width: 6px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-text {
  margin-top: 16px;
  color: #666;
  font-size: 14px;
}
```

---

## 🔴 LoadingSkeleton 컴포넌트

```typescript
// components/common/Loading/LoadingSkeleton.tsx

interface LoadingSkeletonProps {
  type?: 'card' | 'table' | 'text' | 'chart';
  count?: number;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  type = 'card',
  count = 1
}) => {
  if (type === 'card') {
    return (
      <div className="skeleton-container">
        {Array.from({ length: count }).map((_, idx) => (
          <div key={idx} className="skeleton-card">
            <div className="skeleton-line skeleton-title" />
            <div className="skeleton-line skeleton-text" />
            <div className="skeleton-line skeleton-text short" />
          </div>
        ))}
      </div>
    );
  }

  if (type === 'table') {
    return (
      <div className="skeleton-table">
        {Array.from({ length: count }).map((_, idx) => (
          <div key={idx} className="skeleton-row">
            <div className="skeleton-cell" />
            <div className="skeleton-cell" />
            <div className="skeleton-cell" />
          </div>
        ))}
      </div>
    );
  }

  return <div className="skeleton-line" />;
};
```

```css
/* LoadingSkeleton.css */
.skeleton-line {
  height: 16px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

.skeleton-title {
  height: 24px;
  width: 60%;
  margin-bottom: 12px;
}

.skeleton-text {
  margin-bottom: 8px;
}

.skeleton-text.short {
  width: 40%;
}

.skeleton-card {
  padding: 16px;
  background: white;
  border-radius: 8px;
  margin-bottom: 16px;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

---

## ❌ Error 컴포넌트

```typescript
// components/common/Error/ErrorDisplay.tsx

interface ErrorDisplayProps {
  error: Error | string;
  onRetry?: () => void;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry
}) => {
  const errorMessage = typeof error === 'string' ? error : error.message;

  return (
    <div className="error-display">
      <div className="error-icon">⚠️</div>
      <h3 className="error-title">오류가 발생했습니다</h3>
      <p className="error-message">{errorMessage}</p>
      {onRetry && (
        <Button variant="primary" onClick={onRetry}>
          다시 시도
        </Button>
      )}
    </div>
  );
};
```

```css
/* ErrorDisplay.css */
.error-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.error-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.error-title {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
}

.error-message {
  font-size: 16px;
  color: #666;
  margin-bottom: 24px;
  max-width: 400px;
}
```

---

## 🪟 Modal 컴포넌트

```typescript
// components/common/Modal/Modal.tsx

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {title && (
          <div className="modal-header">
            <h2 className="modal-title">{title}</h2>
            <button className="modal-close" onClick={onClose}>
              ✕
            </button>
          </div>
        )}

        <div className="modal-body">
          {children}
        </div>

        {footer && (
          <div className="modal-footer">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};
```

```css
/* Modal.css */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #666;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #eee;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
```

---

## 📦 컴포넌트 익스포트

```typescript
// components/index.ts

// Common
export { Button } from './common/Button/Button';
export { Card } from './common/Card/Card';
export { Badge } from './common/Badge/Badge';
export { Modal } from './common/Modal/Modal';
export { Loading } from './common/Loading/Loading';
export { LoadingSkeleton } from './common/Loading/LoadingSkeleton';
export { ErrorDisplay } from './common/Error/ErrorDisplay';

// Stock
export { StockCard } from './stock/StockCard/StockCard';
export { PriceDisplay } from './stock/PriceDisplay/PriceDisplay';
export { VolumeDisplay } from './stock/VolumeDisplay/VolumeDisplay';
```

---

## 🎨 Storybook 설정 (선택사항)

```typescript
// .storybook/main.ts

export default {
  stories: ['../src/components/**/*.stories.tsx'],
  addons: ['@storybook/addon-essentials'],
  framework: '@storybook/react'
};
```

```typescript
// components/common/Button/Button.stories.tsx

import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'Common/Button',
  component: Button
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: {
    children: '버튼',
    variant: 'primary'
  }
};

export const Loading: Story = {
  args: {
    children: '로딩 중',
    loading: true
  }
};
```

---

**마지막 업데이트**: 2025-11-06
**작성자**: SKKU-INSIGHT 개발팀
