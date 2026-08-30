import { apiFetch } from './client'
import {
  Project,
  ProjectSummary,
  ToolDefinition,
  MetricsData,
  SettingsData,
  EntityType,
  TaskStep,
} from '../types/api'
import { GraphData } from '../types/graph'

export const api = {
  // ── Project Management ──────────────────────────────────────────────────
  async listProjects(): Promise<ProjectSummary[]> {
    const res = await apiFetch<{ projects: ProjectSummary[] }>('/api/projects')
    return res.projects
  },

  async createProject(params: {
    name?: string
    target_seed: string
    target_type?: EntityType
    context_briefing?: string
  }): Promise<Project> {
    const res = await apiFetch<{ status: string; project: Project }>('/api/projects', {
      method: 'POST',
      body: JSON.stringify(params),
    })
    return res.project
  },

  async getProject(id: string): Promise<Project> {
    const res = await apiFetch<{ project: Project }>(`/api/projects/${id}`)
    return res.project
  },

  async updateProject(
    id: string,
    params: {
      name?: string
      target_seed?: string
      target_type?: EntityType
      context_briefing?: string
    }
  ): Promise<Project> {
    const res = await apiFetch<{ status: string; project: Project }>(`/api/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(params),
    })
    return res.project
  },

  async deleteProject(id: string): Promise<boolean> {
    const res = await apiFetch<{ status: string; deleted: boolean }>(`/api/projects/${id}`, {
      method: 'DELETE',
    })
    return res.deleted
  },

  async runProject(id: string): Promise<boolean> {
    const res = await apiFetch<{ status: string; project_id: string }>(`/api/projects/${id}/run`, {
      method: 'POST',
    })
    return res.status === 'started' || res.status === 'already_running'
  },

  async stopProject(id: string): Promise<boolean> {
    const res = await apiFetch<{ status: string }>(`/api/projects/${id}/stop`, {
      method: 'POST',
    })
    return res.status === 'stopped'
  },

  async injectTask(
    projectId: string,
    toolName: string,
    params: Record<string, any>,
    reasoning?: string
  ): Promise<{ status: string }> {
    return apiFetch<{ status: string }>(`/api/projects/${projectId}/inject-task`, {
      method: 'POST',
      body: JSON.stringify({
        tool_name: toolName,
        params,
        reasoning: reasoning || 'Analyst injected task',
      }),
    })
  },

  // ── Project Artifacts & Graphs ──────────────────────────────────────────
  async getProjectGraph(id: string): Promise<GraphData> {
    return apiFetch<GraphData>(`/api/projects/${id}/graph`)
  },

  async getProjectTasks(id: string): Promise<{
    project_id: string
    status: string
    active_task: TaskStep | null
    active_hypotheses: string[]
    pending_tasks: string[]
    completed_tasks: TaskStep[]
  }> {
    return apiFetch(`/api/projects/${id}/tasks`)
  },

  async getProjectDossier(id: string): Promise<{ project_id: string; dossier: string }> {
    return apiFetch(`/api/projects/${id}/dossier`)
  },

  async getEntityProvenance(
    projectId: string,
    entityId: string
  ): Promise<{
    project_id: string
    entity_id: string
    provenance_tasks: TaskStep[]
  }> {
    return apiFetch(`/api/projects/${projectId}/entities/${encodeURIComponent(entityId)}/provenance`)
  },

  async exportDossier(id: string, format: 'pdf' | 'stix' | 'json' | 'md'): Promise<any> {
    if (format === 'stix') {
      return apiFetch(`/api/projects/${id}/export/stix`)
    }
    return apiFetch(`/api/projects/${id}/dossier/export?format=${format}`)
  },

  async getTimeline(id: string): Promise<{ project_id: string; events: any[] }> {
    return apiFetch(`/api/projects/${id}/timeline`)
  },

  // ── Tool Arsenal & Synthesis ────────────────────────────────────────────
  async listTools(): Promise<ToolDefinition[]> {
    const res = await apiFetch<{ tools: ToolDefinition[] }>('/api/tools')
    return res.tools
  },

  async executeTool(toolName: string, params: Record<string, any>): Promise<{
    tool_name: string
    execution_time_ms: number
    success: boolean
    data: any
    error?: string
  }> {
    return apiFetch('/api/tools/execute', {
      method: 'POST',
      body: JSON.stringify({ tool_name: toolName, params }),
    })
  },

  async synthesizeTool(description: string, autoRegister = false): Promise<any> {
    return apiFetch('/api/tools/synthesize', {
      method: 'POST',
      body: JSON.stringify({ description, auto_register: autoRegister }),
    })
  },

  async listStagedTools(): Promise<{ staged_tools: ToolDefinition[] }> {
    return apiFetch('/api/tools/staged')
  },

  async approveTool(stageId: string): Promise<{ status: string; tool_name: string }> {
    return apiFetch(`/api/tools/synthesize/${stageId}/approve`, {
      method: 'POST',
    })
  },

  async rejectTool(stageId: string): Promise<{ status: string }> {
    return apiFetch(`/api/tools/synthesize/${stageId}/reject`, {
      method: 'POST',
    })
  },

  // ── Image Forensics ─────────────────────────────────────────────────────
  async uploadImage(file: File): Promise<{ status: string; filename: string }> {
    const formData = new FormData()
    formData.append('file', file)
    return apiFetch('/api/upload/image', {
      method: 'POST',
      body: formData,
    })
  },

  async analyzeImage(filename: string): Promise<any> {
    return apiFetch('/api/images/analyze', {
      method: 'POST',
      body: JSON.stringify({ filename }),
    })
  },

  // ── Settings & Telemetry ────────────────────────────────────────────────
  async getSettings(): Promise<{ settings: SettingsData; available_models: string[] }> {
    const res = await apiFetch<{ settings: SettingsData; available_models?: string[] }>('/api/settings')
    return {
      settings: res.settings,
      available_models: res.available_models || [],
    }
  },

  async updateSettings(data: Partial<SettingsData>): Promise<{ status: string }> {
    return apiFetch('/api/settings', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async getMetrics(): Promise<MetricsData> {
    return apiFetch<MetricsData>('/api/metrics')
  },

  async regenerateToken(): Promise<{ status: string; token: string }> {
    return apiFetch('/api/auth/token/regenerate', {
      method: 'POST',
    })
  },

  async checkSystemUpdate(): Promise<any> {
    return apiFetch('/api/system/update/check')
  },
}
