/**
 * AETHER Design System v2 — Token Definitions
 * Single source of truth for all visual tokens.
 * Consumed by tailwind.config.ts and directly by components.
 */

// ── Colors ──────────────────────────────────────────────────────────────────

export const colors = {
  dark: {
    bgCanvas: '#0b0d12',
    bgSurface: '#12151c',
    bgSurfaceRaised: '#191d26',
    bgOverlay: 'rgba(11,13,18,0.72)',
    borderSubtle: '#232834',
    borderStrong: '#323847',
    textPrimary: '#eef1f6',
    textSecondary: '#9aa4b2',
    textTertiary: '#5b6472',
  },
  light: {
    bgCanvas: '#f7f8fa',
    bgSurface: '#ffffff',
    bgSurfaceRaised: '#ffffff',
    bgOverlay: 'rgba(255,255,255,0.72)',
    borderSubtle: '#e6e8ec',
    borderStrong: '#d3d7de',
    textPrimary: '#14171c',
    textSecondary: '#5b6472',
    textTertiary: '#8b93a1',
  },
} as const

export const accent = {
  primary: '#4f9dff',
  primarySubtle: 'rgba(79,157,255,0.12)',
  primaryHover: '#6bb0ff',
  primaryActive: '#3a8af0',
} as const

export const status = {
  idle: '#6b7280',
  running: '#4f9dff',
  confirmed: '#16a34a',
  plausible: '#d97706',
  rejected: '#dc2626',
  critical: '#b91c1c',
} as const

// Confidence tier mapping
export const confidenceTier = {
  high: { color: status.confirmed, label: 'High', minScore: 0.75 },
  medium: { color: status.plausible, label: 'Medium', minScore: 0.45 },
  low: { color: status.rejected, label: 'Low', minScore: 0.0 },
} as const

export function getConfidenceTier(score: number) {
  if (score >= 0.75) return confidenceTier.high
  if (score >= 0.45) return confidenceTier.medium
  return confidenceTier.low
}

// ── Typography ──────────────────────────────────────────────────────────────

export const fontFamily = {
  sans: '"Inter", system-ui, -apple-system, sans-serif',
  mono: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace',
} as const

// 1.125 modular scale
export const fontSize = {
  '2xs': '0.75rem',     // 12px
  xs: '0.8438rem',      // 13.5px
  sm: '0.9375rem',      // 15px
  base: '1.0625rem',    // 17px
  lg: '1.1875rem',      // 19px
  xl: '1.5rem',         // 24px
  '2xl': '1.875rem',    // 30px
  '3xl': '2.375rem',    // 38px
} as const

export const fontWeight = {
  normal: '400',
  medium: '500',
  semibold: '600',
} as const

export const lineHeight = {
  body: '1.5',
  dense: '1.3',
  tight: '1.2',
} as const

// ── Spacing (4px base) ──────────────────────────────────────────────────────

export const spacing = {
  '1': '4px',
  '2': '8px',
  '3': '12px',
  '4': '16px',
  '5': '20px',
  '6': '24px',
  '8': '32px',
  '10': '40px',
  '12': '48px',
  '16': '64px',
} as const

// ── Radius ──────────────────────────────────────────────────────────────────

export const radius = {
  sm: '4px',     // chips, badges
  DEFAULT: '6px', // default
  lg: '10px',    // cards, modals
  full: '9999px',
} as const

// ── Elevation ───────────────────────────────────────────────────────────────

export const shadow = {
  sm: '0 1px 2px rgba(0,0,0,0.04)',
  DEFAULT: '0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.08)',
  lg: '0 2px 4px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.12)',
  overlay: '0 4px 16px rgba(0,0,0,0.16), 0 16px 48px rgba(0,0,0,0.24)',
} as const

// ── Icon sizes ──────────────────────────────────────────────────────────────

export const iconSize = {
  inline: 16,
  ui: 18,
  lg: 24,
} as const
