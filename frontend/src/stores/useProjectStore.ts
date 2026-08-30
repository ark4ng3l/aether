import { create } from 'zustand'
import { Project, ProjectSummary, InvestigationStatus } from '../types/api'

export type TabType =
  | 'overview'
  | 'graph'
  | 'timeline'
  | 'map'
  | 'arsenal'
  | 'vision'
  | 'dossier'
  | 'console'

interface ProjectState {
  projects: ProjectSummary[]
  activeProjectId: string | null
  activeProject: Project | null
  activeTab: TabType
  systemHealth: 'online' | 'degraded' | 'offline'
  selectedEntityId: string | null
  isNewModalOpen: boolean
  isPurgeModalOpen: boolean
  isCodeReviewOpen: boolean
  isSettingsOpen: boolean
  activeDraftId: string | null
  sidebarCollapsed: boolean

  // Actions
  setProjects: (projects: ProjectSummary[]) => void
  setActiveProjectId: (id: string | null) => void
  setActiveProject: (project: Project | null) => void
  setActiveTab: (tab: TabType) => void
  setSystemHealth: (health: 'online' | 'degraded' | 'offline') => void
  setSelectedEntityId: (entityId: string | null) => void
  setIsNewModalOpen: (open: boolean) => void
  setIsPurgeModalOpen: (open: boolean) => void
  setIsCodeReviewOpen: (open: boolean, draftId?: string) => void
  setIsSettingsOpen: (open: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  updateProjectStatus: (projectId: string, status: InvestigationStatus) => void
  incrementEntityCount: (projectId: string) => void
}

const storedCollapsed = typeof window !== 'undefined'
  ? localStorage.getItem('aether_sidebar_collapsed') === 'true'
  : false

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeProjectId: null,
  activeProject: null,
  activeTab: 'overview',
  systemHealth: 'online',
  selectedEntityId: null,
  isNewModalOpen: false,
  isPurgeModalOpen: false,
  isCodeReviewOpen: false,
  isSettingsOpen: false,
  activeDraftId: null,
  sidebarCollapsed: storedCollapsed,

  setProjects: (projects) => set({ projects }),
  setActiveProjectId: (id) => set({ activeProjectId: id }),
  setActiveProject: (project) => set({ activeProject: project }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSystemHealth: (health) => set({ systemHealth: health }),
  setSelectedEntityId: (entityId) => set({ selectedEntityId: entityId }),
  setIsNewModalOpen: (open) => set({ isNewModalOpen: open }),
  setIsPurgeModalOpen: (open) => set({ isPurgeModalOpen: open }),
  setIsCodeReviewOpen: (open, draftId) => set({ isCodeReviewOpen: open, activeDraftId: draftId || null }),
  setIsSettingsOpen: (open) => set({ isSettingsOpen: open }),
  setSidebarCollapsed: (collapsed) => {
    localStorage.setItem('aether_sidebar_collapsed', String(collapsed))
    set({ sidebarCollapsed: collapsed })
  },

  updateProjectStatus: (projectId, status) => {
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, status } : p
      ),
      activeProject:
        state.activeProject?.id === projectId
          ? { ...state.activeProject, status }
          : state.activeProject,
    }))
  },

  incrementEntityCount: (projectId) => {
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, entities_count: p.entities_count + 1 } : p
      ),
      activeProject:
        state.activeProject?.id === projectId
          ? { ...state.activeProject, entities_count: state.activeProject.entities_count + 1 }
          : state.activeProject,
    }))
  },
}))
