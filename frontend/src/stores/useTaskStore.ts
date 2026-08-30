import { create } from 'zustand'
import { TaskStep } from '../types/api'

interface TaskState {
  completedTasks: TaskStep[]
  activeTask: TaskStep | null
  pendingTasks: string[]
  activeHypotheses: string[]
  toolFilter: string
  statusFilter: string

  setTasks: (data: {
    completed_tasks: TaskStep[]
    active_task: TaskStep | null
    pending_tasks: string[]
    active_hypotheses: string[]
  }) => void
  addCompletedTask: (task: TaskStep) => void
  setActiveTask: (task: TaskStep | null) => void
  setPendingTasks: (tasks: string[]) => void
  setToolFilter: (tool: string) => void
  setStatusFilter: (status: string) => void
  clearTasks: () => void
}

export const useTaskStore = create<TaskState>((set) => ({
  completedTasks: [],
  activeTask: null,
  pendingTasks: [],
  activeHypotheses: [],
  toolFilter: 'all',
  statusFilter: 'all',

  setTasks: (data) =>
    set({
      completedTasks: data.completed_tasks || [],
      activeTask: data.active_task || null,
      pendingTasks: data.pending_tasks || [],
      activeHypotheses: data.active_hypotheses || [],
    }),

  addCompletedTask: (task) =>
    set((state) => ({
      completedTasks: [task, ...state.completedTasks.filter((t) => t.id !== task.id)],
      activeTask: state.activeTask?.id === task.id ? null : state.activeTask,
    })),

  setActiveTask: (task) => set({ activeTask: task }),
  setPendingTasks: (tasks) => set({ pendingTasks: tasks }),
  setToolFilter: (toolFilter) => set({ toolFilter }),
  setStatusFilter: (statusFilter) => set({ statusFilter }),
  clearTasks: () =>
    set({
      completedTasks: [],
      activeTask: null,
      pendingTasks: [],
      activeHypotheses: [],
      toolFilter: 'all',
      statusFilter: 'all',
    }),
}))
