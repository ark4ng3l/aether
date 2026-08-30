/**
 * AETHER Keyboard Shortcuts Registry
 * Single source of truth — consumed by both the handler hook and the shortcuts overlay.
 */

export interface Shortcut {
  id: string
  key: string
  modifiers?: ('ctrl' | 'shift' | 'alt' | 'meta')[]
  label: string
  description: string
  context: 'global' | 'graph' | 'timeline' | 'console' | 'arsenal'
  action: string // action identifier dispatched to handlers
}

export const shortcuts: Shortcut[] = [
  // ── Global ────────────────────────────────────────────────────────────
  {
    id: 'cmd-palette',
    key: 'k',
    modifiers: ['ctrl'],
    label: '⌘K',
    description: 'Open command palette',
    context: 'global',
    action: 'OPEN_COMMAND_PALETTE',
  },
  {
    id: 'shortcuts-overlay',
    key: '?',
    modifiers: [],
    label: '?',
    description: 'Show keyboard shortcuts',
    context: 'global',
    action: 'OPEN_SHORTCUTS_OVERLAY',
  },
  {
    id: 'new-investigation',
    key: 'n',
    modifiers: ['ctrl', 'shift'],
    label: '⌘⇧N',
    description: 'New investigation',
    context: 'global',
    action: 'NEW_INVESTIGATION',
  },
  {
    id: 'toggle-theme',
    key: 't',
    modifiers: ['ctrl', 'shift'],
    label: '⌘⇧T',
    description: 'Toggle theme (light/dark)',
    context: 'global',
    action: 'TOGGLE_THEME',
  },
  {
    id: 'toggle-sidebar',
    key: 'b',
    modifiers: ['ctrl'],
    label: '⌘B',
    description: 'Toggle left sidebar',
    context: 'global',
    action: 'TOGGLE_SIDEBAR',
  },
  {
    id: 'go-overview',
    key: '1',
    modifiers: ['ctrl'],
    label: '⌘1',
    description: 'Go to Overview',
    context: 'global',
    action: 'GO_TAB_OVERVIEW',
  },
  {
    id: 'go-graph',
    key: '2',
    modifiers: ['ctrl'],
    label: '⌘2',
    description: 'Go to Graph',
    context: 'global',
    action: 'GO_TAB_GRAPH',
  },
  {
    id: 'go-timeline',
    key: '3',
    modifiers: ['ctrl'],
    label: '⌘3',
    description: 'Go to Timeline',
    context: 'global',
    action: 'GO_TAB_TIMELINE',
  },
  {
    id: 'go-map',
    key: '4',
    modifiers: ['ctrl'],
    label: '⌘4',
    description: 'Go to Map',
    context: 'global',
    action: 'GO_TAB_MAP',
  },
  {
    id: 'go-arsenal',
    key: '5',
    modifiers: ['ctrl'],
    label: '⌘5',
    description: 'Go to Arsenal',
    context: 'global',
    action: 'GO_TAB_ARSENAL',
  },
  {
    id: 'go-vision',
    key: '6',
    modifiers: ['ctrl'],
    label: '⌘6',
    description: 'Go to Vision',
    context: 'global',
    action: 'GO_TAB_VISION',
  },
  {
    id: 'go-dossier',
    key: '7',
    modifiers: ['ctrl'],
    label: '⌘7',
    description: 'Go to Dossier',
    context: 'global',
    action: 'GO_TAB_DOSSIER',
  },
  {
    id: 'go-console',
    key: '8',
    modifiers: ['ctrl'],
    label: '⌘8',
    description: 'Go to Console',
    context: 'global',
    action: 'GO_TAB_CONSOLE',
  },
  {
    id: 'escape',
    key: 'Escape',
    modifiers: [],
    label: 'Esc',
    description: 'Close overlay / deselect',
    context: 'global',
    action: 'ESCAPE',
  },

  // ── Graph ─────────────────────────────────────────────────────────────
  {
    id: 'graph-search',
    key: 'f',
    modifiers: ['ctrl'],
    label: '⌘F',
    description: 'Search entities in graph',
    context: 'graph',
    action: 'GRAPH_SEARCH',
  },
  {
    id: 'graph-fit',
    key: '0',
    modifiers: ['ctrl'],
    label: '⌘0',
    description: 'Fit graph to viewport',
    context: 'graph',
    action: 'GRAPH_FIT',
  },
  {
    id: 'graph-relayout',
    key: 'l',
    modifiers: ['ctrl', 'shift'],
    label: '⌘⇧L',
    description: 'Re-run layout',
    context: 'graph',
    action: 'GRAPH_RELAYOUT',
  },

  // ── Console ───────────────────────────────────────────────────────────
  {
    id: 'console-clear',
    key: 'l',
    modifiers: ['ctrl'],
    label: '⌘L',
    description: 'Clear console logs',
    context: 'console',
    action: 'CONSOLE_CLEAR',
  },
  {
    id: 'console-toggle-view',
    key: 'v',
    modifiers: ['ctrl', 'shift'],
    label: '⌘⇧V',
    description: 'Toggle raw/structured view',
    context: 'console',
    action: 'CONSOLE_TOGGLE_VIEW',
  },
]

export function getShortcutsByContext(context: Shortcut['context']): Shortcut[] {
  return shortcuts.filter((s) => s.context === context)
}

export function getGlobalShortcuts(): Shortcut[] {
  return shortcuts.filter((s) => s.context === 'global')
}
