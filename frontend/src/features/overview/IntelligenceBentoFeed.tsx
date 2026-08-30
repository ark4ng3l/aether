import React, { useState } from 'react'
import {
  Globe,
  Server,
  Mail,
  User,
  ShieldAlert,
  Hash,
  Search,
  ExternalLink,
  Copy,
  Check,
  CheckCircle2,
  AlertCircle,
  Layers,
} from 'lucide-react'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { showToast } from '../../components/ui/Toast'
import { useProjectStore } from '../../stores/useProjectStore'

interface EntityNode {
  id: string
  label: string
  type: string
  confidence: number
  corroboration_count: number
  properties: Record<string, any>
}

interface IntelligenceBentoFeedProps {
  nodes: any[]
}

export const IntelligenceBentoFeed: React.FC<IntelligenceBentoFeedProps> = ({ nodes }) => {
  const { t } = useLocaleStore()
  const { setActiveTab } = useProjectStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  // Map nodes to a standardized structure
  const entities: EntityNode[] = nodes.map((n) => {
    const data = n?.data || n || {}
    return {
      id: String(data.id || ''),
      label: String(data.label || data.name || data.id || ''),
      type: String(data.type || 'unknown').toLowerCase(),
      confidence: typeof data.confidence === 'number' ? data.confidence : 0.85,
      corroboration_count: Number(data.corroboration_count || data.signals?.length || 1),
      properties: data.properties || {},
    }
  })

  // Filter entities
  const filteredEntities = entities.filter((ent) => {
    const q = searchQuery.toLowerCase()
    const matchesSearch =
      ent.id.toLowerCase().includes(q) ||
      ent.label.toLowerCase().includes(q) ||
      ent.type.toLowerCase().includes(q)

    if (!matchesSearch) return false

    if (filterType === 'all') return true
    if (filterType === 'domain') return ent.type.includes('domain') || ent.type.includes('subdomain') || ent.type.includes('url')
    if (filterType === 'ip') return ent.type.includes('ip') || ent.type.includes('asn') || ent.type.includes('network')
    if (filterType === 'threat') return ent.type.includes('vulnerability') || ent.type.includes('breach') || ent.type.includes('credential') || ent.type.includes('cve')
    if (filterType === 'identity') return ent.type.includes('person') || ent.type.includes('email') || ent.type.includes('handle') || ent.type.includes('social')
    return true
  })

  const handleCopy = (val: string, id: string) => {
    navigator.clipboard.writeText(val)
    setCopiedId(id)
    showToast({ message: `Copied ${val}`, type: 'info' })
    setTimeout(() => setCopiedId(null), 2000)
  }

  const getEntityIcon = (type: string) => {
    if (type.includes('domain') || type.includes('subdomain')) return Globe
    if (type.includes('ip') || type.includes('asn') || type.includes('network')) return Server
    if (type.includes('email')) return Mail
    if (type.includes('person') || type.includes('handle')) return User
    if (type.includes('vulnerability') || type.includes('breach')) return ShieldAlert
    return Hash
  }

  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl p-4 shadow-sm flex flex-col h-full">
      {/* Header & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-text-primary flex items-center gap-2">
              <span>{t('overview.confidenceMatrix', 'Discovered Intelligence Feed')}</span>
              <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-accent-subtle text-accent font-bold">
                {entities.length} Nodes
              </span>
            </h3>
            <p className="text-[10px] text-text-tertiary">
              Corroborated intelligence graph entities & cross-source telemetry
            </p>
          </div>
        </div>

        {/* Search input */}
        <div className="relative min-w-[180px]">
          <Search className="w-3.5 h-3.5 absolute left-2.5 rtl:left-auto rtl:right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('overview.searchAssets', 'Search assets...')}
            className="w-full pl-8 pr-3 rtl:pl-3 rtl:pr-8 py-1.5 text-2xs bg-bg-canvas border border-border-strong/60 rounded-lg text-text-primary placeholder:text-text-tertiary focus:border-accent outline-none"
          />
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-1.5 py-2.5 overflow-x-auto scrollbar-none border-b border-border-subtle/50 text-[11px]">
        {[
          { id: 'all', label: t('overview.filterAll', 'All Entities') },
          { id: 'domain', label: t('overview.filterDomains', 'Domains') },
          { id: 'ip', label: t('overview.filterIPs', 'IPs & ASN') },
          { id: 'threat', label: t('overview.filterThreats', 'Threats') },
          { id: 'identity', label: t('overview.filterIdentities', 'Identities') },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setFilterType(tab.id)}
            className={`px-2.5 py-1 rounded-md transition-all whitespace-nowrap ${
              filterType === tab.id
                ? 'bg-accent text-white font-medium shadow-xs'
                : 'text-text-secondary hover:text-text-primary hover:bg-bg-canvas'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Entity Cards Grid */}
      <div className="flex-1 overflow-y-auto max-h-[380px] space-y-2 py-2 pr-1 scrollbar-thin">
        {filteredEntities.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center text-text-tertiary">
            <Layers className="w-8 h-8 opacity-20 mb-2" />
            <p className="text-2xs">No matching entities found in intelligence graph.</p>
          </div>
        ) : (
          filteredEntities.map((entity) => {
            const Icon = getEntityIcon(entity.type)
            const confPct = Math.round(entity.confidence * 100)
            const isConfirmed = confPct >= 80

            return (
              <div
                key={entity.id}
                className="group p-2.5 bg-bg-canvas hover:bg-bg-surface-raised border border-border-subtle hover:border-accent/40 rounded-xl transition-all duration-150 shadow-xs flex items-center justify-between gap-3"
              >
                {/* Left icon & details */}
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle flex items-center justify-center shrink-0 group-hover:border-accent/30 group-hover:text-accent transition-colors">
                    <Icon className="w-4 h-4 text-text-secondary group-hover:text-accent" strokeWidth={1.75} />
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-2xs font-semibold text-text-primary font-mono truncate max-w-[200px] sm:max-w-[280px]">
                        {entity.label}
                      </span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-border-subtle/50 text-text-tertiary uppercase">
                        {entity.type}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 mt-0.5 text-[10px] text-text-tertiary">
                      <span className="flex items-center gap-1">
                        {isConfirmed ? (
                          <CheckCircle2 className="w-3 h-3 text-status-confirmed" />
                        ) : (
                          <AlertCircle className="w-3 h-3 text-status-plausible" />
                        )}
                        <span className={isConfirmed ? 'text-status-confirmed font-medium' : 'text-status-plausible'}>
                          {confPct}% {t('overview.corroborations', 'Confidence')}
                        </span>
                      </span>

                      {entity.corroboration_count > 1 && (
                        <span className="font-mono text-accent">
                          • {entity.corroboration_count} Signals
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right Quick Actions */}
                <div className="flex items-center gap-1 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleCopy(entity.label, entity.id)}
                    title="Copy entity value"
                    className="p-1.5 rounded hover:bg-border-subtle/60 text-text-tertiary hover:text-text-primary transition-colors"
                  >
                    {copiedId === entity.id ? (
                      <Check className="w-3.5 h-3.5 text-status-confirmed" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>

                  <button
                    onClick={() => setActiveTab('graph')}
                    title="Explore in Graph Topology"
                    className="p-1.5 rounded hover:bg-accent-subtle hover:text-accent text-text-tertiary transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
