import React, { useState, useRef, useEffect, useMemo } from 'react'
import {
  Terminal,
  Play,
  Pause,
  Trash2,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Info,
  Radio,
  FileCode,
  Sparkles,
} from 'lucide-react'
import { useConsoleStore, LogEntry } from '../../stores/useConsoleStore'
import { Kbd } from '../../components/ui/Kbd'

const typeIcons: Record<LogEntry['type'], React.ElementType> = {
  info: Info,
  warn: AlertTriangle,
  error: AlertTriangle,
  verdict: CheckCircle2,
  token: Terminal,
}

const typeColors: Record<LogEntry['type'], string> = {
  info: 'text-text-secondary',
  warn: 'text-status-plausible',
  error: 'text-status-rejected',
  verdict: 'text-status-confirmed',
  token: 'text-accent',
}

export const ConsoleTab: React.FC = () => {
  const { logs, isPaused, viewMode, setIsPaused, setViewMode, clearLogs } = useConsoleStore()
  const [selectedType, setSelectedType] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const scrollRef = useRef<HTMLDivElement | null>(null)

  // Auto-scroll to bottom unless paused
  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs, isPaused])

  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (selectedType !== 'all' && log.type !== selectedType) return false
      if (searchQuery && !log.text.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false
      }
      return true
    })
  }, [logs, selectedType, searchQuery])

  // Raw combined text for raw stream view
  const rawStreamText = useMemo(() => {
    return logs.map((l) => l.text).join('\n')
  }, [logs])

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg-canvas select-text font-mono-data text-2xs">
      {/* Control Header */}
      <div className="p-3 bg-bg-surface border-b border-border-subtle flex flex-wrap items-center justify-between gap-3 shrink-0 select-none font-sans">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-accent" strokeWidth={1.5} />
            <h3 className="text-xs font-semibold text-text-primary">Live Neural Telemetry & Logs</h3>
          </div>

          {/* View mode toggle */}
          <div className="flex items-center rounded-lg border border-border-subtle bg-bg-canvas p-0.5 text-2xs">
            <button
              onClick={() => setViewMode('structured')}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewMode === 'structured'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              Structured Log
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`px-2 py-1 rounded font-medium transition-colors ${
                viewMode === 'raw'
                  ? 'bg-accent text-white shadow-sm'
                  : 'text-text-tertiary hover:text-text-secondary'
              }`}
            >
              Raw Stream
            </button>
          </div>
        </div>

        {/* Filter and Action controls */}
        <div className="flex items-center gap-2">
          {viewMode === 'structured' && (
            <>
              <input
                type="text"
                placeholder="Search log output..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-7 px-2 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary placeholder:text-text-tertiary w-36"
              />

              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="h-7 px-2 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary"
              >
                <option value="all">All Types</option>
                <option value="verdict">Verdicts</option>
                <option value="info">Info</option>
                <option value="warn">Warnings</option>
                <option value="error">Errors</option>
                <option value="token">Model Tokens</option>
              </select>
            </>
          )}

          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`flex items-center gap-1 px-2.5 py-1 text-2xs font-medium rounded border transition-colors ${
              isPaused
                ? 'bg-status-plausible/10 text-status-plausible border-status-plausible/30'
                : 'bg-bg-canvas text-text-secondary border-border-subtle hover:text-text-primary'
            }`}
          >
            {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
            {isPaused ? 'Resume' : 'Pause'}
          </button>

          <button
            onClick={clearLogs}
            className="p-1 text-text-tertiary hover:text-status-rejected hover:bg-status-rejected/10 rounded transition-colors"
            title="Clear logs (⌘L)"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Stream / Logs Viewport */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-1 bg-[#0b0d12]">
        {viewMode === 'raw' ? (
          /* Raw Stream View */
          <pre className="text-text-primary font-mono-data text-[11px] whitespace-pre-wrap leading-relaxed">
            {rawStreamText || '# Waiting for neural token stream...'}
          </pre>
        ) : (
          /* Structured Log View */
          filteredLogs.length === 0 ? (
            <p className="text-2xs text-text-tertiary py-8 text-center">
              {logs.length > 0 ? 'No logs match the current filter.' : 'Console ready. Awaiting investigation stream...'}
            </p>
          ) : (
            filteredLogs.map((log) => {
              const Icon = typeIcons[log.type] || Info
              const colorClass = typeColors[log.type]

              return (
                <div
                  key={log.id}
                  className="flex items-start gap-2.5 px-2.5 py-1 rounded hover:bg-bg-surface-raised/40 transition-colors leading-relaxed"
                >
                  <span className="text-text-tertiary shrink-0 text-[10px] w-14 mt-0.5">
                    {log.timestamp}
                  </span>
                  <div className={`mt-0.5 shrink-0 ${colorClass}`}>
                    <Icon className="w-3 h-3" strokeWidth={1.5} />
                  </div>
                  <span className={`flex-1 break-all text-[11px] ${colorClass}`}>
                    {log.text}
                  </span>
                </div>
              )
            })
          )
        )}
      </div>
    </div>
  )
}
