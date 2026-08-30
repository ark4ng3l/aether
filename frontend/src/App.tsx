import React, { useEffect, useState, Suspense, lazy } from 'react'
import { TopBar } from './features/shell/TopBar'
import { LeftRail } from './features/shell/LeftRail'
import { TabStrip } from './features/shell/TabStrip'
import { CommandPalette } from './features/command-palette/CommandPalette'
import { useCommandPaletteStore } from './features/command-palette/useCommandPaletteStore'
import { ShortcutsOverlay } from './features/shortcuts/ShortcutsOverlay'
import { OnboardingTour } from './features/onboarding/OnboardingTour'
import { SettingsModal } from './features/settings/SettingsModal'
import { NewInvestigationModal } from './features/modals/NewInvestigationModal'
import { ConfirmPurgeModal } from './features/modals/ConfirmPurgeModal'
import { ToastContainer } from './components/ui/Toast'

import { useAuthStore } from './stores/useAuthStore'
import { useProjectStore } from './stores/useProjectStore'
import { useGraphStore } from './stores/useGraphStore'
import { useTaskStore } from './stores/useTaskStore'
import { useLiveEvents } from './hooks/useLiveEvents'
import { useShortcuts } from './shortcuts/useShortcuts'
import { api } from './api/endpoints'


// Lazy load complex tabs for code-splitting
const OverviewTab = lazy(() =>
  import('./features/overview/OverviewTab').then((m) => ({ default: m.OverviewTab }))
)
const GraphTab = lazy(() =>
  import('./features/graph/GraphTab').then((m) => ({ default: m.GraphTab }))
)
const TimelineTab = lazy(() =>
  import('./features/timeline/TimelineTab').then((m) => ({ default: m.TimelineTab }))
)
const MapTab = lazy(() =>
  import('./features/map/MapTab').then((m) => ({ default: m.MapTab }))
)
const ArsenalTab = lazy(() =>
  import('./features/arsenal/ArsenalTab').then((m) => ({ default: m.ArsenalTab }))
)
const VisionTab = lazy(() =>
  import('./features/vision/VisionTab').then((m) => ({ default: m.VisionTab }))
)
const DossierTab = lazy(() =>
  import('./features/dossier/DossierTab').then((m) => ({ default: m.DossierTab }))
)
const ConsoleTab = lazy(() =>
  import('./features/console/ConsoleTab').then((m) => ({ default: m.ConsoleTab }))
)

export const App: React.FC = () => {
  const { initToken, isInitialized } = useAuthStore()
  const {
    projects,
    activeProjectId,
    activeTab,
    setProjects,
    setActiveProjectId,
    setActiveProject,
    sidebarCollapsed,
    setSidebarCollapsed,
  } = useProjectStore()

  const { open: openCommandPalette } = useCommandPaletteStore()
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false)

  // Initialize global & per-project WebSocket stream
  useLiveEvents()

  // Register global keyboard shortcuts
  useShortcuts({
    onOpenCommandPalette: openCommandPalette,
    onOpenShortcutsOverlay: () => setIsShortcutsOpen(true),
    onToggleSidebar: () => setSidebarCollapsed(!sidebarCollapsed),
    onEscape: () => setIsShortcutsOpen(false),
  })

  // Initialize Auth Token on boot
  useEffect(() => {
    initToken()
  }, [initToken])

  // Load project list once token is ready
  useEffect(() => {
    if (!isInitialized) return
    api
      .listProjects()
      .then((list) => {
        setProjects(list)
        if (!activeProjectId && list.length > 0) {
          setActiveProjectId(list[0].id)
        }
      })
      .catch((err) => console.error('Failed to bootstrap projects:', err))
  }, [isInitialized, setProjects, activeProjectId, setActiveProjectId])

  // Load active project full details, graph nodes, and tasks
  useEffect(() => {
    if (!activeProjectId) {
      setActiveProject(null)
      useGraphStore.getState().clearGraph()
      useTaskStore.getState().clearTasks()
      return
    }

    // 1. Fetch project metadata
    api
      .getProject(activeProjectId)
      .then((proj) => {
        setActiveProject(proj)
      })
      .catch((err) => console.error('Failed to load project details:', err))

    // 2. Fetch graph topology nodes & edges for immediate rendering
    api
      .getProjectGraph(activeProjectId)
      .then((graph) => {
        if (graph?.nodes) {
          useGraphStore.getState().setGraphData({ nodes: graph.nodes, edges: graph.edges || [] })
        }
      })
      .catch((err) => console.error('Failed to load project graph:', err))


    // 3. Fetch completed & active tasks
    api
      .getProjectTasks(activeProjectId)
      .then((tasks) => {
        if (tasks) {
          useTaskStore.getState().setTasks(tasks)
        }
      })
      .catch((err) => console.error('Failed to load project tasks:', err))
  }, [activeProjectId, setActiveProject])


  const renderActiveTab = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab />
      case 'graph':
        return <GraphTab />
      case 'timeline':
        return <TimelineTab />
      case 'map':
        return <MapTab />
      case 'arsenal':
        return <ArsenalTab />
      case 'vision':
        return <VisionTab />
      case 'dossier':
        return <DossierTab />
      case 'console':
        return <ConsoleTab />
      default:
        return <OverviewTab />
    }
  }

  return (
    <div className="h-screen w-screen bg-bg-canvas text-text-primary flex flex-col overflow-hidden font-sans select-none antialiased">
      {/* Shell TopBar */}
      <TopBar onOpenCommandPalette={openCommandPalette} />

      {/* Main Workspace Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Rail */}
        <LeftRail onOpenShortcuts={() => setIsShortcutsOpen(true)} />

        {/* Workspace Central Viewport */}
        <main className="flex-1 flex flex-col min-w-0 bg-bg-canvas relative overflow-hidden">
          <TabStrip />
          <div className="flex-1 flex flex-col overflow-hidden relative">
            <Suspense
              fallback={
                <div className="flex-1 flex items-center justify-center text-xs font-mono-data text-text-tertiary">
                  Loading view...
                </div>
              }
            >
              {renderActiveTab()}
            </Suspense>
          </div>
        </main>
      </div>

      {/* Cross-Cutting Modals & Overlays */}
      <CommandPalette />
      <ShortcutsOverlay
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />
      <OnboardingTour />
      <SettingsModal />
      <NewInvestigationModal />
      <ConfirmPurgeModal />
      <ToastContainer />
    </div>
  )
}

export default App
