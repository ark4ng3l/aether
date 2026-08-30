import React from 'react'
import { Filter, Search, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react'

interface TimelineFilterBarProps {
  searchQuery: string
  onSearchChange: (q: string) => void
  statusFilter: string
  onStatusFilterChange: (s: string) => void
  confidenceFilter: number
  onConfidenceFilterChange: (c: number) => void
  toolFilter: string
  onToolFilterChange: (t: string) => void
  availableTools: string[]
  totalCount: number
}

export const TimelineFilterBar: React.FC<TimelineFilterBarProps> = ({
  searchQuery,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  confidenceFilter,
  onConfidenceFilterChange,
  toolFilter,
  onToolFilterChange,
  availableTools,
  totalCount,
}) => {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-bg-surface border-b border-border-subtle shrink-0">
      <div className="flex items-center gap-2 flex-1 max-w-md">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
          <input
            type="text"
            placeholder="Search task output, reasoning, parameters..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary placeholder:text-text-tertiary focus:border-accent focus:ring-0"
          />
        </div>
      </div>

      <div className="flex items-center gap-2 text-2xs">
        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => onStatusFilterChange(e.target.value)}
          className="h-8 px-2 bg-bg-canvas border border-border-subtle rounded text-text-primary"
        >
          <option value="all">All Statuses</option>
          <option value="completed">Completed Only</option>
          <option value="failed">Failed Only</option>
        </select>

        {/* Tool filter */}
        <select
          value={toolFilter}
          onChange={(e) => onToolFilterChange(e.target.value)}
          className="h-8 px-2 bg-bg-canvas border border-border-subtle rounded text-text-primary"
        >
          <option value="all">All Tools</option>
          {availableTools.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>

        {/* Min Confidence */}
        <select
          value={confidenceFilter}
          onChange={(e) => onConfidenceFilterChange(parseFloat(e.target.value))}
          className="h-8 px-2 bg-bg-canvas border border-border-subtle rounded text-text-primary"
        >
          <option value="0">Min Conf: Any</option>
          <option value="0.45">Min Conf: 45%+</option>
          <option value="0.75">Min Conf: 75%+</option>
        </select>

        <span className="text-2xs text-text-tertiary font-mono-data ml-1">
          {totalCount} event(s)
        </span>
      </div>
    </div>
  )
}
