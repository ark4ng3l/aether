import { create } from 'zustand'

export interface LogEntry {
  id: string
  timestamp: string
  text: string
  type: 'token' | 'info' | 'warn' | 'error' | 'verdict'
}

type ViewMode = 'raw' | 'structured'

interface ConsoleState {
  logs: LogEntry[]
  isPaused: boolean
  viewMode: ViewMode
  addLog: (entry: Omit<LogEntry, 'id'>) => void
  bufferToken: (token: string, type?: LogEntry['type']) => void
  setIsPaused: (paused: boolean) => void
  setViewMode: (mode: ViewMode) => void
  clearLogs: () => void
}

let tokenBuffer: string[] = []
let rafId: number | null = null

export const useConsoleStore = create<ConsoleState>((set, get) => ({
  logs: [],
  isPaused: false,
  viewMode: 'structured',

  addLog: (entry) => {
    if (get().isPaused) return
    const newEntry: LogEntry = {
      ...entry,
      id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    }
    set((state) => ({
      logs: [...state.logs.slice(-500), newEntry],
    }))
  },

  bufferToken: (token: string, type: LogEntry['type'] = 'token') => {
    if (get().isPaused) return
    tokenBuffer.push(token)

    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        if (tokenBuffer.length > 0) {
          const combined = tokenBuffer.join('')
          tokenBuffer = []
          const newEntry: LogEntry = {
            id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            timestamp: new Date().toISOString().split('T')[1].slice(0, 8),
            text: combined,
            type,
          }
          set((state) => ({
            logs: [...state.logs.slice(-500), newEntry],
          }))
        }
        rafId = null
      })
    }
  },

  setIsPaused: (isPaused) => set({ isPaused }),
  setViewMode: (viewMode) => set({ viewMode }),
  clearLogs: () => {
    tokenBuffer = []
    if (rafId !== null) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    set({ logs: [] })
  },
}))
