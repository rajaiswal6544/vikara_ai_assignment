"""Abstract base class for all agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI

from app.models import AgentResponse, ConversationState, KBSource, Message, MessageRole
from app.rag.rewriter import rewrite_query


class BaseAgent(ABC):
    """All agents inherit from this class and implement `process`."""

    def __init__(
        self,
        agent_type: str,
        config: dict[str, Any],
        client: AsyncOpenAI,
        rag_pipeline: Any | None = None,
    ) -> None:
        self.agent_type = agent_type
        self.config = config
        self.client = client
        self.rag = rag_pipeline
        self._system_prompt: str = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        prompt_file: str | None = self.config.get("system_prompt_file")
        if prompt_file:
            try:
                with open(prompt_file, encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                pass
        # Fall back to inline prompt from config
        return self.config.get("system_prompt", f"You are the {self.agent_type} agent for CloudDash support.")

    def _build_history_text(self, state: ConversationState) -> list[dict[str, str]]:
        """Convert ConversationState messages to OpenAI message format."""
        messages = []
        for msg in state.messages:
            role = "user" if msg.role == MessageRole.CUSTOMER else "assistant"
            messages.append({"role": role, "content": msg.content})
        return messages

    async def _call_llm(
        self,
        system: str,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
    ) -> str:
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system}] + messages,
        )
        return response.choices[0].message.content

    async def _retrieve_context(self, query: str, state: ConversationState) -> tuple[str, list[KBSource]]:
        """Retrieve KB chunks and return formatted context + source list."""
        if not self.rag:
            return "", []

        collections = self.config.get("kb_collections", [])
        max_chunks = self.config.get("max_retrieval_chunks", 5)

        # Rewrite query using conversation context for better retrieval
        search_query = await rewrite_query(self.client, query, state)

        chunks = await self.rag.retrieve(
            query=search_query,
            state=state,
            collections=collections,
            top_k=max_chunks,
        )

        if not chunks:
            return "", []

        sources: list[KBSource] = []
        context_parts: list[str] = []
        for chunk in chunks:
            src = KBSource(
                chunk_id=chunk["chunk_id"],
                document=chunk["document"],
                section=chunk["section"],
                excerpt=chunk["text"][:200],
            )
            sources.append(src)
            context_parts.append(
                f"[Source: {chunk['document']} §{chunk['section']}]\n{chunk['text']}"
            )

        return "\n\n---\n\n".join(context_parts), sources

    @abstractmethod
    async def process(self, state: ConversationState, message: str) -> AgentResponse:
        """Process a customer message and return an AgentResponse."""
        ...
