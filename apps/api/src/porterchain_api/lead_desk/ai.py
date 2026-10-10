"""Optional LLM hook. Off unless LEAD_AI_ENABLED=true and an NVIDIA NIM key exists.

No paid dependency is required: every caller has a deterministic fallback and
treats ``None`` as "no AI".
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def ai_enabled() -> bool:
    from porterchain_api.config import get_settings

    if not getattr(get_settings(), "lead_ai_enabled", False):
        return False
    from porterchain_api.intelligence_engine.nim_client import nim_configured

    return nim_configured()


def complete_text(prompt: str, *, max_tokens: int = 200) -> str | None:
    if not ai_enabled():
        return None
    from porterchain_api.intelligence_engine.privacy import redact

    prompt = redact(prompt)
    try:
        from porterchain_api.intelligence_engine.nim_client import chat_completion

        out = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            json_object=False,
            timeout_s=8.0,
            max_retries=0,
        )
        text = str(out.get("content") or "").strip()
        return text or None
    except Exception:
        logger.warning("lead_ai_completion_failed", exc_info=True)
        return None
