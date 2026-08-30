import { EntityType, RelationshipType, InvestigationStatus, ConfidenceSignal } from './api'

export type WebSocketEventType =
  | 'investigation_started'
  | 'status_change'
  | 'entity_discovered'
  | 'entity_updated'
  | 'relationship_added'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'tool_skipped_degraded'
  | 'token_stream'
  | 'dossier_ready'
  | 'investigation_completed'

export interface BaseWSEvent {
  event: WebSocketEventType
  timestamp?: string
}

export interface InvestigationStartedEvent extends BaseWSEvent {
  event: 'investigation_started'
  seed: string
  project_id: string
  project_name: string
  context_briefing?: string
}

export interface StatusChangeEvent extends BaseWSEvent {
  event: 'status_change'
  status: InvestigationStatus
  phase?: string
}

export interface EntityDiscoveredEvent extends BaseWSEvent {
  event: 'entity_discovered'
  id: string
  type: EntityType
  properties: Record<string, any>
  confidence?: number
  confidence_signals?: ConfidenceSignal[]
}

export interface EntityUpdatedEvent extends BaseWSEvent {
  event: 'entity_updated'
  id: string
  confidence: number
  confidence_signals: ConfidenceSignal[]
  corroboration_count: number
}

export interface RelationshipAddedEvent extends BaseWSEvent {
  event: 'relationship_added'
  source_id: string
  target_id: string
  rel_type: RelationshipType
  confidence: number
}

export interface TaskStartedEvent extends BaseWSEvent {
  event: 'task_started'
  task_id: string
  tool?: string
  tool_name?: string
  params?: Record<string, any>
  reasoning?: string
  pending_count?: number
}

export interface TaskCompletedEvent extends BaseWSEvent {
  event: 'task_completed'
  task_id: string
  tool?: string
  tool_name?: string
  status: 'completed' | 'failed' | 'rejected'
  verdict?: 'CONFIRMED' | 'PLAUSIBLE' | 'REJECTED'
  confidence: number
  critic_reasoning?: string
  confidence_breakdown?: Record<string, any>
  duration?: number
  summary?: string
  produced_entity_ids?: string[]
  total_completed?: number
  pending_count?: number
}

export interface TaskFailedEvent extends BaseWSEvent {
  event: 'task_failed'
  task_id: string
  tool?: string
  error: string
  duration?: number
}

export interface ToolSkippedDegradedEvent extends BaseWSEvent {
  event: 'tool_skipped_degraded'
  tool_name: string
  reason: string
}

export interface TokenStreamEvent extends BaseWSEvent {
  event: 'token_stream'
  task_id?: string
  token: string
}

export interface DossierReadyEvent extends BaseWSEvent {
  event: 'dossier_ready'
  project_id: string
}

export interface InvestigationCompletedEvent extends BaseWSEvent {
  event: 'investigation_completed'
  project_id: string
  entities_count: number
  duration_seconds: number
}

export type AnyWebSocketEvent =
  | InvestigationStartedEvent
  | StatusChangeEvent
  | EntityDiscoveredEvent
  | EntityUpdatedEvent
  | RelationshipAddedEvent
  | TaskStartedEvent
  | TaskCompletedEvent
  | TaskFailedEvent
  | ToolSkippedDegradedEvent
  | TokenStreamEvent
  | DossierReadyEvent
  | InvestigationCompletedEvent
