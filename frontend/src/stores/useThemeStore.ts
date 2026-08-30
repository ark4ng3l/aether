import { create } from 'zustand'

type ThemeMode = 'light' | 'dark' | 'system'

interface ThemeState {
  mode: ThemeMode
  resolved: 'light' | 'dark'
  setMode: (mode: ThemeMode) => void
}

function resolveTheme(mode: ThemeMode): 'light' | 'dark' {
  if (mode === 'system') {
    return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light'
  }
  return mode
}

function applyTheme(resolved: 'light' | 'dark') {
  const root = document.documentElement
  if (resolved === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

const storedMode = (typeof window !== 'undefined'
  ? (localStorage.getItem('aether_theme') as ThemeMode)
  : null) || 'dark'

const initialResolved = resolveTheme(storedMode)

// Apply on load
if (typeof window !== 'undefined') {
  applyTheme(initialResolved)
}

export const useThemeStore = create<ThemeState>((set) => ({
  mode: storedMode,
  resolved: initialResolved,

  setMode: (mode) => {
    const resolved = resolveTheme(mode)
    applyTheme(resolved)
    localStorage.setItem('aether_theme', mode)
    set({ mode, resolved })
  },
}))

// Listen for system theme changes when mode is 'system'
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const state = useThemeStore.getState()
    if (state.mode === 'system') {
      const resolved = resolveTheme('system')
      applyTheme(resolved)
      useThemeStore.setState({ resolved })
    }
  })
}
