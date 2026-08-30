import React from 'react'
import { InvestigationStatus } from '../../types/api'

const phases = [
  { key: 'planning', label: 'Planning' },
  { key: 'collecting', label: 'Collecting' },
  { key: 'reasoning', label: 'Reasoning' },
  { key: 'verifying', label: 'Verifying' },
  { key: 'synthesizing', label: 'Synthesizing' },
  { key: 'completed', label: 'Done' },
] as const

function getPhaseIndex(status: InvestigationStatus): number {
  const idx = phases.findIndex((p) => p.key === status)
  if (status === 'idle' || status === 'queued') return -1
  if (status === 'failed' || status === 'stopped') return -1
  return idx
}

interface ProgressRailProps {
  status: InvestigationStatus
}

export const ProgressRail: React.FC<ProgressRailProps> = ({ status }) => {
  const currentIdx = getPhaseIndex(status)
  const isFailed = status === 'failed'
  const isStopped = status === 'stopped'

  return (
    <div className="flex items-center gap-1 py-2">
      {phases.map((phase, i) => {
        const isCompleted = currentIdx > i
        const isCurrent = currentIdx === i
        const isPending = currentIdx < i

        return (
          <React.Fragment key={phase.key}>
            {/* Node */}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-2xs font-medium transition-all duration-240 ${
                  isCompleted
                    ? 'bg-status-confirmed text-white'
                    : isCurrent
                    ? 'bg-accent text-white animate-pulse-dot'
                    : isFailed && i === 0
                    ? 'bg-status-rejected text-white'
                    : 'bg-bg-canvas border border-border-subtle text-text-tertiary'
                }`}
              >
                {isCompleted ? '✓' : i + 1}
              </div>
              <span
                className={`text-2xs whitespace-nowrap ${
                  isCurrent ? 'text-accent font-medium' : isCompleted ? 'text-status-confirmed' : 'text-text-tertiary'
                }`}
              >
                {phase.label}
              </span>
            </div>

            {/* Connector */}
            {i < phases.length - 1 && (
              <div
                className={`flex-1 h-0.5 min-w-[16px] rounded-full transition-colors duration-240 ${
                  isCompleted ? 'bg-status-confirmed' : 'bg-border-subtle'
                }`}
              />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}
