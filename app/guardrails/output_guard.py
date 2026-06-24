"""Output guardrails: PII redaction and hallucination check."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.logger import get_logger
from app.models import KBSource

logger = get_logger(__name__)

PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b(\+\d{1,3}[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[\s\-]?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "api_key": re.compile(r"\b(sk|pk|api)[-_][a-zA-Z0-9]{20,}\b"),
}

# Sentences that suggest the model is making something up about CloudDash specifics
FABRICATION_RISK_PHRASES = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"as of (january|february|march|april|may|june|july|august|september|october|november|december) 20\d\d",
        r"cloudDash (charges|costs|prices|offers) .{0,30}\$\d+",
        r"your (current )?plan (includes|allows|provides)",
    ]
]


@dataclass
class OutputGuardResult:
    content: str
    pii_redacted: bool
    redaction_types: list[str]


def redact_pii(content: str) -> OutputGuardResult:
    """Replace PII patterns with [REDACTED_<type>] tokens."""
    redacted = content
    types_found: list[str] = []

    for pii_type, pattern in PII_PATTERNS.items():
        new_text, count = pattern.subn(f"[REDACTED_{pii_type.upper()}]", redacted)
        if count > 0:
            types_found.append(pii_type)
            redacted = new_text

    if types_found:
        logger.warning("pii_redacted", types=types_found)

    return OutputGuardResult(
        content=redacted,
        pii_redacted=bool(types_found),
        redaction_types=types_found,
    )


def check_hallucination(content: str, sources: list[KBSource]) -> str:
    """
    Lightweight hallucination check: if the response contains fabrication-risk phrases
    but no KB sources were retrieved, append a disclaimer.
    """
    if sources:
        return content  # KB sources present — trust the grounding

    for pattern in FABRICATION_RISK_PHRASES:
        if pattern.search(content):
            logger.warning("potential_hallucination_detected", content_preview=content[:150])
            disclaimer = (
                "\n\n*Note: I couldn't verify this information against my knowledge base. "
                "If you need confirmed details about pricing or policies, please ask me to escalate "
                "to our support team.*"
            )
            return content + disclaimer

    return content


def apply_output_guardrails(content: str, sources: list[KBSource]) -> str:
    """Apply all output guardrails in sequence."""
    # 1. PII redaction
    pii_result = redact_pii(content)
    safe_content = pii_result.content

    # 2. Hallucination check
    safe_content = check_hallucination(safe_content, sources)

    return safe_content
