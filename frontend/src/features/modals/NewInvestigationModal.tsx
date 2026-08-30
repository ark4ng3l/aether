import React, { useState } from 'react'
import { Plus, X, Shield, AlertCircle } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { showToast } from '../../components/ui/Toast'
import { api } from '../../api/endpoints'
import { EntityType } from '../../types/api'

export const NewInvestigationModal: React.FC = () => {
  const { isNewModalOpen, setIsNewModalOpen, setProjects, setActiveProjectId, setActiveProject } = useProjectStore()
  const { t } = useLocaleStore()

  const [name, setName] = useState('')
  const [targetSeed, setTargetSeed] = useState('')
  const [targetType, setTargetType] = useState<EntityType>('domain')
  const [briefing, setBriefing] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  if (!isNewModalOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const cleanSeed = targetSeed.trim()
    if (!cleanSeed || isSubmitting) return

    setIsSubmitting(true)
    setErrorMsg(null)

    try {
      const project = await api.createProject({
        name: name.trim() || cleanSeed,
        target_seed: cleanSeed,
        target_type: targetType,
        context_briefing: briefing.trim(),
      })

      // Refresh list & select newly created project
      const list = await api.listProjects()
      setProjects(list)
      setActiveProjectId(project.id)
      setActiveProject(project)
      setIsNewModalOpen(false)

      // Reset form
      setName('')
      setTargetSeed('')
      setBriefing('')
      setErrorMsg(null)

      showToast({
        message: `Investigation "${project.name}" initialized successfully.`,
        type: 'success',
      })
    } catch (err: any) {
      const msg = err?.message || 'Failed to initialize investigation'
      console.error('Failed to create investigation:', err)
      setErrorMsg(msg)
      showToast({ message: msg, type: 'error' })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg-overlay glass animate-fade-in select-none">
      <div className="bg-bg-surface border border-border-subtle rounded-xl shadow-overlay max-w-lg w-full overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent">
              <Shield className="w-4 h-4" strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-sm font-bold text-text-primary">
                {t('project.newTitle', 'Initialize Target Investigation')}
              </h3>
              <p className="text-2xs text-text-tertiary">
                {t('project.newSubtitle', 'Seed autonomous cognitive OSINT & threat intelligence')}
              </p>
            </div>
          </div>
          <button
            onClick={() => setIsNewModalOpen(false)}
            className="p-1 rounded text-text-tertiary hover:text-text-primary transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4 text-2xs select-text">
          {errorMsg && (
            <div className="flex items-center gap-2 p-2.5 rounded bg-status-rejected/10 border border-status-rejected/30 text-status-rejected animate-shake">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span className="text-2xs font-medium">{errorMsg}</span>
            </div>
          )}

          <div>
            <label className="text-text-secondary block mb-1 font-medium">
              {t('project.targetSeed', 'Target Seed (Domain, IP, Org, Email, Hash)')} *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. example.com, 185.199.108.153, Acme Corp"
              value={targetSeed}
              onChange={(e) => {
                setTargetSeed(e.target.value)
                if (errorMsg) setErrorMsg(null)
              }}
              className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary font-mono-data focus:border-accent focus:ring-0"
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-text-secondary block mb-1 font-medium">
                {t('project.name', 'Investigation Name')}
              </label>
              <input
                type="text"
                placeholder={t('project.namePlaceholder', 'Defaults to target seed')}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full h-8 px-2.5 bg-bg-canvas border border-border-subtle rounded text-text-primary"
              />
            </div>

            <div>
              <label className="text-text-secondary block mb-1 font-medium">
                {t('project.targetType', 'Target Type')}
              </label>
              <select
                value={targetType}
                onChange={(e) => setTargetType(e.target.value as EntityType)}
                className="w-full h-8 px-2 bg-bg-canvas border border-border-subtle rounded text-text-primary"
              >
                <option value="domain">Domain Name</option>
                <option value="ip_address">IP Address</option>
                <option value="company">Organization / Company</option>
                <option value="email">Email Address</option>
                <option value="person">Individual Name</option>
                <option value="hash">File Hash</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-text-secondary block mb-1 font-medium">
              {t('project.contextBriefing', 'Context Briefing / Analyst Notes (Optional)')}
            </label>
            <textarea
              rows={3}
              placeholder={t('project.briefingPlaceholder', 'Specify known threat actors, targeted industries, or specific investigation focus...')}
              value={briefing}
              onChange={(e) => setBriefing(e.target.value)}
              className="w-full p-2 bg-bg-canvas border border-border-subtle rounded text-text-primary resize-none focus:border-accent focus:ring-0"
            />
          </div>

          {/* Footer */}
          <div className="pt-3 border-t border-border-subtle flex items-center justify-between">
            <button
              type="button"
              onClick={() => setIsNewModalOpen(false)}
              className="px-3 py-1.5 text-2xs text-text-secondary hover:text-text-primary transition-colors"
            >
              {t('action.cancel', 'Cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !targetSeed.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded text-2xs font-medium text-white bg-accent hover:bg-accent-hover disabled:opacity-50 transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              {isSubmitting ? t('action.creating', 'Creating...') : t('project.createBtn', 'Create Investigation')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

