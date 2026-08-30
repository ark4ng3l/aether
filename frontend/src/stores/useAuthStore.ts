import { create } from 'zustand'
import { getAuthToken, setAuthToken } from '../api/client'

interface AuthState {
  token: string
  isInitialized: boolean
  initToken: () => Promise<void>
  updateToken: (newToken: string) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: '',
  isInitialized: false,

  initToken: async () => {
    const token = await getAuthToken()
    set({ token, isInitialized: true })
  },

  updateToken: (newToken: string) => {
    setAuthToken(newToken)
    set({ token: newToken })
  },
}))
