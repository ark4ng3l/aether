import { create } from 'zustand'

export interface Notification {
  id: string
  type: 'investigation_completed' | 'dossier_ready' | 'tool_awaiting_approval' | 'tool_degraded' | 'info'
  title: string
  description?: string
  timestamp: string
  read: boolean
  /** Tab to navigate to when clicked */
  navigateTo?: string
  /** Entity to select when clicked */
  entityId?: string
  /** Project this notification belongs to */
  projectId?: string
}

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  isOpen: boolean

  addNotification: (n: Omit<Notification, 'id' | 'read'>) => void
  markRead: (id: string) => void
  markAllRead: () => void
  setIsOpen: (open: boolean) => void
  clearAll: () => void
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  unreadCount: 0,
  isOpen: false,

  addNotification: (n) => {
    const notification: Notification = {
      ...n,
      id: `notif_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      read: false,
    }
    set((state) => ({
      notifications: [notification, ...state.notifications].slice(0, 100),
      unreadCount: state.unreadCount + 1,
    }))
  },

  markRead: (id) => {
    set((state) => {
      const was = state.notifications.find((n) => n.id === id)
      if (!was || was.read) return state
      return {
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n
        ),
        unreadCount: Math.max(0, state.unreadCount - 1),
      }
    })
  },

  markAllRead: () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    }))
  },

  setIsOpen: (open) => set({ isOpen: open }),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),
}))
