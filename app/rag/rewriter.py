"""Query rewriter — rewrites user query using conversation context for better retrieval."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.logger import get_logger
from app.models import ConversationState, MessageRole

logger = get_logger(__name__)

REWRITER_SYSTEM = """You are a search query optimizer for a customer support knowledge base.

Given a conversation history and the latest customer message, rewrite the message into a
standalone, context-complete search query that will find the most relevant KB articles.

Rules:
- Preserve exact technical terms, error codes, and product names.
- Resolve pronouns ("it", "that", "the issue") using conversation context.
- Keep the query concise (under 30 words).
- Output ONLY the rewritten query — no explanation, no prefix.

If the message is already a good standalone query, return it unchanged."""


async def rewrite_query(
    client: AsyncOpenAI,
    query: str,
    state: ConversationState,
) -> str:
    """Rewrite query using conversation context for improved retrieval."""
    if len(state.messages) < 2:
        return query  # First turn — no context needed

    recent = state.messages[-4:]
    history_text = "\n".join(
        f"{m.role.value.upper()}: {m.content}"
        for m in recent
        if m.role in (MessageRole.CUSTOMER, MessageRole.AGENT)
    )

    prompt = f"Conversation so far:\n{history_text}\n\nLatest customer message: {query}"

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # fast + cheap model for query rewriting
            max_tokens=128,
            messages=[
                {"role": "system", "content": REWRITER_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        rewritten = response.choices[0].message.content.strip()
        logger.info("query_rewritten", original=query[:80], rewritten=rewritten[:80])
        return rewritten
    except Exception as exc:
        logger.warning("query_rewrite_failed", error=str(exc))
        return query
