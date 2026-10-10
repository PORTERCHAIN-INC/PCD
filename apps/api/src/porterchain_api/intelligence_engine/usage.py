"""Record AI/LLM usage into ai_usage_logs (ops metering — not on pay path)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.intelligence_engine.usage_models import AiUsageLog


def record_ai_usage(
    db: Session,
    *,
    provider: str,
    model: str,
    feature: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    latency_ms: int | None = None,
    status: str = "ok",
    error: str | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> AiUsageLog:
    total = int(prompt_tokens) + int(completion_tokens)
    row = AiUsageLog(
        provider=provider,
        model=model,
        feature=feature,
        actor_type=actor_type,
        actor_id=actor_id,
        prompt_tokens=int(prompt_tokens),
        completion_tokens=int(completion_tokens),
        total_tokens=total,
        latency_ms=latency_ms,
        status=status,
        error=(error or None) and str(error)[:2000],
        meta=dict(meta or {}),
    )
    db.add(row)
    db.flush()
    return row


def ai_usage_summary(db: Session, *, limit: int = 40) -> dict[str, Any]:
    """Aggregates + recent rows for diagnostics (no secrets)."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import case, func

    from porterchain_api.intelligence_engine.nim_client import nim_status
    from porterchain_api.config import get_settings

    since = datetime.now(UTC) - timedelta(hours=24)
    rows = (
        db.query(AiUsageLog)
        .order_by(AiUsageLog.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    day = (
        db.query(
            AiUsageLog.feature,
            AiUsageLog.provider,
            func.count(AiUsageLog.id),
            func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AiUsageLog.prompt_tokens), 0),
            func.coalesce(func.sum(AiUsageLog.completion_tokens), 0),
            func.coalesce(
                func.sum(case((AiUsageLog.status != "ok", 1), else_=0)),
                0,
            ),
        )
        .filter(AiUsageLog.created_at >= since)
        .group_by(AiUsageLog.feature, AiUsageLog.provider)
        .all()
    )
    flags = get_settings().phase2_flags
    from porterchain_api.intelligence_engine.cuopt_client import cuopt_status
    from porterchain_api.intelligence_engine.cuopt_shadow import cuopt_shadow_enabled

    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "window": "24h",
        "nim": nim_status(),
        "cuopt": cuopt_status(),
        "phase2": {
            "intelligence": bool(flags.get("intelligence")),
            "ai_dispatch": bool(flags.get("ai_dispatch")),
            "cuopt_shadow": cuopt_shadow_enabled(),
        },
        "by_feature": [
            {
                "feature": feature,
                "provider": provider,
                "calls": int(calls),
                "total_tokens": int(tokens),
                "prompt_tokens": int(prompt),
                "completion_tokens": int(completion),
                "errors": int(errors),
            }
            for feature, provider, calls, tokens, prompt, completion, errors in day
        ],
        "recent": [
            {
                "id": r.id,
                "provider": r.provider,
                "model": r.model,
                "feature": r.feature,
                "status": r.status,
                "total_tokens": r.total_tokens,
                "latency_ms": r.latency_ms,
                "error": (r.error or None) and str(r.error)[:240],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
