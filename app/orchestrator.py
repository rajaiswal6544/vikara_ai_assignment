"""Central orchestrator — routes messages, manages state, executes handovers."""

from __future__ import annotations

import importlib
import time
import uuid
from typing import Any

import structlog
import yaml
from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.guardrails.input_guard import check_input
from app.guardrails.output_guard import apply_output_guardrails
from app.handover import build_handover_system_addendum, execute_handover, log_handover_failure
from app.logger import get_logger
from app.models import (
    AgentType,
    ConversationState,
    ConversationStatus,
    Message,
    MessageRole,
)
from app.rag.retriever import RAGPipeline

logger = get_logger(__name__)

HUMAN_ESCALATION_PHRASES = {
    "speak to a human",
    "speak to a manager",
    "talk to a person",
    "talk to a manager",
    "real agent",
    "human agent",
    "human support",
    "i want a real person",
    "want to speak to a manager",
    "connect me to support",
    "escalate my issue",
    "immediate refund",
    "charged twice",
    "double charge",
    "duplicate charge",
}

# Built-in agent class registry — extended automatically for any class in app.agents.*
_BUILTIN_AGENTS = {
    "TriageAgent": "app.agents.triage",
    "TechnicalAgent": "app.agents.technical",
    "BillingAgent": "app.agents.billing",
    "EscalationAgent": "app.agents.escalation",
}


def _load_agent_class(class_name: str) -> type:
    """
    Resolve an agent class by name without hardcoding all classes in this module.
    Checks the built-in registry first, then attempts dynamic import from app.agents.<module>.
    Adding a new agent only requires a YAML entry + a new file in app/agents/ — no changes here.
    """
    module_path = _BUILTIN_AGENTS.get(class_name)
    if module_path:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

    # Dynamic fallback: try app.agents.<snake_case_of_class_name>
    snake = "".join(
        f"_{c.lower()}" if c.isupper() else c for c in class_name
    ).lstrip("_").replace("_agent", "")
    try:
        module = importlib.import_module(f"app.agents.{snake}")
        return getattr(module, class_name)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise ImportError(
            f"Cannot load agent class '{class_name}'. "
            f"Create app/agents/{snake}.py with a class named {class_name} "
            f"inheriting BaseAgent, then add it to agents.yaml."
        ) from exc


class Orchestrator:
    def __init__(self, config_path: str, rag: RAGPipeline, openai_client: AsyncOpenAI) -> None:
        self.rag = rag
        self.client = openai_client
        self._conversations: dict[str, ConversationState] = {}
        self._config = self._load_config(config_path)
        self._agents: dict[AgentType, BaseAgent] = self._build_agents()

    def _load_config(self, path: str) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _build_agents(self) -> dict[AgentType, BaseAgent]:
        agents: dict[AgentType, BaseAgent] = {}
        for name, cfg in self._config.get("agents", {}).items():
            agent_type = AgentType(name)
            cls_name = cfg.get("class", "")
            try:
                cls = _load_agent_class(cls_name)
            except ImportError as exc:
                logger.warning("unknown_agent_class", cls_name=cls_name, error=str(exc))
                continue
            agents[agent_type] = cls(config=cfg, client=self.client, rag_pipeline=self.rag)
        return agents

    # ------------------------------------------------------------------
    # Conversation lifecycle
    # ------------------------------------------------------------------

    def create_conversation(self, customer_id: str | None = None) -> ConversationState:
        state = ConversationState()
        if customer_id:
            state.entities["customer_id"] = customer_id
        self._conversations[state.id] = state
        logger.info("conversation_created", trace_id=state.trace_id, conversation_id=state.id)
        return state

    def get_conversation(self, conversation_id: str) -> ConversationState | None:
        return self._conversations.get(conversation_id)

    # ------------------------------------------------------------------
    # Message processing
    # ------------------------------------------------------------------

    async def process_message(
        self, conversation_id: str, message: str
    ) -> tuple[ConversationState, str, list]:
        state = self._conversations.get(conversation_id)
        if state is None:
            raise KeyError(f"Conversation {conversation_id!r} not found.")

        # --- Input guardrail ---
        guard_result = check_input(message)
        if not guard_result.allowed:
            logger.info(
                "input_blocked",
                trace_id=state.trace_id,
                reason=guard_result.reason,
            )
            return state, guard_result.cleaned, []

        # Append customer message to history
        state.messages.append(
            Message(role=MessageRole.CUSTOMER, content=message)
        )

        # --- Human escalation shortcut ---
        if any(phrase in message.lower() for phrase in HUMAN_ESCALATION_PHRASES):
            logger.info("explicit_escalation_request", trace_id=state.trace_id)
            state.active_agent = AgentType.ESCALATION

        structlog.contextvars.bind_contextvars(trace_id=state.trace_id)

        response_content, sources = await self._dispatch(state, message)

        # --- Output guardrail ---
        safe_content = apply_output_guardrails(response_content, sources)

        # Append agent message to history
        state.messages.append(
            Message(
                role=MessageRole.AGENT,
                content=safe_content,
                agent=state.active_agent,
                sources=sources,
            )
        )

        return state, safe_content, sources

    async def _dispatch(
        self, state: ConversationState, message: str, depth: int = 0
    ) -> tuple[str, list]:
        """Dispatch to active agent; handle routing, handover, escalation."""
        if depth > 3:
            logger.error("max_dispatch_depth", trace_id=state.trace_id)
            state.status = ConversationStatus.ESCALATED
            return "I'm escalating your case to our support team. Someone will be in touch shortly.", []

        t0 = time.monotonic()
        agent = self._agents.get(state.active_agent)
        if agent is None:
            logger.error("agent_not_found", agent_type=state.active_agent.value)
            state.active_agent = AgentType.TRIAGE
            return await self._dispatch(state, message, depth + 1)

        try:
            agent_response = await agent.process(state, message)
        except Exception as exc:
            logger.error(
                "agent_error",
                trace_id=state.trace_id,
                agent=state.active_agent.value,
                error=str(exc),
            )
            state.failed_attempts += 1
            if state.failed_attempts >= 3:
                state.active_agent = AgentType.ESCALATION
                return await self._dispatch(state, message, depth + 1)
            return "I'm having trouble processing your request right now. Could you rephrase your question?", []

        latency = (time.monotonic() - t0) * 1000
        logger.info(
            "agent_invoked",
            trace_id=state.trace_id,
            agent=state.active_agent.value,
            latency_ms=round(latency, 1),
            escalation=agent_response.escalation_required,
        )

        # Update extracted entities from triage
        if agent_response.entities_extracted:
            state.entities.update(agent_response.entities_extracted)

        # --- Routing: Triage → specialist ---
        if state.active_agent == AgentType.TRIAGE and agent_response.routing_decision:
            state.active_agent = agent_response.routing_decision
            return await self._dispatch(state, message, depth + 1)

        # --- Handover: mid-conversation domain switch ---
        if agent_response.handover_request:
            try:
                payload = await execute_handover(
                    self.client, state, agent_response.handover_request
                )
                # Inject handover context into the target agent's next call
                addendum = build_handover_system_addendum(payload)
                handover_msg = f"{addendum}\n\nCustomer message: {message}"
                return await self._dispatch(state, handover_msg, depth + 1)
            except Exception as exc:
                log_handover_failure(
                    state=state,
                    from_agent=state.active_agent,
                    to_agent=agent_response.handover_request.to_agent,
                    reason=agent_response.handover_request.reason,
                    error=str(exc),
                    fallback=AgentType.TRIAGE,
                )
                return await self._dispatch(state, message, depth + 1)

        # --- Escalation ---
        if agent_response.escalation_required:
            state.status = ConversationStatus.ESCALATED
            if state.active_agent != AgentType.ESCALATION:
                state.active_agent = AgentType.ESCALATION
                return await self._dispatch(state, message, depth + 1)

        if state.status != ConversationStatus.ESCALATED:
            state.status = ConversationStatus.ACTIVE

        return agent_response.content, agent_response.sources
