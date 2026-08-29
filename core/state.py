from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
import uuid


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class EntityType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    DOMAIN = "domain"
    IP_ADDRESS = "ip_address"
    EMAIL = "email"
    SOCIAL_HANDLE = "social_handle"
    IMAGE = "image"
    DOCUMENT = "document"
    ARTIFACT = "artifact"
    UNKNOWN = "unknown"


class RelationshipType(str, Enum):
    OWNED_BY = "owned_by"
    RESOLVES_TO = "resolves_to"
    ASSOCIATED_WITH = "associated_with"
    AUTHORED = "authored"
    MEMBER_OF = "member_of"
    LOCATED_IN = "located_in"
    SUBDOMAIN_OF = "subdomain_of"
    HOSTED_ON = "hosted_on"


class Entity(BaseModel):
    model_config = ConfigDict(frozen=True)  # Immutable for hashability in sets/graphs

    id: str = Field(..., description="Unique identifier (e.g., UUID or normalized string)")
    type: EntityType
    properties: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    first_seen: datetime = Field(default_factory=_now_utc)


class Relationship(BaseModel):
    source_id: str
    target_id: str
    rel_type: RelationshipType
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvestigationStatus(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    PLANNING = "planning"
    COLLECTING = "collecting"
    REASONING = "reasoning"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class TaskStep(BaseModel):
    """Structured record of an executed task step within an investigation."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    tool_name: str
    params: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = ""
    status: str = "completed"  # running, completed, failed, rejected
    verdict: Optional[str] = None  # CONFIRMED, PLAUSIBLE, REJECTED
    confidence: float = 0.5
    output_summary: str = ""
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=_now_utc)


class AgentState(BaseModel):
    """The live execution state of an active investigation."""
    investigation_id: str
    project_id: str = ""
    project_name: str = ""
    target_seed: str
    target_type: EntityType = EntityType.UNKNOWN
    context_briefing: str = ""  # User-supplied context/briefing
    status: InvestigationStatus = InvestigationStatus.IDLE
    discovered_entities: List[Entity] = Field(default_factory=list)
    active_hypotheses: List[str] = Field(default_factory=list)
    current_task_stack: List[str] = Field(default_factory=list)  # Queued/pending tasks
    completed_tasks: List[TaskStep] = Field(default_factory=list)  # Historical task log
    active_task: Optional[TaskStep] = None  # Currently running task
    dossier: str = ""
    last_error: Optional[str] = None
    start_time: datetime = Field(default_factory=_now_utc)
    finished_time: Optional[datetime] = None

    def add_entity(self, entity: Entity):
        if not any(e.id == entity.id for e in self.discovered_entities):
            self.discovered_entities.append(entity)

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Lookup a discovered entity by ID. Returns None if not found."""
        return next((e for e in self.discovered_entities if e.id == entity_id), None)


class Project(BaseModel):
    """Persistent representation of an intelligence investigation project."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str
    target_seed: str
    target_type: EntityType = EntityType.UNKNOWN
    context_briefing: str = ""  # Guidance / background info for LLM
    status: InvestigationStatus = InvestigationStatus.IDLE
    entities_count: int = 0
    completed_tasks_count: int = 0
    dossier: str = ""
    state: Optional[AgentState] = None
    created_at: datetime = Field(default_factory=_now_utc)
    updated_at: datetime = Field(default_factory=_now_utc)
    finished_at: Optional[datetime] = None


class ProjectSummary(BaseModel):
    """Lightweight project summary for dashboard listing."""
    id: str
    name: str
    target_seed: str
    target_type: EntityType
    context_briefing: str
    status: InvestigationStatus
    entities_count: int
    completed_tasks_count: int
    has_dossier: bool
    created_at: datetime
    updated_at: datetime
