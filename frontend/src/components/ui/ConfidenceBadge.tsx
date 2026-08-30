import React from 'react'
import { getConfidenceTier } from '../../theme/tokens'

interface ConfidenceBadgeProps {
  score: number
  showLabel?: boolean
  size?: 'sm' | 'md'
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  score,
  showLabel = true,
  size = 'sm',
}) => {
  const tier = getConfidenceTier(score)
  const pct = Math.round(score * 100)

  return (
    <span
      className={`inline-flex items-center gap-1 font-mono-data ${
        size === 'sm' ? 'text-2xs px-1.5 py-0.5' : 'text-xs px-2 py-1'
      } rounded-sm border`}
      style={{
        color: tier.color,
        borderColor: `${tier.color}33`,
        backgroundColor: `${tier.color}0d`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ backgroundColor: tier.color }}
      />
      {pct}%
      {showLabel && (
        <span className="text-text-tertiary font-sans ml-0.5">{tier.label}</span>
      )}
    </span>
  )
}
