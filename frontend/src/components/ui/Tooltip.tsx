import React, { useState, useRef, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'

interface TooltipProps {
  content: React.ReactNode
  children: React.ReactElement
  side?: 'top' | 'bottom' | 'left' | 'right'
  delay?: number
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  side = 'top',
  delay = 400,
}) => {
  const [open, setOpen] = useState(false)
  const timeoutRef = useRef<number | null>(null)

  const show = useCallback(() => {
    timeoutRef.current = window.setTimeout(() => setOpen(true), delay)
  }, [delay])

  const hide = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setOpen(false)
  }, [])

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-1.5',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-1.5',
    left: 'right-full top-1/2 -translate-y-1/2 mr-1.5',
    right: 'left-full top-1/2 -translate-y-1/2 ml-1.5',
  }

  return (
    <span className="relative inline-flex" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      {children}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.1 }}
            className={`absolute z-50 px-2 py-1 text-2xs text-text-primary bg-bg-surface-raised border border-border-subtle rounded shadow-lg whitespace-nowrap pointer-events-none ${positionClasses[side]}`}
            role="tooltip"
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  )
}
