"""FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import structlog
from openai import AsyncOpenAI
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.logger import configure_logging, get_logger
from app.models import (
    ConversationHistoryResponse,
    HandoverLogResponse,
    SendMessageRequest,
    SendMessageResponse,
    StartConversationRequest,
    StartConversationResponse,
)
from app.orchestrator import Orchestrator
from app.rag.embedder import VectorStore
from app.rag.loader import load_knowledge_base
from app.rag.retriever import BM25Index, RAGPipeline

configure_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE"),
)
logger = get_logger(__name__)

BASE_DIR = Path(__file__).parent.parent
KB_DIR = BASE_DIR / "knowledge_base"
CONFIG_PATH = BASE_DIR / "config" / "agents.yaml"

_orchestrator: Orchestrator | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _orchestrator

    logger.info("startup_begin")

    # 1. Load and index knowledge base
    chunks = load_knowledge_base(KB_DIR)

    vector_store = VectorStore(
        persist_directory=os.getenv("CHROMA_PERSIST_DIR") or None
    )
    vector_store.index_chunks(chunks)

    bm25 = BM25Index()
    bm25.build(chunks)

    rag = RAGPipeline(vector_store=vector_store, bm25_index=bm25)

    # 2. Build OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set — LLM calls will fail")
    client = AsyncOpenAI(api_key=api_key or "placeholder")

    # 3. Build orchestrator
    _orchestrator = Orchestrator(
        config_path=str(CONFIG_PATH),
        rag=rag,
        openai_client=client,
    )

    logger.info("startup_complete", kb_chunks=len(chunks))
    yield
    logger.info("shutdown")


STATIC_DIR = BASE_DIR / "app" / "static"

app = FastAPI(
    title="CloudDash Support API",
    description="Multi-agent customer support system for CloudDash.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _get_orchestrator() -> Orchestrator:
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialised.")
    return _orchestrator


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def serve_ui() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post(
    "/conversations",
    response_model=StartConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_conversation(body: StartConversationRequest) -> StartConversationResponse:
    orch = _get_orchestrator()
    state = orch.create_conversation(customer_id=body.customer_id)

    response_text: str | None = None
    if body.initial_message:
        _, response_text, _ = await orch.process_message(state.id, body.initial_message)

    return StartConversationResponse(
        conversation_id=state.id,
        trace_id=state.trace_id,
        message=response_text,
    )


@app.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
async def send_message(
    conversation_id: str, body: SendMessageRequest
) -> SendMessageResponse:
    orch = _get_orchestrator()
    try:
        state, response_text, sources = await orch.process_message(conversation_id, body.message)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id!r} not found.",
        )

    ticket_id: str | None = state.entities.get("ticket_id")

    return SendMessageResponse(
        conversation_id=state.id,
        trace_id=state.trace_id,
        response=response_text,
        agent=state.active_agent,
        sources=sources,
        escalated=state.status.value == "escalated",
        ticket_id=ticket_id,
    )


@app.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistoryResponse,
)
async def get_conversation(conversation_id: str) -> ConversationHistoryResponse:
    orch = _get_orchestrator()
    state = orch.get_conversation(conversation_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id!r} not found.",
        )
    return ConversationHistoryResponse(
        conversation_id=state.id,
        trace_id=state.trace_id,
        status=state.status,
        messages=state.messages,
        active_agent=state.active_agent,
    )


@app.get(
    "/conversations/{conversation_id}/handovers",
    response_model=HandoverLogResponse,
)
async def get_handovers(conversation_id: str) -> HandoverLogResponse:
    orch = _get_orchestrator()
    state = orch.get_conversation(conversation_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id!r} not found.",
        )
    return HandoverLogResponse(
        conversation_id=state.id,
        trace_id=state.trace_id,
        handovers=state.handover_log,
    )
