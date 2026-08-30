import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  FileText,
  Download,
  Copy,
  Check,
  RefreshCw,
  Clock,
  Sparkles,
  Shield,
  FileCheck,
} from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { api } from '../../api/endpoints'
import { EmptyState } from '../../components/ui/EmptyState'

interface DossierVersion {
  id: string
  timestamp: string
  content: string
}

export const DossierTab: React.FC = () => {
  const { activeProject, activeProjectId, setSelectedEntityId, setActiveTab, setIsNewModalOpen } = useProjectStore()
  const [dossierText, setDossierText] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [copied, setCopied] = useState(false)
  const [versions, setVersions] = useState<DossierVersion[]>([])
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null)

  const fetchDossier = async () => {
    if (!activeProjectId) return
    setIsLoading(true)
    try {
      const res = await api.getProjectDossier(activeProjectId)
      const text = res.dossier || ''
      setDossierText(text)

      // Store in version history if new
      if (text) {
        const newVer: DossierVersion = {
          id: `v_${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          content: text,
        }
        setVersions((prev) => {
          if (prev.length === 0 || prev[0].content !== text) {
            return [newVer, ...prev].slice(0, 10)
          }
          return prev
        })
        setSelectedVersionId(newVer.id)
      }
    } catch (err) {
      console.error('Failed to load dossier:', err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchDossier()
  }, [activeProjectId])

  const handleCopy = () => {
    navigator.clipboard.writeText(dossierText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExport = (format: 'pdf' | 'stix' | 'json' | 'md') => {
    if (!activeProjectId) return
    api.exportDossier(activeProjectId, format)
      .then((data) => {
        if (typeof data === 'object') {
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `aether-report-${activeProjectId}.${format === 'stix' ? 'stix.json' : 'json'}`
          a.click()
        }
      })
      .catch((err) => console.error('Export failed:', err))
  }

  const handleSelectVersion = (versionId: string) => {
    setSelectedVersionId(versionId)
    const ver = versions.find((v) => v.id === versionId)
    if (ver) {
      setDossierText(ver.content)
    }
  }

  if (!activeProject) {
    return (
      <EmptyState
        icon={Shield}
        title="No active project"
        description="Select or start an investigation to view its synthesized intelligence dossier."
        action={{ label: 'New Investigation', onClick: () => setIsNewModalOpen(true) }}
      />
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-bg-canvas select-text">
      {/* Action Header */}
      <div className="p-3 bg-bg-surface border-b border-border-subtle flex flex-wrap items-center justify-between gap-3 shrink-0 select-none">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-accent" strokeWidth={1.5} />
            <h3 className="text-xs font-semibold text-text-primary">Intelligence Dossier</h3>
          </div>

          {/* Version dropdown */}
          {versions.length > 0 && (
            <div className="flex items-center gap-1.5 text-2xs text-text-tertiary">
              <Clock className="w-3 h-3" />
              <select
                value={selectedVersionId || ''}
                onChange={(e) => handleSelectVersion(e.target.value)}
                className="h-6 px-1.5 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary"
              >
                {versions.map((v, i) => (
                  <option key={v.id} value={v.id}>
                    Draft #{versions.length - i} · {v.timestamp}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Export and Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={fetchDossier}
            className="p-1.5 rounded text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors"
            title="Refresh dossier"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2.5 py-1 text-2xs font-medium text-text-secondary border border-border-subtle hover:text-text-primary rounded bg-bg-canvas transition-colors"
          >
            {copied ? <Check className="w-3 h-3 text-status-confirmed" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>

          <div className="h-4 w-px bg-border-subtle mx-0.5" />

          <button
            onClick={() => handleExport('md')}
            className="px-2 py-1 text-2xs font-medium text-text-secondary border border-border-subtle hover:text-text-primary rounded bg-bg-canvas transition-colors"
          >
            Markdown
          </button>
          <button
            onClick={() => handleExport('stix')}
            className="px-2 py-1 text-2xs font-medium text-accent border border-accent/30 hover:bg-accent-subtle rounded transition-colors flex items-center gap-1"
          >
            <Sparkles className="w-3 h-3" /> STIX 2.1
          </button>
          <button
            onClick={() => handleExport('pdf')}
            className="px-2.5 py-1 text-2xs font-medium text-white bg-accent hover:bg-accent-hover rounded transition-colors flex items-center gap-1"
          >
            <Download className="w-3 h-3" /> PDF Export
          </button>
        </div>
      </div>

      {/* Markdown Content Area */}
      <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto w-full">
        {isLoading ? (
          <p className="text-2xs text-text-tertiary text-center py-12 animate-pulse">
            Synthesizing intelligence dossier...
          </p>
        ) : !dossierText ? (
          <EmptyState
            icon={FileCheck}
            title="Dossier is synthesizing"
            description="The dossier will appear here automatically once the synthesis agent verifies all evidence."
          />
        ) : (
          <article className="prose prose-invert max-w-none text-2xs leading-relaxed space-y-4 font-sans">
            <ReactMarkdown
              components={{
                h1: ({ children }) => (
                  <h1 className="text-base font-bold text-text-primary border-b border-border-subtle pb-2 mt-4 mb-3">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-sm font-bold text-text-primary mt-4 mb-2">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-xs font-semibold text-accent mt-3 mb-1">
                    {children}
                  </h3>
                ),
                p: ({ children }) => (
                  <p className="text-2xs text-text-secondary leading-relaxed">
                    {children}
                  </p>
                ),
                code: ({ children }) => (
                  <code className="px-1.5 py-0.5 rounded bg-bg-surface border border-border-subtle font-mono-data text-accent text-[11px]">
                    {children}
                  </code>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-inside space-y-1 text-text-secondary pl-2">
                    {children}
                  </ul>
                ),
              }}
            >
              {dossierText}
            </ReactMarkdown>
          </article>
        )}
      </div>
    </div>
  )
}
