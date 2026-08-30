import React from 'react'

interface KbdProps {
  children: React.ReactNode
}

/** Keyboard shortcut badge for UI display. */
export const Kbd: React.FC<KbdProps> = ({ children }) => (
  <kbd className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-2xs font-mono-data text-text-tertiary bg-bg-surface border border-border-subtle rounded-sm shadow-sm select-none">
    {children}
  </kbd>
)
