import React from 'react'
import { Keyboard, X } from 'lucide-react'
import { shortcuts, Shortcut } from '../../shortcuts/registry'
import { Kbd } from '../../components/ui/Kbd'

interface ShortcutsOverlayProps {
  isOpen: boolean
  onClose: () => void
}

export const ShortcutsOverlay: React.FC<ShortcutsOverlayProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null

  // Group shortcuts by context
  const grouped: Record<string, Shortcut[]> = {}
  shortcuts.forEach((s) => {
    const ctx = s.context.charAt(0).toUpperCase() + s.context.slice(1)
    if (!grouped[ctx]) grouped[ctx] = []
    grouped[ctx].push(s)
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in select-none">
      <div className="bg-bg-surface border border-border-subtle rounded-xl shadow-overlay max-w-lg w-full max-h-[80vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-accent" strokeWidth={1.5} />
            <h3 className="text-sm font-bold text-text-primary">Keyboard Shortcuts</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-text-tertiary hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* List of shortcuts generated from registry */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 text-2xs">
          {Object.entries(grouped).map(([context, items]) => (
            <div key={context} className="space-y-1.5">
              <span className="font-semibold text-text-tertiary uppercase tracking-wider text-[10px] block">
                {context}
              </span>
              <div className="space-y-1 rounded-lg border border-border-subtle bg-bg-canvas p-2">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between py-1 px-1.5 rounded hover:bg-bg-surface transition-colors"
                  >
                    <span className="text-text-secondary">{item.description}</span>
                    <Kbd>{item.label}</Kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-border-subtle bg-bg-canvas text-center text-2xs text-text-tertiary">
          Press <Kbd>Esc</Kbd> or click outside to dismiss
        </div>
      </div>
    </div>
  )
}
