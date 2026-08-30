import React from 'react'
import { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
  }
}

export const EmptyState: React.FC<EmptyStateProps> = ({ icon: Icon, title, description, action }) => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center select-none animate-fade-in">
    <div className="w-12 h-12 rounded-lg bg-bg-surface flex items-center justify-center border border-border-subtle mb-4">
      <Icon className="w-5 h-5 text-text-tertiary" strokeWidth={1.5} />
    </div>
    <h3 className="text-sm font-medium text-text-primary mb-1">{title}</h3>
    {description && (
      <p className="text-2xs text-text-secondary max-w-xs leading-relaxed">{description}</p>
    )}
    {action && (
      <button
        onClick={action.onClick}
        className="mt-4 px-3 py-1.5 text-2xs font-medium text-white bg-accent rounded hover:bg-accent-hover transition-colors duration-120 ease-enter"
      >
        {action.label}
      </button>
    )}
  </div>
)
