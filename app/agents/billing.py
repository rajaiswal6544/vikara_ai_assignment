"""Billing Agent — handles billing inquiries and simulated plan changes."""

from __future__ import annotations

import json
from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.logger import get_logger
from app.models import AgentResponse, AgentType, ConversationState, HandoverRequest

logger = get_logger(__name__)

BILLING_SYSTEM = """You are the Billing Agent for CloudDash — a cloud infrastructure monitoring platform.

You help customers with:
- Understanding their invoices and charges
- Plan upgrades and downgrades
- Payment failures and methods
- Refund requests (subject to policy)
- Subscription cancellations

IMPORTANT RULES:
1. Base all pricing and policy information ONLY on the KB context provided.
2. Never fabricate pricing figures or policy details.
3. Cite sources using: [Source: <document> §<section>]
4. If asked about technical issues (alerts, dashboards, integrations), say: "That's a technical question — let me transfer you to our Technical team."
5. For plan changes or cancellations, confirm the action with the customer before proceeding.
6. Always be empathetic about billing concerns.

MOCK ACCOUNT DATA (use when customer asks about their specific account):
{account_data}

KB CONTEXT:
{kb_context}"""

TECHNICAL_REDIRECT_KEYWORDS = {
    "alert", "dashboard", "integration", "api", "aws", "gcp", "azure",
    "monitor", "metric", "threshold", "webhook", "notification channel",
}

# Mock account fixtures
MOCK_ACCOUNTS: dict[str, dict] = {
    "cust_001": {
        "customer_id": "cust_001",
        "name": "Acme Corp",
        "email": "admin@acme.example.com",
        "plan": "pro",
        "monthly_cost": 299.00,
        "next_billing": "2026-07-01",
        "payment_method": "Visa ending 4242",
        "outstanding_invoices": [],
    },
    "cust_002": {
        "customer_id": "cust_002",
        "name": "Startup Inc",
        "email": "billing@startup.example.com",
        "plan": "starter",
        "monthly_cost": 49.00,
        "next_billing": "2026-07-15",
        "payment_method": "Mastercard ending 5555",
        "outstanding_invoices": [{"id": "inv_2026_05", "amount": 49.00, "status": "overdue"}],
    },
}

PLAN_DETAILS = {
    "free": {"price": 0, "hosts": 5, "retention_days": 7},
    "starter": {"price": 49, "hosts": 25, "retention_days": 30},
    "pro": {"price": 299, "hosts": 200, "retention_days": 90},
    "enterprise": {"price": "custom", "hosts": "unlimited", "retention_days": 365},
}


class BillingAgent(BaseAgent):
    def __init__(self, config: dict[str, Any], client: AsyncOpenAI, rag_pipeline: Any | None = None) -> None:
        super().__init__("billing", config, client, rag_pipeline)

    async def process(self, state: ConversationState, message: str) -> AgentResponse:
        msg_lower = message.lower()

        # Detect technical domain shift
        if any(kw in msg_lower for kw in TECHNICAL_REDIRECT_KEYWORDS):
            logger.info("billing_to_technical_handover", trace_id=state.trace_id)
            return AgentResponse(
                content="That sounds like a technical question. Let me transfer you to our Technical Support team.",
                handover_request=HandoverRequest(
                    to_agent=AgentType.TECHNICAL,
                    reason="Customer asked a technical question during a billing support conversation.",
                ),
            )

        kb_context, sources = await self._retrieve_context(message, state)

        # Look up mock account data
        customer_id = state.entities.get("customer_id")
        account_data = self._lookup_account(customer_id)

        system = BILLING_SYSTEM.format(
            kb_context=kb_context or "No relevant KB articles found.",
            account_data=json.dumps(account_data, indent=2),
        )

        history = self._build_history_text(state)
        history.append({"role": "user", "content": message})

        content = await self._call_llm(system=system, messages=history, max_tokens=1024)
        escalation_required = self._should_escalate(state, content)

        logger.info(
            "billing_response",
            trace_id=state.trace_id,
            customer_id=customer_id,
            sources_count=len(sources),
        )

        return AgentResponse(
            content=content,
            sources=sources,
            escalation_required=escalation_required,
        )

    def _lookup_account(self, customer_id: str | None) -> dict:
        if customer_id and customer_id in MOCK_ACCOUNTS:
            return MOCK_ACCOUNTS[customer_id]
        return {"note": "No account found. Customer has not provided their customer ID yet."}

    def _should_escalate(self, state: ConversationState, response: str) -> bool:
        threshold = self.config.get("escalation_threshold", 2)
        if state.failed_attempts >= threshold:
            return True
        no_answer_phrases = ["i don't have that information", "i cannot find"]
        return any(p in response.lower() for p in no_answer_phrases)
