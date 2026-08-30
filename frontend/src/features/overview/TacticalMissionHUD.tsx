import React, { useState } from 'react'
import {
  Play,
  Square,
  Sparkles,
  Download,
  Copy,
  Check,
  Shield,
  Clock,
  Radio,
  ExternalLink,
  ChevronDown,
} from 'lucide-react'
import { Project } from '../../types/api'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { showToast } from '../../components/ui/Toast'
import { api } from '../../api/endpoints'


interface TacticalMissionHUDProps {
  project: Project
  isRunning: boolean
  onRun: () => void
  onStop: () => void
  onOpenInjectModal: () => void
}

export const TacticalMissionHUD: React.FC<TacticalMissionHUDProps> = ({
  project,
  isRunning,
  onRun,
  onStop,
  onOpenInjectModal,
}) => {
  const { t, locale } = useLocaleStore()
  const [copied, setCopied] = useState(false)
  const [isExportOpen, setIsExportOpen] = useState(false)

  const handleCopySeed = () => {
    navigator.clipboard.writeText(project.target_seed)
    setCopied(true)
    showToast({ message: 'Target seed copied to clipboard', type: 'info' })
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExport = (format: 'stix' | 'md' | 'json' | 'pdf') => {
    setIsExportOpen(false)
    const token = localStorage.getItem('aether_auth_token') || ''
    const url = `/api/projects/${project.id}/dossier/export?format=${format}${token ? `&token=${token}` : ''}`
    window.open(url, '_blank')
    showToast({ message: `Exporting dossier as ${format.toUpperCase()}`, type: 'success' })
  }


  const getStatusColor = () => {
    switch (project.status) {
      case 'planning':
      case 'reasoning':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30'
      case 'collecting':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30'
      case 'verifying':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30'
      case 'synthesizing':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
      case 'completed':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
      case 'failed':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30'
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30'
    }
  }

  return (
    <div className="relative overflow-hidden bg-bg-surface border border-border-subtle rounded-xl p-4 shadow-sm mb-4">
      {/* Background glowing ambient gradient */}
      <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-accent/5 to-transparent pointer-events-none" />

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 relative z-10">
        {/* Left Target Info */}
        <div className="flex items-start sm:items-center gap-3.5">
          <div className="w-11 h-11 rounded-lg bg-accent-subtle border border-accent/20 flex items-center justify-center shrink-0 shadow-inner">
            <Shield className="w-5 h-5 text-accent" strokeWidth={1.75} />
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-semibold text-text-primary tracking-tight truncate">
                {project.name}
              </h2>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-border-subtle/60 text-text-tertiary border border-border-strong/40">
                {t('overview.targetClassification', 'RESTRICTED // PASSIVE OSINT')}
              </span>
              <div
                className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-2xs font-medium border ${getStatusColor()}`}
              >
                {isRunning && <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping" />}
                <span className="capitalize">{t(`status.${project.status}`, project.status)}</span>
              </div>
            </div>

            <div className="flex items-center gap-3 mt-1 text-2xs text-text-secondary">
              {/* Target Seed chip */}
              <div className="flex items-center gap-1.5 bg-bg-canvas px-2 py-0.5 rounded border border-border-subtle">
                <Radio className="w-3 h-3 text-accent" strokeWidth={1.5} />
                <span className="font-mono text-text-primary font-medium">{project.target_seed}</span>
                <button
                  onClick={handleCopySeed}
                  title="Copy Target Seed"
                  className="text-text-tertiary hover:text-text-primary transition-colors ml-1 rtl:ml-0 rtl:mr-1"
                >
                  {copied ? <Check className="w-3 h-3 text-status-confirmed" /> : <Copy className="w-3 h-3" />}
                </button>
              </div>

              {/* Target Type */}
              <span className="text-text-tertiary font-mono uppercase text-[11px]">
                [{project.target_type}]
              </span>

              {/* Created Time */}
              {project.created_at && (
                <span className="hidden sm:inline-flex items-center gap-1 text-text-tertiary text-2xs">
                  <Clock className="w-3 h-3" />
                  {new Date(project.created_at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right Tactical Action Controls */}
        <div className="flex items-center gap-2 self-end lg:self-center shrink-0">
          {/* Direct Task / Thought Injection Button */}
          <button
            onClick={onOpenInjectModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-text-primary bg-bg-canvas border border-border-strong/60 rounded-lg hover:border-accent/50 hover:bg-accent-subtle/30 transition-all duration-150 shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-accent" strokeWidth={1.75} />
            <span>{t('overview.injectGuidance', 'Inject Guidance')}</span>
          </button>

          {/* Quick Export Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsExportOpen(!isExportOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-2xs font-medium text-text-primary bg-bg-canvas border border-border-strong/60 rounded-lg hover:bg-border-subtle/30 transition-all duration-150 shadow-sm"
            >
              <Download className="w-3.5 h-3.5 text-text-secondary" strokeWidth={1.75} />
              <span>{t('overview.exportDossier', 'Export')}</span>
              <ChevronDown className="w-3 h-3 text-text-tertiary" />
            </button>

            {isExportOpen && (
              <div className="absolute right-0 rtl:right-auto rtl:left-0 mt-1.5 w-44 bg-bg-surface border border-border-strong rounded-lg shadow-xl py-1 z-30 animate-scale-in text-2xs">
                <button
                  onClick={() => handleExport('md')}
                  className="w-full text-left rtl:text-right px-3 py-1.5 hover:bg-accent-subtle hover:text-accent text-text-secondary transition-colors"
                >
                  📄 Markdown Report (.md)
                </button>
                <button
                  onClick={() => handleExport('stix')}
                  className="w-full text-left rtl:text-right px-3 py-1.5 hover:bg-accent-subtle hover:text-accent text-text-secondary transition-colors"
                >
                  🛡️ STIX 2.1 Threat Bundle
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  className="w-full text-left rtl:text-right px-3 py-1.5 hover:bg-accent-subtle hover:text-accent text-text-secondary transition-colors"
                >
                  📑 Intelligence Dossier (PDF/HTML)
                </button>
                <button
                  onClick={() => handleExport('json')}
                  className="w-full text-left rtl:text-right px-3 py-1.5 hover:bg-accent-subtle hover:text-accent text-text-secondary transition-colors"
                >
                  ⚙️ Raw JSON State Dump
                </button>
              </div>
            )}
          </div>

          {/* Run / Stop Primary Action */}
          {!isRunning ? (
            <button
              onClick={onRun}
              className="flex items-center gap-2 px-4 py-1.5 text-2xs font-semibold text-white bg-gradient-to-r from-accent to-blue-600 rounded-lg hover:brightness-110 shadow-md shadow-accent/20 transition-all duration-150"
            >
              <Play className="w-3.5 h-3.5 fill-current" strokeWidth={1.5} />
              <span>{t('overview.runMission', 'Run Mission')}</span>
            </button>
          ) : (
            <button
              onClick={onStop}
              className="flex items-center gap-2 px-4 py-1.5 text-2xs font-semibold text-status-rejected bg-status-rejected/10 border border-status-rejected/30 rounded-lg hover:bg-status-rejected/20 transition-all duration-150"
            >
              <Square className="w-3.5 h-3.5 fill-current" strokeWidth={1.5} />
              <span>{t('overview.stopMission', 'Stop')}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
