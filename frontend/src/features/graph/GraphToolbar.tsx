import React from 'react'
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  RefreshCw,
  Search,
  Filter,
  EyeOff,
  Download,
  Lock,
  Unlock,
} from 'lucide-react'
import { Kbd } from '../../components/ui/Kbd'
import { Tooltip } from '../../components/ui/Tooltip'

interface GraphToolbarProps {
  searchQuery: string
  onSearchChange: (q: string) => void
  onZoomIn: () => void
  onZoomOut: () => void
  onFit: () => void
  onRelayout: () => void
  isLocked: boolean
  onToggleLock: () => void
  onExportPNG: () => void
  confidenceFilter: number
  onConfidenceFilterChange: (val: number) => void
  selectedCount: number
  onHideSelected: () => void
}

export const GraphToolbar: React.FC<GraphToolbarProps> = ({
  searchQuery,
  onSearchChange,
  onZoomIn,
  onZoomOut,
  onFit,
  onRelayout,
  isLocked,
  onToggleLock,
  onExportPNG,
  confidenceFilter,
  onConfidenceFilterChange,
  selectedCount,
  onHideSelected,
}) => {
  return (
    <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-10">
      {/* Left controls: search & filter */}
      <div className="flex items-center gap-2 pointer-events-auto p-1.5 rounded-lg bg-bg-surface/90 border border-border-subtle shadow-md backdrop-blur-sm transition-opacity duration-180 hover:opacity-100 opacity-60">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
          <input
            type="text"
            placeholder="Search graph (⌘F)..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-48 h-7 pl-7 pr-2 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary placeholder:text-text-tertiary focus:border-accent focus:ring-0 transition-colors"
          />
        </div>

        <div className="h-4 w-px bg-border-subtle" />

        <div className="flex items-center gap-1.5 px-1 text-2xs text-text-secondary">
          <Filter className="w-3 h-3 text-text-tertiary" />
          <span>Min Conf:</span>
          <select
            value={confidenceFilter}
            onChange={(e) => onConfidenceFilterChange(parseFloat(e.target.value))}
            className="h-6 px-1 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary"
          >
            <option value="0">All (0%)</option>
            <option value="0.45">Med+ (45%)</option>
            <option value="0.75">High (75%)</option>
          </select>
        </div>

        {selectedCount > 0 && (
          <>
            <div className="h-4 w-px bg-border-subtle" />
            <button
              onClick={onHideSelected}
              className="flex items-center gap-1 px-2 py-1 text-2xs font-medium text-text-secondary hover:text-status-rejected hover:bg-status-rejected/10 rounded transition-colors"
            >
              <EyeOff className="w-3 h-3" />
              Hide ({selectedCount})
            </button>
          </>
        )}
      </div>

      {/* Right controls: view utilities */}
      <div className="flex items-center gap-1 pointer-events-auto p-1.5 rounded-lg bg-bg-surface/90 border border-border-subtle shadow-md backdrop-blur-sm transition-opacity duration-180 hover:opacity-100 opacity-60">
        <Tooltip content="Zoom in">
          <button
            onClick={onZoomIn}
            className="w-7 h-7 flex items-center justify-center rounded text-text-secondary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          >
            <ZoomIn className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </Tooltip>
        <Tooltip content="Zoom out">
          <button
            onClick={onZoomOut}
            className="w-7 h-7 flex items-center justify-center rounded text-text-secondary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          >
            <ZoomOut className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </Tooltip>
        <Tooltip content={<span className="flex items-center gap-1.5">Fit View <Kbd>⌘0</Kbd></span>}>
          <button
            onClick={onFit}
            className="w-7 h-7 flex items-center justify-center rounded text-text-secondary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          >
            <Maximize2 className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </Tooltip>
        <Tooltip content={<span className="flex items-center gap-1.5">Re-layout <Kbd>⌘⇧L</Kbd></span>}>
          <button
            onClick={onRelayout}
            className="w-7 h-7 flex items-center justify-center rounded text-text-secondary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </Tooltip>
        <Tooltip content={isLocked ? "Unlock positions" : "Lock positions"}>
          <button
            onClick={onToggleLock}
            className={`w-7 h-7 flex items-center justify-center rounded transition-colors ${
              isLocked ? 'text-accent bg-accent-subtle' : 'text-text-secondary hover:text-text-primary hover:bg-bg-canvas'
            }`}
          >
            {isLocked ? <Lock className="w-3.5 h-3.5" /> : <Unlock className="w-3.5 h-3.5" />}
          </button>
        </Tooltip>

        <div className="h-4 w-px bg-border-subtle mx-0.5" />

        <Tooltip content="Export PNG snapshot">
          <button
            onClick={onExportPNG}
            className="w-7 h-7 flex items-center justify-center rounded text-text-secondary hover:text-text-primary hover:bg-bg-canvas transition-colors"
          >
            <Download className="w-3.5 h-3.5" strokeWidth={1.5} />
          </button>
        </Tooltip>
      </div>
    </div>
  )
}
