"""Input guardrails: prompt injection detection and off-topic filtering."""

from __future__ import annotations

import re

from app.logger import get_logger

logger = get_logger(__name__)

INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"ignore (previous|above|all|prior|these|your).{0,20}instructions",
        r"disregard (your|the|all) (instructions|rules|guidelines)",
        r"you are now",
        r"new persona",
        r"system prompt",
        r"jailbreak",
        r"DAN mode",
        r"pretend (you are|you're) (not|a different)",
        r"forget everything",
        r"override (your|all) (instructions|constraints)",
        r"act as (DAN|an AI with no restrictions|a different AI)",
    ]
]

OFF_TOPIC_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"write (me )?(a |an )?(poem|story|essay|song|joke)",
        r"(generate|create|make) (an? )?(image|picture|video|music)",
        r"(what is|tell me about) the (meaning of life|weather|news|stock)",
        r"(who is|tell me about) (elon|bezos|trump|biden)",
        r"translate (this|the following) (to|into)",
    ]
]

MAX_INPUT_LENGTH = 4000


class InputGuardResult:
    def __init__(self, allowed: bool, reason: str = "", cleaned: str = "") -> None:
        self.allowed = allowed
        self.reason = reason
        self.cleaned = cleaned


def check_input(message: str) -> InputGuardResult:
    """Check message for injection attempts and off-topic content."""

    # Length check
    if len(message) > MAX_INPUT_LENGTH:
        logger.warning("input_too_long", length=len(message))
        return InputGuardResult(
            allowed=False,
            reason="message_too_long",
            cleaned="Your message is too long. Please keep it under 4000 characters.",
        )

    # Prompt injection detection
    for pattern in INJECTION_PATTERNS:
        if pattern.search(message):
            logger.warning(
                "prompt_injection_detected",
                pattern=pattern.pattern,
                message_preview=message[:100],
            )
            return InputGuardResult(
                allowed=False,
                reason="prompt_injection",
                cleaned="I'm sorry, but I can only help with CloudDash support questions.",
            )

    # Off-topic detection
    for pattern in OFF_TOPIC_PATTERNS:
        if pattern.search(message):
            logger.info("off_topic_detected", message_preview=message[:100])
            return InputGuardResult(
                allowed=False,
                reason="off_topic",
                cleaned=(
                    "I'm here to help with CloudDash support questions only. "
                    "Could you describe the issue you're having with CloudDash?"
                ),
            )

    return InputGuardResult(allowed=True, cleaned=message)
