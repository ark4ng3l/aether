import { create } from 'zustand'

interface CommandPaletteState {
  isOpen: boolean
  recentItems: { id: string; label: string; type: string }[]
  open: () => void
  close: () => void
  toggle: () => void
  addRecentItem: (item: { id: string; label: string; type: string }) => void
}

export const useCommandPaletteStore = create<CommandPaletteState>((set) => ({
  isOpen: false,
  recentItems: [],

  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),

  addRecentItem: (item) => {
    set((state) => {
      const filtered = state.recentItems.filter((r) => r.id !== item.id)
      return { recentItems: [item, ...filtered].slice(0, 10) }
    })
  },
}))
