import React from 'react'
import { Search, ChevronRight } from 'lucide-react'
import { useProjectStore } from '../../stores/useProjectStore'
import { useLocaleStore } from '../../stores/useLocaleStore'
import { StatusDot } from '../../components/ui/StatusDot'
import { Kbd } from '../../components/ui/Kbd'
import { NotificationCenter } from '../notifications/NotificationCenter'
import { LanguageSelector } from '../../components/ui/LanguageSelector'

interface TopBarProps {
  onOpenCommandPalette?: () => void
}

export const TopBar: React.FC<TopBarProps> = ({ onOpenCommandPalette }) => {
  const { activeProject } = useProjectStore()
  const { t } = useLocaleStore()

  return (
    <header className="flex items-center justify-between h-11 px-3 bg-bg-surface border-b border-border-subtle shrink-0 select-none">
      {/* Left: Breadcrumb */}
      <div className="flex items-center gap-1.5 text-2xs min-w-0">
        <span className="text-text-tertiary">{t('nav.workspace', 'Workspace')}</span>
        {activeProject && (
          <>
            <ChevronRight className="w-3 h-3 text-text-tertiary shrink-0 rtl:rotate-180" strokeWidth={1.5} />
            <span className="text-text-primary font-medium truncate max-w-[200px]">
              {activeProject.name}
            </span>
          </>
        )}
      </div>

      {/* Center: Command Palette Trigger */}
      <button
        onClick={onOpenCommandPalette}
        className="flex items-center gap-2 px-3 py-1 mx-4 rounded border border-border-subtle bg-bg-canvas hover:border-border-strong text-text-tertiary hover:text-text-secondary transition-colors duration-120 max-w-xs"
      >
        <Search className="w-3.5 h-3.5" strokeWidth={1.5} />
        <span className="text-2xs">{t('nav.search', 'Search or jump to...')}</span>
        <Kbd>⌘K</Kbd>
      </button>

      {/* Right: Status + Language Selector + Notifications */}
      <div className="flex items-center gap-2 sm:gap-3">
        {activeProject && (
          <StatusDot
            status={activeProject.status}
            label={t(`status.${activeProject.status}`, activeProject.status)}
            size="sm"
          />
        )}

        <LanguageSelector />
        <NotificationCenter />
      </div>
    </header>
  )
}

