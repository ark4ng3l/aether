import React, { useRef, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Bell, Check, CheckCheck, X, GitFork, FileText, Wrench, AlertTriangle, Info } from 'lucide-react'
import { useNotificationStore, Notification } from './useNotificationStore'
import { useProjectStore } from '../../stores/useProjectStore'

const typeIcons: Record<Notification['type'], React.ElementType> = {
  investigation_completed: Check,
  dossier_ready: FileText,
  tool_awaiting_approval: Wrench,
  tool_degraded: AlertTriangle,
  info: Info,
}

const typeColors: Record<Notification['type'], string> = {
  investigation_completed: 'text-status-confirmed',
  dossier_ready: 'text-accent',
  tool_awaiting_approval: 'text-status-plausible',
  tool_degraded: 'text-status-rejected',
  info: 'text-text-tertiary',
}

export const NotificationCenter: React.FC = () => {
  const { notifications, unreadCount, isOpen, setIsOpen, markRead, markAllRead } = useNotificationStore()
  const { setActiveTab } = useProjectStore()
  const panelRef = useRef<HTMLDivElement>(null)

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [isOpen, setIsOpen])

  const handleNotificationClick = (n: Notification) => {
    markRead(n.id)
    if (n.navigateTo) {
      setActiveTab(n.navigateTo as any)
    }
    setIsOpen(false)
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-8 h-8 rounded flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors duration-120"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <Bell className="w-4 h-4" strokeWidth={1.5} />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-status-rejected animate-pulse-dot" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.12, ease: [0.16, 1, 0.3, 1] }}
            className="absolute right-0 top-full mt-1 w-80 max-h-96 bg-bg-surface border border-border-subtle rounded-lg shadow-overlay overflow-hidden z-50"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-border-subtle">
              <span className="text-2xs font-medium text-text-primary">Notifications</span>
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-2xs text-accent hover:text-accent-hover transition-colors duration-120 flex items-center gap-1"
                >
                  <CheckCheck className="w-3 h-3" strokeWidth={1.5} />
                  Mark all read
                </button>
              )}
            </div>

            {/* List */}
            <div className="overflow-y-auto max-h-80">
              {notifications.length === 0 ? (
                <div className="py-8 text-center text-2xs text-text-tertiary">
                  No notifications yet
                </div>
              ) : (
                notifications.map((n) => {
                  const Icon = typeIcons[n.type]
                  return (
                    <button
                      key={n.id}
                      onClick={() => handleNotificationClick(n)}
                      className={`w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-bg-canvas transition-colors duration-120 border-b border-border-subtle last:border-0 ${
                        n.read ? 'opacity-60' : ''
                      }`}
                    >
                      <div className={`mt-0.5 shrink-0 ${typeColors[n.type]}`}>
                        <Icon className="w-4 h-4" strokeWidth={1.5} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-2xs font-medium text-text-primary truncate">{n.title}</p>
                        {n.description && (
                          <p className="text-2xs text-text-secondary truncate mt-0.5">{n.description}</p>
                        )}
                        <p className="text-2xs text-text-tertiary mt-1 font-mono-data">
                          {new Date(n.timestamp).toLocaleTimeString()}
                        </p>
                      </div>
                      {!n.read && (
                        <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0 mt-1.5" />
                      )}
                    </button>
                  )
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
