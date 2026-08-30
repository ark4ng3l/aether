import React, { useCallback, useMemo } from 'react'
import { Command } from 'cmdk'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Search,
  FolderOpen,
  Globe,
  Wrench,
  Plus,
  Download,
  Sun,
  Moon,
  Settings,
  Keyboard,
  Play,
  Square,
  FileText,
  GitFork,
  Eye,
  MapPin,
  Terminal,
  Clock,
  LayoutDashboard,
} from 'lucide-react'
import { useCommandPaletteStore } from './useCommandPaletteStore'
import { useProjectStore, TabType } from '../../stores/useProjectStore'
import { useGraphStore } from '../../stores/useGraphStore'
import { useThemeStore } from '../../stores/useThemeStore'
import { api } from '../../api/endpoints'

export const CommandPalette: React.FC = () => {
  const { isOpen, close, recentItems, addRecentItem } = useCommandPaletteStore()
  const {
    projects,
    activeProjectId,
    activeProject,
    setActiveProjectId,
    setActiveTab,
    setIsNewModalOpen,
    setIsSettingsOpen,
  } = useProjectStore()
  const { nodes } = useGraphStore()
  const { resolved, setMode } = useThemeStore()

  const goToTab = useCallback(
    (tab: TabType) => {
      setActiveTab(tab)
      close()
    },
    [setActiveTab, close]
  )

  const selectProject = useCallback(
    (id: string, name: string) => {
      setActiveProjectId(id)
      addRecentItem({ id, label: name, type: 'project' })
      close()
    },
    [setActiveProjectId, addRecentItem, close]
  )

  const selectEntity = useCallback(
    (entityId: string, label: string) => {
      useProjectStore.getState().setSelectedEntityId(entityId)
      setActiveTab('graph')
      addRecentItem({ id: entityId, label, type: 'entity' })
      close()
    },
    [setActiveTab, addRecentItem, close]
  )

  // Entity items from current graph
  const entityItems = useMemo(
    () =>
      nodes.slice(0, 50).map((n) => ({
        id: n.data.id,
        label: n.data.label || n.data.id,
        type: n.data.type,
      })),
    [nodes]
  )

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="fixed inset-0 z-[100] bg-bg-overlay glass"
            onClick={close}
          />

          {/* Palette */}
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.12, ease: [0.16, 1, 0.3, 1] }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 z-[101] w-full max-w-lg"
          >
            <Command
              className="bg-bg-surface border border-border-subtle rounded-lg shadow-overlay overflow-hidden"
              label="Command palette"
            >
              <div className="flex items-center gap-2 px-3 border-b border-border-subtle">
                <Search className="w-4 h-4 text-text-tertiary shrink-0" strokeWidth={1.5} />
                <Command.Input
                  placeholder="Search projects, entities, actions..."
                  className="flex-1 h-11 text-sm bg-transparent text-text-primary placeholder:text-text-tertiary border-0 outline-none focus:ring-0"
                  autoFocus
                />
              </div>

              <Command.List className="max-h-80 overflow-y-auto py-2 px-1.5">
                <Command.Empty className="py-6 text-center text-2xs text-text-tertiary">
                  No results found.
                </Command.Empty>

                {/* Recent Items */}
                {recentItems.length > 0 && (
                  <Command.Group heading="Recent" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-tertiary">
                    {recentItems.map((item) => (
                      <Command.Item
                        key={`recent-${item.id}`}
                        value={`recent ${item.label}`}
                        onSelect={() => {
                          if (item.type === 'project') selectProject(item.id, item.label)
                          else selectEntity(item.id, item.label)
                        }}
                        className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                      >
                        <Clock className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                        {item.label}
                        <span className="ml-auto text-text-tertiary capitalize">{item.type}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                {/* Projects */}
                <Command.Group heading="Projects" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-tertiary">
                  {projects.map((p) => (
                    <Command.Item
                      key={p.id}
                      value={`project ${p.name} ${p.target_seed}`}
                      onSelect={() => selectProject(p.id, p.name)}
                      className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                    >
                      <FolderOpen className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                      <span className="flex-1 truncate">{p.name}</span>
                      <span className="text-text-tertiary font-mono-data">{p.target_seed}</span>
                    </Command.Item>
                  ))}
                </Command.Group>

                {/* Entities */}
                {entityItems.length > 0 && (
                  <Command.Group heading="Entities" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-tertiary">
                    {entityItems.map((e) => (
                      <Command.Item
                        key={e.id}
                        value={`entity ${e.label} ${e.type} ${e.id}`}
                        onSelect={() => selectEntity(e.id, e.label)}
                        className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                      >
                        <Globe className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                        <span className="flex-1 truncate">{e.label}</span>
                        <span className="text-text-tertiary capitalize">{e.type}</span>
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}

                {/* Actions */}
                <Command.Group heading="Actions" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-tertiary">
                  <Command.Item
                    value="new investigation create"
                    onSelect={() => { setIsNewModalOpen(true); close() }}
                    className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                  >
                    <Plus className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                    New Investigation
                  </Command.Item>
                  {activeProject && (
                    <>
                      <Command.Item
                        value="run investigation start"
                        onSelect={() => { api.runProject(activeProject.id); close() }}
                        className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                      >
                        <Play className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                        Run Investigation
                      </Command.Item>
                      <Command.Item
                        value="stop investigation halt"
                        onSelect={() => { api.stopProject(activeProject.id); close() }}
                        className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                      >
                        <Square className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                        Stop Investigation
                      </Command.Item>
                      <Command.Item
                        value="export dossier pdf"
                        onSelect={() => { api.exportDossier(activeProject.id, 'pdf'); close() }}
                        className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                      >
                        <Download className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                        Export Dossier as PDF
                      </Command.Item>
                    </>
                  )}
                  <Command.Item
                    value="toggle theme light dark"
                    onSelect={() => { setMode(resolved === 'dark' ? 'light' : 'dark'); close() }}
                    className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                  >
                    {resolved === 'dark' ? (
                      <Sun className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                    ) : (
                      <Moon className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                    )}
                    Toggle Theme
                  </Command.Item>
                  <Command.Item
                    value="settings preferences"
                    onSelect={() => { setIsSettingsOpen(true); close() }}
                    className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                  >
                    <Settings className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                    Open Settings
                  </Command.Item>
                </Command.Group>

                {/* Navigation */}
                <Command.Group heading="Navigate" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-text-tertiary">
                  {[
                    { tab: 'overview' as TabType, label: 'Overview', icon: LayoutDashboard },
                    { tab: 'graph' as TabType, label: 'Graph', icon: GitFork },
                    { tab: 'timeline' as TabType, label: 'Timeline', icon: Clock },
                    { tab: 'map' as TabType, label: 'Map', icon: MapPin },
                    { tab: 'arsenal' as TabType, label: 'Arsenal', icon: Wrench },
                    { tab: 'vision' as TabType, label: 'Vision', icon: Eye },
                    { tab: 'dossier' as TabType, label: 'Dossier', icon: FileText },
                    { tab: 'console' as TabType, label: 'Console', icon: Terminal },
                  ].map(({ tab, label, icon: Icon }) => (
                    <Command.Item
                      key={tab}
                      value={`go navigate ${label}`}
                      onSelect={() => goToTab(tab)}
                      className="flex items-center gap-2 px-2 py-1.5 text-2xs text-text-secondary rounded cursor-pointer data-[selected=true]:bg-accent-subtle data-[selected=true]:text-text-primary"
                    >
                      <Icon className="w-3.5 h-3.5 text-text-tertiary" strokeWidth={1.5} />
                      Go to {label}
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
