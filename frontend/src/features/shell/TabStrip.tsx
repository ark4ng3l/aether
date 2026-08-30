import React from 'react'
import {
  LayoutDashboard,
  GitFork,
  Clock,
  MapPin,
  Wrench,
  Eye,
  FileText,
  Terminal,
} from 'lucide-react'
import { useProjectStore, TabType } from '../../stores/useProjectStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { Tooltip } from '../../components/ui/Tooltip'
import { Kbd } from '../../components/ui/Kbd'

interface TabDef {
  id: TabType
  icon: React.ElementType
  shortcut: string
}

const tabs: TabDef[] = [
  { id: 'overview', icon: LayoutDashboard, shortcut: '⌘1' },
  { id: 'graph', icon: GitFork, shortcut: '⌘2' },
  { id: 'timeline', icon: Clock, shortcut: '⌘3' },
  { id: 'map', icon: MapPin, shortcut: '⌘4' },
  { id: 'arsenal', icon: Wrench, shortcut: '⌘5' },
  { id: 'vision', icon: Eye, shortcut: '⌘6' },
  { id: 'dossier', icon: FileText, shortcut: '⌘7' },
  { id: 'console', icon: Terminal, shortcut: '⌘8' },
]

export const TabStrip: React.FC = () => {
  const { activeTab, setActiveTab, activeProject } = useProjectStore()
  const { t } = useLocaleStore()

  if (!activeProject) return null

  return (
    <nav className="flex items-center gap-0.5 px-3 border-b border-border-subtle bg-bg-surface overflow-x-auto scrollbar-none" role="tablist">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id
        const Icon = tab.icon
        const label = t(`nav.${tab.id}`, tab.id)
        return (
          <Tooltip key={tab.id} content={<span className="flex items-center gap-2">{label} <Kbd>{tab.shortcut}</Kbd></span>} side="bottom" delay={600}>
            <button
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-2xs font-medium whitespace-nowrap border-b-2 transition-colors duration-120 ease-enter ${
                isActive
                  ? 'border-accent text-accent'
                  : 'border-transparent text-text-tertiary hover:text-text-secondary hover:border-border-strong'
              }`}
            >
              <Icon className="w-3.5 h-3.5" strokeWidth={1.5} />
              {label}
            </button>
          </Tooltip>
        )
      })}
    </nav>
  )
}

