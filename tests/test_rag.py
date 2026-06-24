"""Tests for RAG pipeline components."""

from __future__ import annotations

import pytest

from app.rag.loader import chunk_document, load_knowledge_base
from app.rag.retriever import BM25Index, _fuse_results


def test_chunk_document_basic():
    text = "## Section A\nThis is some content about alerts and dashboards.\n\n## Section B\nMore content here."
    chunks = chunk_document(text, "Test Doc")
    assert len(chunks) >= 1
    assert all(c["document"] == "Test Doc" for c in chunks)
    assert all("chunk_id" in c for c in chunks)


def test_chunk_respects_headings():
    text = "## Alerts\nAlert content.\n\n## Billing\nBilling content."
    chunks = chunk_document(text, "Mixed Doc")
    sections = {c["section"] for c in chunks}
    assert "Alerts" in sections
    assert "Billing" in sections


def test_chunk_small_document():
    text = "## FAQ\nShort answer."
    chunks = chunk_document(text, "Short Doc", chunk_size=400)
    assert len(chunks) >= 1


def test_bm25_index_build_and_query():
    chunks = [
        {"chunk_id": "a", "document": "FAQ", "section": "General", "text": "How do I configure alerts in CloudDash"},
        {"chunk_id": "b", "document": "FAQ", "section": "Billing", "text": "CloudDash billing plans and pricing"},
        {"chunk_id": "c", "document": "FAQ", "section": "Setup", "text": "Install the CloudDash agent on Linux"},
    ]
    idx = BM25Index()
    idx.build(chunks)

    results = idx.query("alert configuration", top_k=2)
    assert len(results) <= 2
    assert results[0]["chunk_id"] == "a"


def test_bm25_empty_query():
    idx = BM25Index()
    idx.build([{"chunk_id": "a", "document": "D", "section": "S", "text": "some text"}])
    results = idx.query("", top_k=5)
    assert isinstance(results, list)


def test_rrf_fusion():
    dense = [
        {"chunk_id": "a", "document": "D", "section": "S", "text": "t", "score": 0.9, "rank": 0, "source": "dense"},
        {"chunk_id": "b", "document": "D", "section": "S", "text": "t", "score": 0.7, "rank": 1, "source": "dense"},
    ]
    sparse = [
        {"chunk_id": "b", "document": "D", "section": "S", "text": "t", "score": 10.0, "rank": 0, "source": "sparse"},
        {"chunk_id": "c", "document": "D", "section": "S", "text": "t", "score": 8.0, "rank": 1, "source": "sparse"},
    ]
    fused = _fuse_results(dense, sparse)
    # 'b' appears in both dense and sparse — should score highest via RRF
    assert fused[0]["chunk_id"] == "b"


def test_load_knowledge_base(tmp_path):
    (tmp_path / "faq.md").write_text("# FAQ\n## General\nSome content here about CloudDash.")
    (tmp_path / "billing_policy.md").write_text("# Billing\n## Plans\nPro plan costs $299.")
    chunks = load_knowledge_base(tmp_path)
    assert len(chunks) >= 2
    docs = {c["document"] for c in chunks}
    assert "Faq" in docs or "FAQ" in docs or any("Faq" in d or "FAQ" in d for d in docs)
