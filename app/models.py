"""Pydantic data models for the entire system."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AgentType(str, Enum):
    TRIAGE = "triage"
    TECHNICAL = "technical"
    BILLING = "billing"
    ESCALATION = "escalation"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageRole(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


# ---------------------------------------------------------------------------
# Core message / conversation models
# ---------------------------------------------------------------------------


class KBSource(BaseModel):
    chunk_id: str
    document: str
    section: str
    excerpt: str


class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    agent: AgentType | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sources: list[KBSource] = Field(default_factory=list)


class HandoverEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    from_agent: AgentType
    to_agent: AgentType
    reason: str
    context_snapshot: str
    entity_snapshot: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    failure_reason: str | None = None


class ConversationState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = Field(default_factory=lambda: f"conv-{uuid.uuid4().hex[:8]}")
    messages: list[Message] = Field(default_factory=list)
    active_agent: AgentType = AgentType.TRIAGE
    entities: dict[str, Any] = Field(default_factory=dict)
    handover_log: list[HandoverEvent] = Field(default_factory=list)
    status: ConversationStatus = ConversationStatus.ACTIVE
    failed_attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Agent response / request models
# ---------------------------------------------------------------------------


class HandoverRequest(BaseModel):
    to_agent: AgentType
    reason: str


class AgentResponse(BaseModel):
    content: str
    sources: list[KBSource] = Field(default_factory=list)
    routing_decision: AgentType | None = None  # used by TriageAgent
    handover_request: HandoverRequest | None = None
    escalation_required: bool = False
    entities_extracted: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Handover payload
# ---------------------------------------------------------------------------


class HandoverPayload(BaseModel):
    trace_id: str
    from_agent: AgentType
    to_agent: AgentType
    reason: str
    conversation_history: list[Message]
    extracted_entities: dict[str, Any]
    context_snapshot: str


# ---------------------------------------------------------------------------
# Escalation package
# ---------------------------------------------------------------------------


class EscalationPackage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str
    conversation_id: str
    priority: Priority
    summary: str
    customer_id: str | None
    full_history: list[Message]
    recommended_team: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------


class StartConversationRequest(BaseModel):
    customer_id: str | None = None
    initial_message: str | None = None


class StartConversationResponse(BaseModel):
    conversation_id: str
    trace_id: str
    message: str | None = None


class SendMessageRequest(BaseModel):
    message: str


class SendMessageResponse(BaseModel):
    conversation_id: str
    trace_id: str
    response: str
    agent: AgentType
    sources: list[KBSource] = Field(default_factory=list)
    escalated: bool = False
    ticket_id: str | None = None


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    trace_id: str
    status: ConversationStatus
    messages: list[Message]
    active_agent: AgentType


class HandoverLogResponse(BaseModel):
    conversation_id: str
    trace_id: str
    handovers: list[HandoverEvent]
