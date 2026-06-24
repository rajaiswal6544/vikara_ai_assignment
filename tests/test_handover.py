"""Tests for handover protocol."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models import AgentType, ConversationState, HandoverRequest, Message, MessageRole


def _openai_response(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(
        return_value=_openai_response(
            "Customer reported alert not firing. Technical agent could not resolve. Transferring to billing."
        )
    )
    return client


@pytest.fixture
def state_with_history():
    state = ConversationState()
    state.messages = [
        Message(role=MessageRole.CUSTOMER, content="My alerts are not firing."),
        Message(
            role=MessageRole.AGENT,
            content="I've checked and it seems to be a configuration issue.",
            agent=AgentType.TECHNICAL,
        ),
        Message(role=MessageRole.CUSTOMER, content="Also, what does my current plan cost?"),
    ]
    state.active_agent = AgentType.TECHNICAL
    state.entities = {"customer_id": "cust_001", "product_area": "alerts"}
    return state


@pytest.mark.asyncio
async def test_execute_handover(mock_client, state_with_history):
    from app.handover import execute_handover

    request = HandoverRequest(to_agent=AgentType.BILLING, reason="Customer asked about billing")
    payload = await execute_handover(mock_client, state_with_history, request)

    assert payload.from_agent == AgentType.TECHNICAL
    assert payload.to_agent == AgentType.BILLING
    assert state_with_history.active_agent == AgentType.BILLING
    assert len(state_with_history.handover_log) == 1
    assert state_with_history.handover_log[0].success is True


@pytest.mark.asyncio
async def test_handover_preserves_entities(mock_client, state_with_history):
    from app.handover import execute_handover

    request = HandoverRequest(to_agent=AgentType.BILLING, reason="Billing question")
    payload = await execute_handover(mock_client, state_with_history, request)

    assert payload.extracted_entities.get("customer_id") == "cust_001"
    assert payload.extracted_entities.get("product_area") == "alerts"


def test_handover_addendum_contains_context(state_with_history):
    from app.handover import build_handover_system_addendum
    from app.models import HandoverPayload

    payload = HandoverPayload(
        trace_id="test-trace",
        from_agent=AgentType.TECHNICAL,
        to_agent=AgentType.BILLING,
        reason="Billing question",
        conversation_history=state_with_history.messages,
        extracted_entities=state_with_history.entities,
        context_snapshot="Customer had alert issue then asked about billing.",
    )
    addendum = build_handover_system_addendum(payload)
    assert "technical" in addendum.lower()
    assert "billing" in addendum.lower()
    assert "Customer had alert issue" in addendum


def test_log_handover_failure(state_with_history):
    from app.handover import log_handover_failure

    log_handover_failure(
        state=state_with_history,
        from_agent=AgentType.TECHNICAL,
        to_agent=AgentType.BILLING,
        reason="test",
        error="connection timeout",
        fallback=AgentType.TRIAGE,
    )
    assert len(state_with_history.handover_log) == 1
    assert state_with_history.handover_log[0].success is False
    assert state_with_history.active_agent == AgentType.TRIAGE
