"""Handover protocol — context preservation and agent transition logic."""

from __future__ import annotations

from datetime import datetime, timezone

from openai import AsyncOpenAI

from app.logger import get_logger
from app.models import (
    AgentType,
    ConversationState,
    HandoverEvent,
    HandoverPayload,
    HandoverRequest,
    Message,
    MessageRole,
)

logger = get_logger(__name__)

SUMMARY_SYSTEM = (
    "You are a support operations assistant. "
    "Summarize the conversation below in exactly 3 sentences for a handover briefing. "
    "Focus on: what the customer needs, what was already tried, and any key entities (IDs, errors)."
)


async def _generate_context_snapshot(
    client: AsyncOpenAI,
    messages: list[Message],
) -> str:
    if not messages:
        return "New conversation — no prior context."

    history_text = "\n".join(
        f"{m.role.value.upper()}: {m.content}" for m in messages[-8:]
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM},
                {"role": "user", "content": history_text},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("snapshot_generation_failed", error=str(exc))
        return "Could not generate context snapshot."


async def execute_handover(
    client: AsyncOpenAI,
    state: ConversationState,
    request: HandoverRequest,
) -> HandoverPayload:
    """Build and log a HandoverPayload, update conversation state."""
    snapshot = await _generate_context_snapshot(client, state.messages)

    event = HandoverEvent(
        trace_id=state.trace_id,
        from_agent=state.active_agent,
        to_agent=request.to_agent,
        reason=request.reason,
        context_snapshot=snapshot,
        entity_snapshot=dict(state.entities),
        success=True,
    )
    state.handover_log.append(event)
    state.active_agent = request.to_agent

    logger.info(
        "handover_executed",
        trace_id=state.trace_id,
        from_agent=event.from_agent.value,
        to_agent=event.to_agent.value,
        reason=request.reason,
        event_id=event.event_id,
    )

    return HandoverPayload(
        trace_id=state.trace_id,
        from_agent=event.from_agent,
        to_agent=event.to_agent,
        reason=request.reason,
        conversation_history=list(state.messages),
        extracted_entities=dict(state.entities),
        context_snapshot=snapshot,
    )


def log_handover_failure(
    state: ConversationState,
    from_agent: AgentType,
    to_agent: AgentType,
    reason: str,
    error: str,
    fallback: AgentType,
) -> None:
    event = HandoverEvent(
        trace_id=state.trace_id,
        from_agent=from_agent,
        to_agent=to_agent,
        reason=reason,
        context_snapshot="",
        entity_snapshot=dict(state.entities),
        success=False,
        failure_reason=error,
    )
    state.handover_log.append(event)
    state.active_agent = fallback

    logger.error(
        "handover_failed",
        trace_id=state.trace_id,
        from_agent=from_agent.value,
        to_agent=to_agent.value,
        error=error,
        fallback=fallback.value,
    )


def build_handover_system_addendum(payload: HandoverPayload) -> str:
    """Extra context injected into the receiving agent's system prompt."""
    return f"""
--- HANDOVER CONTEXT ---
You have received this conversation from the {payload.from_agent.value} agent.
Reason for transfer: {payload.reason}

Conversation summary:
{payload.context_snapshot}

Known entities: {payload.extracted_entities}

Begin your response by briefly acknowledging what was already discussed, so the customer
does not need to repeat themselves. Do NOT ask for information already captured above.
--- END HANDOVER CONTEXT ---
"""
