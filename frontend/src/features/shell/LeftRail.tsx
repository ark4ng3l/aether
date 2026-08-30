import React, { useState } from 'react'
import {
  Search,
  Plus,
  Settings,
  Keyboard,
  ChevronLeft,
  ChevronRight,
  Moon,
  Sun,
  Shield,
  Trash2,
} from 'lucide-react'

import { useProjectStore } from '../../stores/useProjectStore'
import { useThemeStore } from '../../stores/useThemeStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { StatusDot } from '../../components/ui/StatusDot'
import { Tooltip } from '../../components/ui/Tooltip'
import { Kbd } from '../../components/ui/Kbd'
import { showToast } from '../../components/ui/Toast'
import { api } from '../../api/endpoints'
import aetherLogo from '../../assets/aether_logo.png'


interface LeftRailProps {
  onOpenShortcuts?: () => void
}

export const LeftRail: React.FC<LeftRailProps> = ({ onOpenShortcuts }) => {
  const {
    projects,
    activeProjectId,
    setActiveProjectId,
    sidebarCollapsed,
    setSidebarCollapsed,
    setIsNewModalOpen,
    setIsSettingsOpen,
  } = useProjectStore()

  const { resolved, setMode } = useThemeStore()
  const { t } = useLocaleStore()
  const [filter, setFilter] = useState('')

  const filtered = filter
    ? projects.filter(
        (p) =>
          p.name.toLowerCase().includes(filter.toLowerCase()) ||
          p.target_seed.toLowerCase().includes(filter.toLowerCase())
      )
    : projects

  if (sidebarCollapsed) {
    return (
      <aside className="flex flex-col items-center w-12 bg-bg-surface border-r border-border-subtle py-3 gap-2 shrink-0">
        <Tooltip content="AETHER" side="right">
          <button className="w-8 h-8 rounded-lg overflow-hidden border border-accent/20 shadow-sm flex items-center justify-center mb-2 hover:border-accent/50 transition-all">
            <img src={aetherLogo} alt="AETHER" className="w-full h-full object-cover" />
          </button>
        </Tooltip>

        <Tooltip content={t('nav.expandSidebar', 'Expand sidebar')} side="right">
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="w-8 h-8 rounded flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors duration-120"
          >
            <ChevronRight className="w-4 h-4 rtl:rotate-180" strokeWidth={1.5} />
          </button>
        </Tooltip>

        <div className="flex-1" />

        {/* Collapsed project dots */}
        <div className="flex flex-col gap-1.5 mb-3">
          {projects.slice(0, 8).map((p) => (
            <Tooltip key={p.id} content={p.name} side="right">
              <button
                onClick={() => setActiveProjectId(p.id)}
                className={`w-7 h-7 rounded flex items-center justify-center text-2xs font-medium transition-colors duration-120 ${
                  activeProjectId === p.id
                    ? 'bg-accent text-white'
                    : 'text-text-tertiary hover:bg-bg-canvas'
                }`}
              >
                {p.name.charAt(0).toUpperCase()}
              </button>
            </Tooltip>
          ))}
        </div>

        <div className="flex flex-col gap-1">
          <Tooltip content={t('nav.newInvestigation', 'New Investigation')} side="right">
            <button
              onClick={() => setIsNewModalOpen(true)}
              className="w-8 h-8 rounded flex items-center justify-center text-text-tertiary hover:text-accent hover:bg-accent-subtle transition-colors duration-120"
            >
              <Plus className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </Tooltip>
          <Tooltip content={t('nav.settings', 'Settings')} side="right">
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="w-8 h-8 rounded flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors duration-120"
            >
              <Settings className="w-4 h-4" strokeWidth={1.5} />
            </button>
          </Tooltip>
        </div>
      </aside>
    )
  }

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string, projectName: string) => {
    e.stopPropagation()
    if (!window.confirm(`Delete project "${projectName}"?`)) return

    try {
      await api.deleteProject(projectId)
      const remaining = projects.filter((p) => p.id !== projectId)
      useProjectStore.getState().setProjects(remaining)
      if (activeProjectId === projectId) {
        useProjectStore.getState().setActiveProjectId(remaining.length > 0 ? remaining[0].id : null)
      }
      showToast({ message: `Project "${projectName}" deleted`, type: 'info' })
    } catch (err: any) {
      showToast({ message: err?.message || 'Failed to delete project', type: 'error' })
    }
  }

  return (
    <aside className="flex flex-col w-60 bg-bg-surface border-r border-border-subtle shrink-0 select-none">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-3 border-b border-border-subtle">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg overflow-hidden border border-accent/25 shadow-sm shrink-0">
            <img src={aetherLogo} alt="AETHER" className="w-full h-full object-cover" />
          </div>
          <div>
            <h1 className="text-xs font-bold text-text-primary tracking-wider font-mono">AETHER</h1>
            <p className="text-[10px] text-accent tracking-tight font-medium">Neural OSINT Engine</p>
          </div>
        </div>
        <button
          onClick={() => setSidebarCollapsed(true)}
          className="w-6 h-6 rounded flex items-center justify-center text-text-tertiary hover:text-text-primary hover:bg-bg-canvas transition-colors duration-120"
          title={t('nav.collapseSidebar', 'Collapse sidebar')}
        >
          <ChevronLeft className="w-3.5 h-3.5 rtl:rotate-180" strokeWidth={1.5} />
        </button>
      </div>

      {/* Search & New */}
      <div className="px-3 pt-3 pb-2 space-y-2">
        <div className="relative">
          <Search className="absolute left-2 rtl:left-auto rtl:right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
          <input
            type="text"
            placeholder={t('action.filter', 'Filter projects...')}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="w-full h-7 pl-7 rtl:pl-2 rtl:pr-7 pr-2 text-2xs bg-bg-canvas border border-border-subtle rounded text-text-primary placeholder:text-text-tertiary focus:border-accent/50 focus:ring-0 transition-colors duration-120"
          />
        </div>
        <button
          onClick={() => setIsNewModalOpen(true)}
          className="flex items-center justify-center gap-1.5 w-full px-2 py-1.5 text-2xs font-medium text-accent border border-accent/20 rounded hover:bg-accent-subtle transition-colors duration-120"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={1.5} />
          {t('nav.newInvestigation', 'New Investigation')}
        </button>
      </div>

      {/* Project List */}
      <div className="flex-1 overflow-y-auto scrollbar-none px-1.5 pb-2">
        <div className="px-1.5 py-1.5 flex items-center justify-between">
          <span className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider">
            {t('nav.workspace', 'Projects')} ({filtered.length})
          </span>
        </div>
        {filtered.length === 0 ? (
          <p className="px-3 py-4 text-2xs text-text-tertiary text-center">
            {t('project.noProjects', 'No projects found')}
          </p>
        ) : (
          filtered.map((project) => {
            const isActive = project.id === activeProjectId
            return (
              <div
                key={project.id}
                onClick={() => setActiveProjectId(project.id)}
                className={`w-full flex items-center justify-between gap-2 px-2.5 py-2 rounded text-left rtl:text-right transition-colors duration-120 cursor-pointer group ${
                  isActive
                    ? 'bg-accent-subtle text-text-primary border border-accent/20'
                    : 'hover:bg-bg-canvas text-text-secondary border border-transparent'
                }`}
              >
                <div className="flex items-start gap-2 min-w-0 flex-1">
                  <div className="mt-1 shrink-0">
                    <StatusDot status={project.status} size="sm" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={`text-2xs font-medium truncate ${isActive ? 'text-text-primary' : ''}`}>
                      {project.name}
                    </p>
                    <p className="text-[10px] text-text-tertiary truncate font-mono-data">
                      {project.target_seed}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] text-text-tertiary font-mono-data px-1.5 py-0.5 rounded bg-bg-canvas border border-border-subtle/60">
                    {project.entities_count}
                  </span>
                  <button
                    onClick={(e) => handleDeleteProject(e, project.id, project.name)}
                    title="Delete project"
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-status-rejected/10 text-text-tertiary hover:text-status-rejected transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>


      {/* Bottom Actions */}
      <div className="border-t border-border-subtle px-3 py-2 space-y-1">
        <button
          onClick={() => setIsSettingsOpen(true)}
          className="flex items-center gap-2 w-full px-2 py-1.5 text-2xs text-text-secondary hover:text-text-primary hover:bg-bg-canvas rounded transition-colors duration-120"
        >
          <Settings className="w-3.5 h-3.5" strokeWidth={1.5} />
          {t('nav.settings', 'Settings')}
        </button>
        <button
          onClick={onOpenShortcuts}
          className="flex items-center justify-between w-full px-2 py-1.5 text-2xs text-text-secondary hover:text-text-primary hover:bg-bg-canvas rounded transition-colors duration-120"
        >
          <span className="flex items-center gap-2">
            <Keyboard className="w-3.5 h-3.5" strokeWidth={1.5} />
            {t('nav.keyboardShortcuts', 'Shortcuts')}
          </span>
          <Kbd>?</Kbd>
        </button>
        <button
          onClick={() => setMode(resolved === 'dark' ? 'light' : 'dark')}
          className="flex items-center gap-2 w-full px-2 py-1.5 text-2xs text-text-secondary hover:text-text-primary hover:bg-bg-canvas rounded transition-colors duration-120"
        >
          {resolved === 'dark' ? (
            <Sun className="w-3.5 h-3.5" strokeWidth={1.5} />
          ) : (
            <Moon className="w-3.5 h-3.5" strokeWidth={1.5} />
          )}
          {resolved === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </aside>
  )
}

