import React, { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import { PlusCircle, Copy, Eye, Play, Sparkles } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useGraphStore } from '../../stores/useGraphStore'
import { api } from '../../api/endpoints'
import { Entity } from '../../types/api'
import { GraphToolbar } from './GraphToolbar'
import { GraphMiniMap } from './GraphMiniMap'
import { GraphSidePanel } from './GraphSidePanel'
import { EmptyState } from '../../components/ui/EmptyState'
import { Shield } from 'lucide-react'

// Register layout extension
try {
  cytoscape.use(fcose)
} catch {
  // Already registered
}

export const GraphTab: React.FC = () => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  const { activeProjectId, activeProject, setIsNewModalOpen } = useProjectStore()
  const {
    nodes,
    edges,
    setGraphData,
    selectedEntity,
    setSelectedEntity,
    isolatedNodeId,
    setIsolatedNodeId,
    hiddenNodeIds,
    toggleHideNode,
  } = useGraphStore()

  const [searchQuery, setSearchQuery] = useState('')
  const [confidenceFilter, setConfidenceFilter] = useState(0)
  const [isLocked, setIsLocked] = useState(false)
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean
    x: number
    y: number
    nodeId: string
    nodeData: any
  }>({ visible: false, x: 0, y: 0, nodeId: '', nodeData: null })

  // Fetch initial graph
  useEffect(() => {
    if (!activeProjectId) return
    api.getProjectGraph(activeProjectId)
      .then((data) => {
        setGraphData(data)
      })
      .catch((err) => console.error('Failed to load graph:', err))
  }, [activeProjectId, setGraphData])

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current) return

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'color': '#eef1f6',
            'font-family': 'JetBrains Mono, monospace',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'background-color': '#191d26',
            'border-width': 2,
            'border-color': '#323847',
            'width': 28,
            'height': 28,
            'transition-property': 'border-color, border-width, background-color',
            'transition-duration': 0.15,
          },
        },
        {
          selector: 'node[?is_seed]',
          style: {
            'border-color': '#4f9dff',
            'border-width': 3,
            'width': 36,
            'height': 36,
          },
        },
        {
          selector: 'node[confidence >= 0.75]',
          style: {
            'border-color': '#16a34a',
          },
        },
        {
          selector: 'node[confidence >= 0.45][confidence < 0.75]',
          style: {
            'border-color': '#d97706',
          },
        },
        {
          selector: 'node[confidence < 0.45]',
          style: {
            'border-color': '#dc2626',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-color': '#4f9dff',
            'border-width': 4,
            'background-color': '#232834',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#232834',
            'target-arrow-color': '#323847',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '9px',
            'color': '#5b6472',
            'text-rotation': 'autorotate',
            'font-family': 'Inter, sans-serif',
          },
        },
      ],
      elements: [],
      layout: { name: 'preset' },
      wheelSensitivity: 0.2,
    })

    cy.on('tap', 'node', (evt) => {
      const node = evt.target
      const data = node.data()
      const entityObj: Entity = {
        id: data.id,
        type: data.type || 'unknown',
        properties: data.properties || {},
        confidence: data.confidence || 1.0,
        confidence_signals: data.confidence_signals || [],
        corroboration_count: data.corroboration_count || 1,
        first_seen: new Date().toISOString(),
        last_updated: new Date().toISOString(),
      }
      setSelectedEntity(entityObj)
      setContextMenu((prev) => ({ ...prev, visible: false }))
    })

    cy.on('cxttap', 'node', (evt) => {
      const node = evt.target
      const pos = evt.renderedPosition
      setContextMenu({
        visible: true,
        x: pos.x,
        y: pos.y,
        nodeId: node.id(),
        nodeData: node.data(),
      })
    })

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedEntity(null)
        setContextMenu((prev) => ({ ...prev, visible: false }))
      }
    })

    cyRef.current = cy

    return () => {
      cy.destroy()
      cyRef.current = null
    }
  }, [setSelectedEntity])

  // Sync elements & layout
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return

    // Filter nodes
    const visibleNodes = nodes.filter((n) => {
      if (hiddenNodeIds.includes(n.data.id)) return false
      if (n.data.confidence < confidenceFilter) return false
      return true
    })

    const visibleNodeIds = new Set(visibleNodes.map((n) => n.data.id))
    const visibleEdges = edges.filter(
      (e) => visibleNodeIds.has(e.data.source) && visibleNodeIds.has(e.data.target)
    )

    cy.batch(() => {
      cy.elements().remove()
      cy.add(visibleNodes as any)
      cy.add(visibleEdges as any)
    })

    if (visibleNodes.length > 0 && !isLocked) {
      cy.layout({
        name: 'fcose',
        animate: true,
        animationDuration: 300,
        randomize: false,
        fit: true,
        padding: 40,
        nodeDimensionsIncludeLabels: true,
      } as any).run()
    }
  }, [nodes, edges, hiddenNodeIds, confidenceFilter, isLocked])

  // Search highlight
  useEffect(() => {
    const cy = cyRef.current
    if (!cy) return
    if (!searchQuery) {
      cy.nodes().style('opacity', 1)
      return
    }
    const q = searchQuery.toLowerCase()
    cy.nodes().each((node) => {
      const label = (node.data('label') || '').toLowerCase()
      const id = (node.data('id') || '').toLowerCase()
      if (label.includes(q) || id.includes(q)) {
        node.style('opacity', 1)
      } else {
        node.style('opacity', 0.2)
      }
    })
  }, [searchQuery])

  const handleExportPNG = () => {
    if (!cyRef.current) return
    const png = cyRef.current.png({ full: true, scale: 2, bg: '#0b0d12' })
    const a = document.createElement('a')
    a.href = png
    a.download = `aether-graph-${activeProjectId}.png`
    a.click()
  }

  if (!activeProject) {
    return (
      <EmptyState
        icon={Shield}
        title="No active project"
        description="Select or create a project to inspect its entity graph."
        action={{ label: 'New Investigation', onClick: () => setIsNewModalOpen(true) }}
      />
    )
  }

  return (
    <div className="flex-1 flex overflow-hidden relative select-none">
      <div className="flex-1 relative bg-bg-canvas flex flex-col">
        {/* Floating Toolbar */}
        <GraphToolbar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onZoomIn={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
          onZoomOut={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
          onFit={() => cyRef.current?.fit(undefined, 40)}
          onRelayout={() => {
            cyRef.current?.layout({
              name: 'fcose',
              animate: true,
              animationDuration: 400,
              randomize: true,
              fit: true,
              padding: 40,
            } as any).run()
          }}
          isLocked={isLocked}
          onToggleLock={() => setIsLocked(!isLocked)}
          onExportPNG={handleExportPNG}
          confidenceFilter={confidenceFilter}
          onConfidenceFilterChange={setConfidenceFilter}
          selectedCount={0}
          onHideSelected={() => {}}
        />

        {/* Canvas container */}
        <div ref={containerRef} className="flex-1 w-full h-full" />

        {/* MiniMap */}
        <GraphMiniMap nodes={nodes} edges={edges} />

        {/* Context Menu */}
        {contextMenu.visible && (
          <div
            className="absolute z-50 py-1 bg-bg-surface border border-border-subtle rounded-lg shadow-xl text-2xs min-w-[140px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button
              onClick={() => {
                navigator.clipboard.writeText(contextMenu.nodeId)
                setContextMenu((prev) => ({ ...prev, visible: false }))
              }}
              className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary"
            >
              <Copy className="w-3.5 h-3.5" /> Copy ID
            </button>
            <button
              onClick={() => {
                toggleHideNode(contextMenu.nodeId)
                setContextMenu((prev) => ({ ...prev, visible: false }))
              }}
              className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-status-rejected"
            >
              <Eye className="w-3.5 h-3.5" /> Hide Node
            </button>
          </div>
        )}
      </div>

      {/* Side Panel */}
      {selectedEntity && (
        <GraphSidePanel
          entity={selectedEntity}
          onClose={() => setSelectedEntity(null)}
        />
      )}
    </div>
  )
}
