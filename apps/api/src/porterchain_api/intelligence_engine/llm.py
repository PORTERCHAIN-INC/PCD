"""LLM gate for the intelligence engine (doc 60 R2: FEATURE_AI=false).

Phase 0 ships no LLM client and no third-party AI keys. Every caller already has a
deterministic fallback (heuristics / templates) and treats "not configured" as "no AI".
``FEATURE_AI`` is read so the flag is visible in diagnostics, but nothing is called
even when it is set: a self-hosted model must be wired here first.
"""

from __future__ import annotations

import os
from typing import Any


def feature_ai_enabled() -> bool:
    return (os.environ.get("FEATURE_AI") or "").strip().lower() in {"1", "true", "yes", "on"}


def llm_configured() -> bool:
    return False


def llm_status() -> dict[str, Any]:
    """Ops-facing snapshot (no secrets)."""
    return {
        "configured": False,
        "provider": "none",
        "model": None,
        "feature_ai": feature_ai_enabled(),
        "circuit_open": False,
        "fail_streak": 0,
    }


def chat_completion(**_kwargs: Any) -> dict[str, Any]:
    raise ValueError("llm_disabled")
