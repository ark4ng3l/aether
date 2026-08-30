import React from 'react'
import { AlertTriangle } from 'lucide-react'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message,
  onRetry,
}) => (
  <div className="flex flex-col items-center justify-center py-16 px-6 text-center select-none animate-fade-in">
    <div className="w-12 h-12 rounded-lg bg-status-rejected/10 flex items-center justify-center mb-4">
      <AlertTriangle className="w-5 h-5 text-status-rejected" strokeWidth={1.5} />
    </div>
    <h3 className="text-sm font-medium text-text-primary mb-1">{title}</h3>
    <p className="text-2xs text-text-secondary max-w-sm leading-relaxed font-mono-data">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="mt-4 px-3 py-1.5 text-2xs font-medium text-accent border border-accent/30 rounded hover:bg-accent-subtle transition-colors duration-120 ease-enter"
      >
        Retry
      </button>
    )}
  </div>
)
