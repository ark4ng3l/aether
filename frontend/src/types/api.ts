export type EntityType =
  | 'person'
  | 'company'
  | 'domain'
  | 'ip_address'
  | 'email'
  | 'social_handle'
  | 'image'
  | 'document'
  | 'artifact'
  | 'phone'
  | 'hash'
  | 'cve'
  | 'unknown'

export type RelationshipType =
  | 'owned_by'
  | 'resolves_to'
  | 'associated_with'
  | 'authored'
  | 'member_of'
  | 'located_in'
  | 'subdomain_of'
  | 'hosted_on'

export type InvestigationStatus =
  | 'idle'
  | 'queued'
  | 'planning'
  | 'collecting'
  | 'reasoning'
  | 'verifying'
  | 'synthesizing'
  | 'completed'
  | 'failed'
  | 'stopped'

export interface ConfidenceSignal {
  source_tool: string
  weight: number
  note: string
}

export interface Entity {
  id: string
  type: EntityType
  properties: Record<string, any>
  confidence: number
  confidence_signals: ConfidenceSignal[]
  corroboration_count: number
  first_seen: string
  last_updated: string
}

export interface Relationship {
  source_id: string
  target_id: string
  rel_type: RelationshipType
  confidence: number
  metadata: Record<string, any>
}

export interface TaskStep {
  id: string
  tool_name: string
  params: Record<string, any>
  reasoning: string
  critic_reasoning?: string
  status: 'running' | 'completed' | 'failed' | 'rejected'
  verdict?: 'CONFIRMED' | 'PLAUSIBLE' | 'REJECTED' | null
  confidence: number
  confidence_breakdown?: {
    source_tool?: string
    source_reliability?: number
    deterministic_format_score?: number
    corroboration_count?: number
    corroboration_bonus?: number
    critic_confidence?: number
    final_score?: number
    tier?: string
  }
  output_summary: string
  duration_seconds: number
  timestamp: string
  produced_entity_ids: string[]
}

export interface AgentState {
  investigation_id: string
  project_id: string
  project_name: string
  target_seed: string
  target_type: EntityType
  context_briefing: string
  status: InvestigationStatus
  discovered_entities: Entity[]
  active_hypotheses: string[]
  current_task_stack: string[]
  completed_tasks: TaskStep[]
  active_task?: TaskStep | null
  dossier: string
  last_error?: string | null
  start_time: string
  finished_time?: string | null
}

export interface Project {
  id: string
  name: string
  target_seed: string
  target_type: EntityType
  context_briefing: string
  status: InvestigationStatus
  entities_count: number
  completed_tasks_count: number
  dossier: string
  state?: AgentState | null
  created_at: string
  updated_at: string
  finished_at?: string | null
}

export interface ProjectSummary {
  id: string
  name: string
  target_seed: string
  target_type: EntityType
  context_briefing: string
  status: InvestigationStatus
  entities_count: number
  completed_tasks_count: number
  has_dossier: boolean
  created_at: string
  updated_at: string
}

export interface ToolDefinition {
  name: string
  description: string
  params: Record<string, any>
  category?: string
  is_dynamic?: boolean
  status?: string
  stage_id?: string
  source_code?: string
  ast_safe?: boolean
}

export interface MetricsData {
  uptime_seconds: number
  total_tool_calls: number
  success_rate: number
  avg_latency_ms: number
  tool_latencies: Record<string, number>
  active_semaphores?: Record<string, number>
}

export interface SettingsData {
  LLM_PROVIDER?: 'ollama' | 'openai_compatible' | string
  OLLAMA_BASE_URL: string
  CUSTOM_API_BASE_URL?: string
  CUSTOM_API_KEY?: string
  MODEL_AGGRESSIVE_FAST: string
  MODEL_VLM: string
  MODEL_FAST: string
  MODEL_CRITIC: string
  MODEL_DEEP: string
  MODEL_DEEP_FALLBACK: string
  MODEL_DEEP_31B: string
  HYPOTHESIS_RECURSION_LIMIT: number
  MAX_SEARCH_DEPTH: number
  ENTITY_CONFIDENCE_THRESHOLD: number
  REASONING_TEMPERATURE: number
  PLANNER_TEMPERATURE: number
  CRITIC_TEMPERATURE: number
  MAX_CONCURRENT_HEAVY_MODELS: number
  VRAM_ARBITRATION_ENABLED: boolean
  available_ollama_models?: string[]
}

