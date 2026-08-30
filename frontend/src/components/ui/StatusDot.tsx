import React from 'react'
import { status as statusColors } from '../../theme/tokens'

type Status = 'idle' | 'running' | 'planning' | 'collecting' | 'reasoning' | 'verifying' | 'synthesizing' | 'completed' | 'failed' | 'stopped' | 'queued'

const statusColorMap: Record<Status, string> = {
  idle: statusColors.idle,
  queued: statusColors.idle,
  running: statusColors.running,
  planning: statusColors.running,
  collecting: statusColors.running,
  reasoning: statusColors.running,
  verifying: statusColors.plausible,
  synthesizing: statusColors.running,
  completed: statusColors.confirmed,
  failed: statusColors.rejected,
  stopped: statusColors.idle,
}

interface StatusDotProps {
  status: Status
  size?: 'sm' | 'md'
  pulse?: boolean
  label?: string
}

export const StatusDot: React.FC<StatusDotProps> = ({ status, size = 'sm', pulse, label }) => {
  const color = statusColorMap[status] || statusColors.idle
  const isActive = ['running', 'planning', 'collecting', 'reasoning', 'verifying', 'synthesizing'].includes(status)
  const shouldPulse = pulse ?? isActive
  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5'

  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex">
        {shouldPulse && (
          <span
            className="absolute inset-0 rounded-full animate-ping opacity-40"
            style={{ backgroundColor: color }}
          />
        )}
        <span
          className={`${dotSize} rounded-full relative`}
          style={{ backgroundColor: color }}
        />
      </span>
      {label && (
        <span className="text-2xs font-medium capitalize text-text-secondary">{label}</span>
      )}
    </span>
  )
}
