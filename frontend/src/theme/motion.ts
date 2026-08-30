/**
 * AETHER Motion System v2
 * Centralized animation tokens. Respects prefers-reduced-motion globally.
 */

import { useEffect, useState } from 'react'

// ── Easing Curves ───────────────────────────────────────────────────────────

export const easing = {
  /** Entrance — ease-out-expo-ish (Raycast/Linear feel) */
  enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
  /** Exit — snappier, faster */
  exit: 'cubic-bezier(0.4, 0, 1, 1)',
  /** Smooth default for hover/interactive */
  smooth: 'cubic-bezier(0.25, 0.1, 0.25, 1)',
} as const

export const duration = {
  /** Fast exit animations */
  exit: 120,
  /** Standard entrance animations */
  enter: 180,
  /** Page/tab transitions */
  page: 150,
  /** Tooltip/hover feedback */
  fast: 100,
  /** Slower transitions (modal overlays) */
  slow: 240,
} as const

// Framer Motion transition presets
export const transition = {
  enter: { duration: duration.enter / 1000, ease: [0.16, 1, 0.3, 1] },
  exit: { duration: duration.exit / 1000, ease: [0.4, 0, 1, 1] },
  page: { duration: duration.page / 1000, ease: [0.16, 1, 0.3, 1] },
  spring: { type: 'spring' as const, stiffness: 400, damping: 30 },
} as const

// Common animation variants for Framer Motion
export const variants = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  slideUp: {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -4 },
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.98 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.98 },
  },
} as const

// ── Reduced Motion Hook ─────────────────────────────────────────────────────

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return reduced
}

/**
 * Returns duration of 0 if user prefers reduced motion, otherwise returns the given duration.
 */
export function motionSafe(ms: number, reduced: boolean): number {
  return reduced ? 0 : ms
}
