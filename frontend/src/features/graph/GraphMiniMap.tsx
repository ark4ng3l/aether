import React, { useEffect, useRef } from 'react'
import { CytoscapeNode, CytoscapeEdge } from '../../types/graph'

interface GraphMiniMapProps {
  nodes: CytoscapeNode[]
  edges: CytoscapeEdge[]
  viewportRect?: { x: number; y: number; w: number; h: number }
}

export const GraphMiniMap: React.FC<GraphMiniMapProps> = ({ nodes, edges }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || nodes.length === 0) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    ctx.clearRect(0, 0, width, height)

    // Render background
    ctx.fillStyle = 'rgba(18, 21, 28, 0.85)'
    ctx.fillRect(0, 0, width, height)

    // Simple pseudo-layout bounds for minimap
    const count = nodes.length
    const radius = Math.min(width, height) * 0.35
    const centerX = width / 2
    const centerY = height / 2

    // Draw nodes
    nodes.forEach((node, i) => {
      const angle = (i / count) * 2 * Math.PI
      const x = centerX + Math.cos(angle) * (radius * (0.4 + (i % 3) * 0.3))
      const y = centerY + Math.sin(angle) * (radius * (0.4 + (i % 3) * 0.3))

      ctx.beginPath()
      ctx.arc(x, y, 2.5, 0, 2 * Math.PI)
      ctx.fillStyle = node.data.is_seed ? '#4f9dff' : node.data.confidence >= 0.75 ? '#16a34a' : '#9aa4b2'
      ctx.fill()
    })
  }, [nodes, edges])

  if (nodes.length === 0) return null

  return (
    <div className="absolute bottom-3 right-3 z-10 rounded-lg overflow-hidden border border-border-subtle shadow-md bg-bg-surface/90 backdrop-blur-sm pointer-events-none opacity-80 hover:opacity-100 transition-opacity">
      <div className="px-2 py-1 bg-bg-surface border-b border-border-subtle text-[10px] text-text-tertiary font-mono-data">
        Mini-Map ({nodes.length})
      </div>
      <canvas ref={canvasRef} width={120} height={80} className="block" />
    </div>
  )
}
