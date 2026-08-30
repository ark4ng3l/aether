import React, { useState, useEffect } from 'react'
import {
  X,
  Shield,
  Clock,
  ExternalLink,
  Layers,
  ChevronRight,
  Sparkles,
  Play,
  Copy,
  Check,
  Radio,
  FileCheck2,
} from 'lucide-react'
import { Entity, TaskStep } from '../../types/api'
import { ConfidenceBadge } from '../../components/ui/ConfidenceBadge'
import { MonoText } from '../../components/ui/MonoText'
import { useGraphStore } from '../../stores/useGraphStore'
import { useProjectStore } from '../../stores/useProjectStore'
import { api } from '../../api/endpoints'

interface GraphSidePanelProps {
  entity: Entity | null
  onClose: () => void
}

type PanelTab = 'details' | 'provenance' | 'related'

export const GraphSidePanel: React.FC<GraphSidePanelProps> = ({ entity, onClose }) => {
  const [activeTab, setActiveTab] = useState<PanelTab>('details')
  const [copied, setCopied] = useState(false)
  const [provenanceTasks, setProvenanceTasks] = useState<TaskStep[]>([])
  const [isLoadingProvenance, setIsLoadingProvenance] = useState(false)
  const { nodes, edges, setSelectedEntity } = useGraphStore()
  const { activeProjectId } = useProjectStore()

  useEffect(() => {
    if (!entity || !activeProjectId) return
    setIsLoadingProvenance(true)
    api.getEntityProvenance(activeProjectId, entity.id)
      .then((res) => {
        setProvenanceTasks(res.provenance_tasks || [])
      })
      .catch(() => {
        setProvenanceTasks([])
      })
      .finally(() => setIsLoadingProvenance(false))
  }, [entity?.id, activeProjectId])

  if (!entity) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(entity.id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Find related edges & connected nodes
  const connectedEdges = edges.filter(
    (e) => e.data.source === entity.id || e.data.target === entity.id
  )
  const relatedNodeIds = connectedEdges.map((e) =>
    e.data.source === entity.id ? e.data.target : e.data.source
  )
  const relatedNodes = nodes.filter((n) => relatedNodeIds.includes(n.data.id))

  return (
    <aside className="w-80 border-l border-border-subtle bg-bg-surface flex flex-col h-full shrink-0 z-20 shadow-lg select-text animate-slide-up">
      {/* Header */}
      <div className="p-3.5 border-b border-border-subtle flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xs font-semibold uppercase tracking-wider text-accent px-1.5 py-0.5 rounded bg-accent-subtle border border-accent/20">
              {entity.type}
            </span>
            <ConfidenceBadge score={entity.confidence} />
          </div>
          <div className="flex items-center gap-1.5 group">
            <h3 className="text-xs font-bold text-text-primary font-mono-data truncate">
              {entity.id}
            </h3>
            <button
              onClick={handleCopy}
              className="text-text-tertiary hover:text-text-primary opacity-0 group-hover:opacity-100 transition-opacity"
            >
              {copied ? <Check className="w-3 h-3 text-status-confirmed" /> : <Copy className="w-3 h-3" />}
            </button>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors"
        >
          <X className="w-4 h-4" strokeWidth={1.5} />
        </button>
      </div>

      {/* Tab Switcher */}
      <div className="flex border-b border-border-subtle bg-bg-canvas px-2">
        {(['details', 'provenance', 'related'] as PanelTab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-3 py-2 text-2xs font-medium border-b-2 capitalize transition-colors ${
              activeTab === tab
                ? 'border-accent text-accent'
                : 'border-transparent text-text-tertiary hover:text-text-secondary'
            }`}
          >
            {tab}
            {tab === 'provenance' && provenanceTasks.length > 0 && ` (${provenanceTasks.length})`}
            {tab === 'related' && relatedNodes.length > 0 && ` (${relatedNodes.length})`}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-4">
        {/* DETAILS TAB */}
        {activeTab === 'details' && (
          <>
            {/* Properties */}
            <div>
              <h4 className="text-2xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                Properties
              </h4>
              <div className="rounded border border-border-subtle bg-bg-canvas p-2.5 space-y-2 text-2xs">
                {Object.keys(entity.properties || {}).length === 0 ? (
                  <p className="text-text-tertiary italic">No additional properties</p>
                ) : (
                  Object.entries(entity.properties).map(([k, v]) => (
                    <div key={k} className="flex items-start justify-between gap-2">
                      <span className="text-text-tertiary shrink-0">{k}:</span>
                      <span className="font-mono-data text-text-primary text-right break-all">
                        {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Confidence Signals */}
            {entity.confidence_signals && entity.confidence_signals.length > 0 && (
              <div>
                <h4 className="text-2xs font-semibold text-text-tertiary uppercase tracking-wider mb-2">
                  Corroborating Signals
                </h4>
                <div className="space-y-1.5">
                  {entity.confidence_signals.map((sig, i) => (
                    <div
                      key={i}
                      className="p-2 rounded border border-border-subtle bg-bg-canvas text-2xs flex items-center justify-between"
                    >
                      <div>
                        <p className="font-medium text-text-primary">{sig.source_tool}</p>
                        <p className="text-text-tertiary text-[11px]">{sig.note}</p>
                      </div>
                      <span className="font-mono-data text-accent">+{sig.weight.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Metadata Footer */}
            <div className="pt-2 border-t border-border-subtle text-[11px] text-text-tertiary space-y-1">
              <p>First Seen: {new Date(entity.first_seen).toLocaleString()}</p>
              <p>Corroboration: {entity.corroboration_count || 1} independent source(s)</p>
            </div>
          </>
        )}

        {/* PROVENANCE TAB */}
        {activeTab === 'provenance' && (
          <div className="space-y-2">
            <h4 className="text-2xs font-semibold text-text-tertiary uppercase tracking-wider mb-1">
              Discovery Lineage (DAG)
            </h4>
            {isLoadingProvenance ? (
              <p className="text-2xs text-text-tertiary py-4 text-center">Loading provenance chain...</p>
            ) : provenanceTasks.length === 0 ? (
              <p className="text-2xs text-text-tertiary py-4 text-center">Discovered via target seed initialization.</p>
            ) : (
              provenanceTasks.map((task) => (
                <div
                  key={task.id}
                  className="p-2.5 rounded-lg border border-border-subtle bg-bg-canvas space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-2xs font-bold text-accent">{task.tool_name}</span>
                    <span className="text-[10px] text-text-tertiary font-mono-data">
                      {new Date(task.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  {task.reasoning && (
                    <p className="text-2xs text-text-secondary leading-snug">{task.reasoning}</p>
                  )}
                  {task.critic_reasoning && (
                    <div className="p-1.5 rounded bg-status-confirmed/5 border border-status-confirmed/20 text-[11px] text-status-confirmed">
                      <span className="font-semibold">Critic:</span> {task.critic_reasoning}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* RELATED TAB */}
        {activeTab === 'related' && (
          <div className="space-y-2">
            <h4 className="text-2xs font-semibold text-text-tertiary uppercase tracking-wider mb-1">
              Connected Neighbors ({relatedNodes.length})
            </h4>
            {relatedNodes.length === 0 ? (
              <p className="text-2xs text-text-tertiary py-4 text-center">No connected neighbors yet.</p>
            ) : (
              relatedNodes.map((rn) => (
                <button
                  key={rn.data.id}
                  onClick={() => {
                    setSelectedEntity({
                      id: rn.data.id,
                      type: rn.data.type,
                      properties: rn.data.properties || {},
                      confidence: rn.data.confidence || 1.0,
                      confidence_signals: rn.data.confidence_signals || [],
                      corroboration_count: rn.data.corroboration_count || 1,
                      first_seen: new Date().toISOString(),
                      last_updated: new Date().toISOString(),
                    })
                  }}
                  className="w-full p-2 rounded border border-border-subtle bg-bg-canvas hover:border-accent/30 flex items-center justify-between text-left transition-colors"
                >
                  <div className="min-w-0 flex-1 pr-2">
                    <p className="text-2xs font-mono-data text-text-primary truncate">{rn.data.id}</p>
                    <span className="text-[10px] text-text-tertiary uppercase">{rn.data.type}</span>
                  </div>
                  <ConfidenceBadge score={rn.data.confidence} showLabel={false} size="sm" />
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
