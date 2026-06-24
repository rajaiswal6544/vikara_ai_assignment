"""Technical Support Agent — resolves technical issues using KB retrieval."""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from app.agents.base import BaseAgent
from app.logger import get_logger
from app.models import AgentResponse, AgentType, ConversationState, HandoverRequest

logger = get_logger(__name__)

TECHNICAL_SYSTEM = """You are the Technical Support Agent for CloudDash — a cloud infrastructure monitoring platform (AWS, GCP, Azure).

You help customers with:
- Alert and notification configuration
- Dashboard setup and troubleshooting
- API integration and usage
- Third-party integrations (AWS CloudWatch, GCP Monitoring, Azure Monitor)
- Performance issues and errors

IMPORTANT RULES:
1. Base your answers ONLY on the KB context provided. If the KB does not contain the answer, say so clearly and offer to escalate.
2. Never fabricate pricing, feature details, or policies.
3. Provide step-by-step instructions when troubleshooting.
4. Always cite your sources using the format: [Source: <document> §<section>]
5. If the customer's question is about billing/invoices/payment, respond: "This looks like a billing question. Let me transfer you to our Billing team." — do NOT answer it yourself.
6. Be concise but complete.

KB CONTEXT:
{kb_context}

If KB context is empty, acknowledge you don't have that information and offer escalation."""

BILLING_REDIRECT_KEYWORDS = {
    "invoice", "billing", "payment", "charge", "refund", "subscription",
    "plan upgrade", "plan downgrade", "pricing", "cost", "credit card",
    "overcharged", "cancel subscription",
}


class TechnicalAgent(BaseAgent):
    def __init__(self, config: dict[str, Any], client: AsyncOpenAI, rag_pipeline: Any | None = None) -> None:
        super().__init__("technical", config, client, rag_pipeline)

    async def process(self, state: ConversationState, message: str) -> AgentResponse:
        msg_lower = message.lower()

        # Detect billing domain shift
        if any(kw in msg_lower for kw in BILLING_REDIRECT_KEYWORDS):
            logger.info("technical_to_billing_handover", trace_id=state.trace_id)
            return AgentResponse(
                content="This looks like a billing question. Let me transfer you to our Billing team right away.",
                handover_request=HandoverRequest(
                    to_agent=AgentType.BILLING,
                    reason="Customer asked a billing/subscription question during a technical support conversation.",
                ),
            )

        kb_context, sources = await self._retrieve_context(message, state)
        system = TECHNICAL_SYSTEM.format(kb_context=kb_context or "No relevant KB articles found.")

        history = self._build_history_text(state)
        history.append({"role": "user", "content": message})

        content = await self._call_llm(system=system, messages=history, max_tokens=1024)

        escalation_required = self._should_escalate(state, content)

        logger.info(
            "technical_response",
            trace_id=state.trace_id,
            sources_count=len(sources),
            escalation=escalation_required,
        )

        return AgentResponse(
            content=content,
            sources=sources,
            escalation_required=escalation_required,
        )

    def _should_escalate(self, state: ConversationState, response: str) -> bool:
        threshold = self.config.get("escalation_threshold", 3)
        if state.failed_attempts >= threshold:
            return True
        no_answer_phrases = [
            "i don't have that information",
            "i cannot find",
            "i'm unable to",
            "not in my knowledge base",
        ]
        return any(p in response.lower() for p in no_answer_phrases)
