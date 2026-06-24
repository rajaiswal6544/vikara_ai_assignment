"""Triage Agent — classifies intent and routes to specialist agents."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.logger import get_logger
from app.models import AgentResponse, AgentType, ConversationState

logger = get_logger(__name__)

INTENT_MAP: dict[str, AgentType] = {
    "technical": AgentType.TECHNICAL,
    "integration": AgentType.TECHNICAL,
    "api": AgentType.TECHNICAL,
    "dashboard": AgentType.TECHNICAL,
    "alert": AgentType.TECHNICAL,
    "billing": AgentType.BILLING,
    "subscription": AgentType.BILLING,
    "invoice": AgentType.BILLING,
    "payment": AgentType.BILLING,
    "plan": AgentType.BILLING,
    "account": AgentType.TECHNICAL,
    "sso": AgentType.TECHNICAL,
    "user": AgentType.TECHNICAL,
    "general": AgentType.TECHNICAL,
    "onboarding": AgentType.TECHNICAL,
    "feature_request": AgentType.ESCALATION,
    "escalation": AgentType.ESCALATION,
    "unknown": AgentType.ESCALATION,
}

TRIAGE_SYSTEM = """You are the Triage Agent for CloudDash customer support.

Your job is to:
1. Understand the customer's intent.
2. Extract key entities.
3. Decide which specialist agent should handle this.

Respond ONLY with a JSON object in this exact format (no markdown, no explanation):
{
  "intent": "<one of: technical|billing|account|general|escalation|unknown>",
  "confidence": <0.0-1.0>,
  "entities": {
    "customer_id": "<extracted or null>",
    "product_area": "<e.g. alerts, dashboards, integrations, billing, sso or null>",
    "severity": "<high|medium|low or null>",
    "error_codes": ["<list of any error codes mentioned>"],
    "plan_tier": "<free|starter|pro|enterprise or null>"
  },
  "routing_agent": "<technical|billing|escalation>",
  "clarification_needed": <true|false>,
  "clarification_question": "<question to ask customer if clarification needed, else null>",
  "summary": "<one sentence summary of the customer issue>"
}

Intent definitions:
- technical: alert config, dashboards, API, integrations, setup, errors
- billing: invoices, plans, payments, subscriptions, pricing
- account: users, SSO, permissions, org management (routes to technical)
- general: onboarding, feature questions, how-to (routes to technical)
- escalation: explicit request for human, very angry customer
- unknown: cannot determine intent"""


class TriageAgent(BaseAgent):
    def __init__(self, config: dict[str, Any], client: AsyncOpenAI, rag_pipeline: Any | None = None) -> None:
        super().__init__("triage", config, client, rag_pipeline)

    async def process(self, state: ConversationState, message: str) -> AgentResponse:
        history = self._build_history_text(state)
        # Include the current message
        history.append({"role": "user", "content": message})

        raw = await self._call_llm(
            system=TRIAGE_SYSTEM,
            messages=history,
            max_tokens=512,
        )

        parsed = self._parse_triage(raw)
        logger.info(
            "triage_result",
            trace_id=state.trace_id,
            intent=parsed.get("intent"),
            routing=parsed.get("routing_agent"),
            confidence=parsed.get("confidence"),
        )

        # Update state entities
        entities = parsed.get("entities", {})

        intent = parsed.get("intent", "unknown")
        routing_agent_str = parsed.get("routing_agent", "technical")
        routing_agent = INTENT_MAP.get(intent) or INTENT_MAP.get(routing_agent_str) or AgentType.TECHNICAL

        if parsed.get("clarification_needed") and parsed.get("clarification_question"):
            return AgentResponse(
                content=parsed["clarification_question"],
                routing_decision=None,  # Stay in triage
                entities_extracted=entities,
                confidence=parsed.get("confidence", 0.5),
            )

        return AgentResponse(
            content=parsed.get("summary", "I'll connect you with the right specialist."),
            routing_decision=routing_agent,
            entities_extracted=entities,
            confidence=parsed.get("confidence", 0.9),
        )

    def _parse_triage(self, raw: str) -> dict:
        # Strip markdown code fences if present
        text = re.sub(r"```(?:json)?\n?", "", raw).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("triage_parse_failed", raw=raw[:200])
            return {
                "intent": "unknown",
                "confidence": 0.3,
                "entities": {},
                "routing_agent": "technical",
                "clarification_needed": False,
                "summary": "I'll connect you with our support team.",
            }
