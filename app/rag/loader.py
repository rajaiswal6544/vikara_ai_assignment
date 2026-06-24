"""KB document loader and chunker."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.logger import get_logger

logger = get_logger(__name__)


def _split_by_heading(text: str) -> list[tuple[str, str]]:
    """Split Markdown into (heading, body) pairs. Heading never spans chunks."""
    pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
    parts: list[tuple[str, str]] = []
    positions = [(m.start(), m.group(0)) for m in pattern.finditer(text)]

    if not positions:
        return [("General", text)]

    # Text before first heading
    if positions[0][0] > 0:
        parts.append(("General", text[: positions[0][0]].strip()))

    for i, (start, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        body = text[start + len(heading) : end].strip()
        parts.append((heading.lstrip("#").strip(), body))

    return parts


def _token_approx(text: str) -> int:
    """Rough token count: ~4 chars per token."""
    return len(text) // 4


def chunk_document(
    text: str,
    doc_title: str,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    """Chunk a document respecting Markdown heading boundaries."""
    sections = _split_by_heading(text)
    chunks: list[dict[str, Any]] = []
    chunk_index = 0

    for section_heading, body in sections:
        if not body.strip():
            continue

        words = body.split()
        # Slide window over words
        step = max(1, chunk_size - overlap)
        start = 0
        while start < len(words):
            window = words[start : start + chunk_size]
            chunk_text = " ".join(window)
            if len(chunk_text.strip()) < 5:
                start += step
                continue

            chunk_id = f"{doc_title.lower().replace(' ', '_')}_{chunk_index}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "document": doc_title,
                    "section": section_heading,
                    "text": chunk_text,
                    "token_count": _token_approx(chunk_text),
                    "char_offset": start,
                }
            )
            chunk_index += 1
            start += step

    logger.info("document_chunked", document=doc_title, chunk_count=len(chunks))
    return chunks


def load_knowledge_base(kb_dir: str | Path) -> list[dict[str, Any]]:
    """Load all Markdown files from the KB directory and chunk them."""
    kb_path = Path(kb_dir)
    all_chunks: list[dict[str, Any]] = []

    for md_file in sorted(kb_path.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        doc_title = md_file.stem.replace("_", " ").title()
        chunks = chunk_document(text, doc_title)
        all_chunks.extend(chunks)

    logger.info("kb_loaded", total_chunks=len(all_chunks), kb_dir=str(kb_dir))
    return all_chunks
