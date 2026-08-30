import React, { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import fcose from 'cytoscape-fcose'
import {
  PlusCircle,
  Copy,
  Eye,
  Play,
  Sparkles,
  Shield,
  Search,
  Radio,
  Globe,
  Skull,
  Lock,
  Mail,
  User,
  Terminal,
} from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useGraphStore } from '../../stores/useGraphStore'
import { api } from '../../api/endpoints'
import { Entity } from '../../types/api'
import { GraphToolbar } from './GraphToolbar'
import { GraphMiniMap } from './GraphMiniMap'
import { GraphSidePanel } from './GraphSidePanel'
import { EmptyState } from '../../components/ui/EmptyState'

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
            className="absolute z-50 py-1.5 bg-bg-surface/95 backdrop-blur-md border border-border-subtle rounded-xl shadow-2xl text-2xs min-w-[210px] overflow-hidden animate-in fade-in zoom-in-95 duration-100"
            style={{ left: Math.min(contextMenu.x, window.innerWidth - 230), top: Math.min(contextMenu.y, window.innerHeight - 300) }}
          >
            <div className="px-3 py-1 text-[10px] font-mono font-semibold text-accent uppercase tracking-wider border-b border-border-subtle flex items-center justify-between">
              <span>{contextMenu.nodeData?.type || 'Entity'} Pivot</span>
              <span className="text-text-tertiary">1-Click</span>
            </div>

            {/* IP Specific Pivots */}
            {contextMenu.nodeData?.type === 'ip_address' && (
              <>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'shodan_lookup', { ip: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Search className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Shodan Intel</span>
                </button>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'port_prober', { host: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Radio className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Probe Ports</span>
                </button>
              </>
            )}

            {/* Domain Specific Pivots */}
            {contextMenu.nodeData?.type === 'domain' && (
              <>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'stealth_crawler', { url: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Globe className="w-3.5 h-3.5 text-sky-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Stealth Crawler</span>
                </button>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'darkweb_recon', { query: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Skull className="w-3.5 h-3.5 text-purple-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Dark Web & Tor</span>
                </button>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'cert_transparency', { domain: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Lock className="w-3.5 h-3.5 text-amber-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Cert Transparency</span>
                </button>
              </>
            )}

            {/* Email Specific Pivots */}
            {contextMenu.nodeData?.type === 'email' && (
              <>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'email_security_auditor', { email: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Mail className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Email Security</span>
                </button>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'darkweb_recon', { query: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Skull className="w-3.5 h-3.5 text-purple-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Dark Web Leaks</span>
                </button>
              </>
            )}

            {/* Social / Person Pivots */}
            {(contextMenu.nodeData?.type === 'social_handle' || contextMenu.nodeData?.type === 'person') && (
              <>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'deep_social_matrix', { handle: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <User className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: Deep Social Matrix</span>
                </button>
                <button
                  onClick={async () => {
                    setContextMenu((prev) => ({ ...prev, visible: false }))
                    if (!activeProjectId) return
                    await api.executeToolDirect(activeProjectId, 'github_dorker', { query: contextMenu.nodeId })
                    const g = await api.getProjectGraph(activeProjectId)
                    setGraphData(g)
                  }}
                  className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
                >
                  <Terminal className="w-3.5 h-3.5 text-amber-400 group-hover:scale-110 transition-transform" />
                  <span>Pivot: GitHub Code Dorks</span>
                </button>
              </>
            )}

            {/* Universal Actions */}
            <div className="my-1 border-t border-border-subtle" />

            <button
              onClick={async () => {
                setContextMenu((prev) => ({ ...prev, visible: false }))
                if (!activeProjectId) return
                await api.threatModel(activeProjectId, true)
                const g = await api.getProjectGraph(activeProjectId)
                setGraphData(g)
              }}
              className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary group"
            >
              <Shield className="w-3.5 h-3.5 text-rose-400 group-hover:scale-110 transition-transform" />
              <span>Map MITRE ATT&CK</span>
            </button>

            <button
              onClick={() => {
                navigator.clipboard.writeText(contextMenu.nodeId)
                setContextMenu((prev) => ({ ...prev, visible: false }))
              }}
              className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-text-primary"
            >
              <Copy className="w-3.5 h-3.5 text-text-tertiary" />
              <span>Copy Entity ID</span>
            </button>

            <button
              onClick={() => {
                toggleHideNode(contextMenu.nodeId)
                setContextMenu((prev) => ({ ...prev, visible: false }))
              }}
              className="w-full px-3 py-1.5 flex items-center gap-2 hover:bg-bg-canvas text-left text-status-rejected"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Hide Node</span>
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
