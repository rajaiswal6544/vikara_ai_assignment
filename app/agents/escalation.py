"""Escalation Agent — packages context and routes to human operator queue."""

from __future__ import annotations

import uuid
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.logger import get_logger
from app.models import (
    AgentResponse,
    ConversationState,
    EscalationPackage,
    Priority,
)

logger = get_logger(__name__)

ESCALATION_SYSTEM = """You are the Escalation Agent for CloudDash support.

Your job is to:
1. Acknowledge the customer empathetically.
2. Confirm that you are escalating their case to a human specialist.
3. Give them a ticket reference number.
4. Set expectations on response time.

CONVERSATION SUMMARY:
{summary}

PRIORITY: {priority}
TICKET ID: {ticket_id}

Write a warm, professional message confirming the escalation. Be specific about what was discussed."""

PRIORITY_KEYWORDS: dict[Priority, list[str]] = {
    Priority.CRITICAL: ["data loss", "security breach", "breach", "outage", "down completely"],
    Priority.HIGH: ["payment failure", "cannot login", "all alerts broken", "production down"],
    Priority.MEDIUM: ["billing dispute", "integration broken", "dashboard missing"],
    Priority.LOW: ["feature request", "question", "how do i", "wondering"],
}

TEAM_MAP: dict[str, str] = {
    "technical": "technical_ops",
    "billing": "billing_ops",
    "account": "account_ops",
    "general": "technical_ops",
}

# In-memory human queue (simulates a ticketing system)
HUMAN_QUEUE: list[EscalationPackage] = []


class EscalationAgent(BaseAgent):
    def __init__(self, config: dict[str, Any], client: AsyncOpenAI, rag_pipeline: Any | None = None) -> None:
        super().__init__("escalation", config, client, rag_pipeline)

    async def process(self, state: ConversationState, message: str) -> AgentResponse:
        summary = await self._generate_summary(state)
        priority = self._classify_priority(state, message)
        recommended_team = TEAM_MAP.get(
            state.entities.get("product_area", "general"), "technical_ops"
        )
        ticket_id = f"CLD-{uuid.uuid4().hex[:6].upper()}"

        package = EscalationPackage(
            trace_id=state.trace_id,
            conversation_id=state.id,
            priority=priority,
            summary=summary,
            customer_id=state.entities.get("customer_id"),
            full_history=state.messages,
            recommended_team=recommended_team,
        )
        HUMAN_QUEUE.append(package)

        system = ESCALATION_SYSTEM.format(
            summary=summary,
            priority=priority.value,
            ticket_id=ticket_id,
        )
        history = self._build_history_text(state)
        history.append({"role": "user", "content": message})

        content = await self._call_llm(system=system, messages=history, max_tokens=512)

        logger.info(
            "escalation_created",
            trace_id=state.trace_id,
            ticket_id=ticket_id,
            priority=priority.value,
            team=recommended_team,
            queue_depth=len(HUMAN_QUEUE),
        )

        return AgentResponse(
            content=content,
            escalation_required=True,
            entities_extracted={"ticket_id": ticket_id, "priority": priority.value},
        )

    async def _generate_summary(self, state: ConversationState) -> str:
        if not state.messages:
            return "New conversation with no prior messages."

        history_text = "\n".join(
            f"{m.role.value.upper()}: {m.content}" for m in state.messages[-10:]
        )
        prompt = (
            f"Summarize this customer support conversation in 3 concise sentences "
            f"for a human support agent:\n\n{history_text}"
        )
        return await self._call_llm(
            system="You are a support operations assistant. Write concise summaries.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )

    def _classify_priority(self, state: ConversationState, message: str) -> Priority:
        full_text = " ".join(m.content.lower() for m in state.messages) + " " + message.lower()
        for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            if any(kw in full_text for kw in PRIORITY_KEYWORDS.get(priority, [])):
                return priority
        return Priority.MEDIUM
