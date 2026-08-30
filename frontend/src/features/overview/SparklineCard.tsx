import React from 'react'
import { LucideIcon } from 'lucide-react'

interface SparklineCardProps {
  label: string
  value: number
  icon: LucideIcon
  color: string
}

export const SparklineCard: React.FC<SparklineCardProps> = ({ label, value, icon: Icon, color }) => {
  // Generate a simple sparkline from the value (simulated growth curve)
  const points = Array.from({ length: 12 }, (_, i) => {
    const progress = i / 11
    const y = Math.min(value, Math.floor(value * Math.pow(progress, 0.7)))
    return y
  })

  const max = Math.max(...points, 1)
  const svgWidth = 80
  const svgHeight = 24
  const pathData = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * svgWidth
      const y = svgHeight - (p / max) * svgHeight
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-border-subtle bg-bg-surface hover:border-border-strong transition-colors duration-120">
      <div className="flex items-center gap-2.5">
        <div
          className="w-8 h-8 rounded flex items-center justify-center"
          style={{ backgroundColor: `${color}15` }}
        >
          <Icon className="w-4 h-4" style={{ color }} strokeWidth={1.5} />
        </div>
        <div>
          <p className="text-xl font-semibold text-text-primary font-mono-data">{value}</p>
          <p className="text-2xs text-text-tertiary">{label}</p>
        </div>
      </div>

      {/* Sparkline */}
      <svg width={svgWidth} height={svgHeight} className="shrink-0 ml-2">
        <path d={pathData} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity={0.7} />
      </svg>
    </div>
  )
}
