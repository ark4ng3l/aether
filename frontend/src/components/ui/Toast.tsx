import React, { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X, CheckCircle, AlertTriangle, Info } from 'lucide-react'

export interface ToastData {
  id: string
  type: 'success' | 'error' | 'info'
  message: string
  duration?: number
}

// Simple global toast state
let toastListeners: ((t: ToastData[]) => void)[] = []
let toasts: ToastData[] = []

function notify() {
  toastListeners.forEach((l) => l([...toasts]))
}

export function showToast(data: Omit<ToastData, 'id'>) {
  const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
  const toast: ToastData = { ...data, id }
  toasts = [...toasts, toast]
  notify()

  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    notify()
  }, data.duration || 4000)
}

export const ToastContainer: React.FC = () => {
  const [items, setItems] = useState<ToastData[]>([])

  useEffect(() => {
    toastListeners.push(setItems)
    return () => {
      toastListeners = toastListeners.filter((l) => l !== setItems)
    }
  }, [])

  const icons = {
    success: CheckCircle,
    error: AlertTriangle,
    info: Info,
  }

  const colors = {
    success: 'text-status-confirmed border-status-confirmed/20',
    error: 'text-status-rejected border-status-rejected/20',
    info: 'text-accent border-accent/20',
  }

  return (
    <div
      className="fixed bottom-4 right-4 z-[9999] flex flex-col-reverse gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="false"
    >
      <AnimatePresence>
        {items.map((toast) => {
          const Icon = icons[toast.type]
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
              className={`pointer-events-auto flex items-center gap-2 px-3 py-2.5 rounded-lg bg-bg-surface-raised border shadow-lg backdrop-blur-sm max-w-sm ${colors[toast.type]}`}
            >
              <Icon className="w-4 h-4 shrink-0" strokeWidth={1.5} />
              <span className="text-2xs text-text-primary flex-1">{toast.message}</span>
              <button
                onClick={() => {
                  toasts = toasts.filter((t) => t.id !== toast.id)
                  notify()
                }}
                className="text-text-tertiary hover:text-text-primary shrink-0"
              >
                <X className="w-3.5 h-3.5" strokeWidth={1.5} />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
