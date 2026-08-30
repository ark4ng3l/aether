import type { Config } from 'tailwindcss'
import { colors, accent, status, fontSize, fontFamily, spacing, radius, shadow } from './src/theme/tokens'

export default {
  darkMode: ['class'],
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          canvas: 'var(--bg-canvas)',
          surface: 'var(--bg-surface)',
          raised: 'var(--bg-surface-raised)',
          overlay: 'var(--bg-overlay)',
        },
        border: {
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
        },
        accent: {
          DEFAULT: accent.primary,
          subtle: accent.primarySubtle,
          hover: accent.primaryHover,
          active: accent.primaryActive,
        },
        status: {
          idle: status.idle,
          running: status.running,
          confirmed: status.confirmed,
          plausible: status.plausible,
          rejected: status.rejected,
          critical: status.critical,
        },
      },
      fontSize: {
        '2xs': [fontSize['2xs'], { lineHeight: '1.3' }],
        xs: [fontSize.xs, { lineHeight: '1.3' }],
        sm: [fontSize.sm, { lineHeight: '1.5' }],
        base: [fontSize.base, { lineHeight: '1.5' }],
        lg: [fontSize.lg, { lineHeight: '1.3' }],
        xl: [fontSize.xl, { lineHeight: '1.2' }],
        '2xl': [fontSize['2xl'], { lineHeight: '1.2' }],
        '3xl': [fontSize['3xl'], { lineHeight: '1.2' }],
      },
      fontFamily: {
        sans: [fontFamily.sans],
        mono: [fontFamily.mono],
      },
      spacing: {
        '1': spacing['1'],
        '2': spacing['2'],
        '3': spacing['3'],
        '4': spacing['4'],
        '5': spacing['5'],
        '6': spacing['6'],
        '8': spacing['8'],
        '10': spacing['10'],
        '12': spacing['12'],
        '16': spacing['16'],
      },
      borderRadius: {
        sm: radius.sm,
        DEFAULT: radius.DEFAULT,
        lg: radius.lg,
        full: radius.full,
      },
      boxShadow: {
        sm: shadow.sm,
        DEFAULT: shadow.DEFAULT,
        lg: shadow.lg,
        overlay: shadow.overlay,
      },
      transitionTimingFunction: {
        'ease-enter': 'cubic-bezier(0.16, 1, 0.3, 1)',
        'ease-exit': 'cubic-bezier(0.4, 0, 1, 1)',
      },
      transitionDuration: {
        '120': '120ms',
        '150': '150ms',
        '180': '180ms',
        '240': '240ms',
      },
      keyframes: {
        'pulse-dot': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          from: { opacity: '0', transform: 'scale(0.98)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'fade-in': 'fade-in 180ms cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-up': 'slide-up 150ms cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in': 'scale-in 120ms cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
} satisfies Config
