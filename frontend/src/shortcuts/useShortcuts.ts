import { useEffect } from 'react'
import { shortcuts, Shortcut } from './registry'
import { useProjectStore, TabType } from '../stores/useProjectStore'
import { useThemeStore } from '../stores/useThemeStore'
import { useConsoleStore } from '../stores/useConsoleStore'

type ActionHandler = () => void

interface ShortcutsConfig {
  onOpenCommandPalette?: () => void
  onOpenShortcutsOverlay?: () => void
  onNewInvestigation?: () => void
  onToggleSidebar?: () => void
  onEscape?: () => void
  onGraphSearch?: () => void
  onGraphFit?: () => void
  onGraphRelayout?: () => void
}

export function useShortcuts(config: ShortcutsConfig = {}) {
  const setActiveTab = useProjectStore((s) => s.setActiveTab)
  const activeTab = useProjectStore((s) => s.activeTab)
  const setIsNewModalOpen = useProjectStore((s) => s.setIsNewModalOpen)
  const toggleTheme = useThemeStore((s) => s.setMode)
  const themeMode = useThemeStore((s) => s.mode)
  const clearLogs = useConsoleStore((s) => s.clearLogs)
  const setViewMode = useConsoleStore((s) => s.setViewMode)
  const viewMode = useConsoleStore((s) => s.viewMode)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Don't capture when typing in inputs/textareas
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        // Allow Escape even in inputs
        if (e.key !== 'Escape') return
      }

      for (const shortcut of shortcuts) {
        if (!matchesShortcut(e, shortcut)) continue
        // Check context
        if (shortcut.context !== 'global' && shortcut.context !== activeTab) continue

        e.preventDefault()
        e.stopPropagation()
        dispatchAction(shortcut.action)
        return
      }
    }

    function matchesShortcut(e: KeyboardEvent, s: Shortcut): boolean {
      const mods = s.modifiers || []
      const ctrlMatch = mods.includes('ctrl') ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey)
      const shiftMatch = mods.includes('shift') ? e.shiftKey : !e.shiftKey
      const altMatch = mods.includes('alt') ? e.altKey : !e.altKey
      return e.key.toLowerCase() === s.key.toLowerCase() && ctrlMatch && shiftMatch && altMatch
    }

    const tabMap: Record<string, TabType> = {
      GO_TAB_OVERVIEW: 'overview',
      GO_TAB_GRAPH: 'graph',
      GO_TAB_TIMELINE: 'timeline',
      GO_TAB_MAP: 'map',
      GO_TAB_ARSENAL: 'arsenal',
      GO_TAB_VISION: 'vision',
      GO_TAB_DOSSIER: 'dossier',
      GO_TAB_CONSOLE: 'console',
    }

    function dispatchAction(action: string) {
      // Tab navigation
      if (tabMap[action]) {
        setActiveTab(tabMap[action])
        return
      }

      const handlers: Record<string, ActionHandler> = {
        OPEN_COMMAND_PALETTE: () => config.onOpenCommandPalette?.(),
        OPEN_SHORTCUTS_OVERLAY: () => config.onOpenShortcutsOverlay?.(),
        NEW_INVESTIGATION: () => {
          config.onNewInvestigation?.()
          setIsNewModalOpen(true)
        },
        TOGGLE_THEME: () => toggleTheme(themeMode === 'dark' ? 'light' : 'dark'),
        TOGGLE_SIDEBAR: () => config.onToggleSidebar?.(),
        ESCAPE: () => config.onEscape?.(),
        GRAPH_SEARCH: () => config.onGraphSearch?.(),
        GRAPH_FIT: () => config.onGraphFit?.(),
        GRAPH_RELAYOUT: () => config.onGraphRelayout?.(),
        CONSOLE_CLEAR: () => clearLogs(),
        CONSOLE_TOGGLE_VIEW: () => setViewMode(viewMode === 'raw' ? 'structured' : 'raw'),
      }

      handlers[action]?.()
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [activeTab, config, setActiveTab, setIsNewModalOpen, toggleTheme, themeMode, clearLogs, setViewMode, viewMode])
}
