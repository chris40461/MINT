// 참고: docs/frontend/01-setup.md

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 기본 색상
        border: '#e5e7eb',
        background: '#ffffff',
        foreground: '#111827',

        // 주식 색상
        bullish: {
          DEFAULT: '#ef4444', // 빨강 (한국 상승)
          light: '#fecaca',
        },
        bearish: {
          DEFAULT: '#3b82f6', // 파랑 (한국 하락)
          light: '#bfdbfe',
        },
        neutral: {
          DEFAULT: '#6b7280',
          light: '#d1d5db',
        },
      },
      fontFamily: {
        sans: ['Pretendard', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
        mono: ['D2Coding', 'Monaco', 'Courier New', 'monospace'],
      },
      animation: {
        'blob': 'blob 7s infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        blob: {
          '0%': {
            transform: 'translate(0px, 0px) scale(1)',
          },
          '33%': {
            transform: 'translate(30px, -50px) scale(1.1)',
          },
          '66%': {
            transform: 'translate(-20px, 20px) scale(0.9)',
          },
          '100%': {
            transform: 'translate(0px, 0px) scale(1)',
          },
        },
        float: {
          '0%, 100%': {
            transform: 'translateY(0px)',
          },
          '50%': {
            transform: 'translateY(-20px)',
          },
        },
      },
    },
  },
  plugins: [],
}
