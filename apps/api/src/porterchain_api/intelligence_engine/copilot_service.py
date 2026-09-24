"""LLM admin copilot — read-only assist (§4.2.8). Not on pay path."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Closed set — NIM may only recommend these. Never auto_apply.
ALLOWED_ACTIONS: frozenset[str] = frozenset(
    {
        "review_fleetbase_console",
        "check_sla_queue",
        "reassign_candidate",
        "contact_merchant",
        "escalate_ops_lead",
        "verify_pod_exception",
        "review_ops_notes",
        "hold_for_capacity",
        "retry_fleetbase_sync",
        # Phase 5 — optimize / FSA explain (still auto_apply=false)
        "run_optimize_preview",
        "compare_cuopt_shadow",
        "reoptimize_after_pickup",
        "explain_fsa_coverage",
        "hold_for_out_of_tile",
    }
)

_SYSTEM_PLAYBOOK = """You are PorterChain's ops copilot for a Transportation Capacity Network.
Rules (non-negotiable):
1. Return ONLY JSON: {"suggestions":[{"action":string,"rationale":string,"priority":"p0"|"p1"|"p2","confidence":0.0-1.0,"auto_apply":false}]}
2. action MUST be one of: review_fleetbase_console, check_sla_queue, reassign_candidate, contact_merchant, escalate_ops_lead, verify_pod_exception, review_ops_notes, hold_for_capacity, retry_fleetbase_sync, run_optimize_preview, compare_cuopt_shadow, reoptimize_after_pickup, explain_fsa_coverage, hold_for_out_of_tile
3. Never invent live GPS, driver locations, payments, Stripe state, or Fleetbase mutations. Never invent routes — only recommend Fleetbase optimize / Valhalla explain.
4. Prefer Fleetbase console verification before any reassign suggestion.
5. auto_apply is ALWAYS false. Max 4 suggestions, highest priority first.
6. Be specific to the given context; no generic filler."""


def suggest_ops_action_committed(
    context: str,
    *,
    flags: dict[str, bool],
    db: Session,
    actor_type: str | None = None,
    actor_id: str | None = None,
    merchant_id: str | None = None,
    include_sla_queue: bool = True,
) -> dict[str, Any]:
    """Suggest, then commit any usage rows written during the call."""
    result = suggest_ops_action(
        context,
        flags=flags,
        db=db,
        actor_type=actor_type,
        actor_id=actor_id,
        merchant_id=merchant_id,
        include_sla_queue=include_sla_queue,
    )
    db.commit()
    return result


def suggest_ops_action(
    context: str,
    *,
    flags: dict[str, bool],
    db: Session | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
    merchant_id: str | None = None,
    include_sla_queue: bool = True,
) -> dict[str, Any]:
    """Return ops suggestions; uses NVIDIA NIM when configured + phase2 enabled."""
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    if not phase2_intelligence_enabled(flags):
        return {"suggestions": [], "status": "phase2_disabled"}

    from porterchain_api.intelligence_engine import nim_client

    grounded = context
    tool_bundle: dict[str, Any] | None = None
    if db is not None and (include_sla_queue or merchant_id):
        try:
            from porterchain_api.intelligence_engine.tools import (
                format_tool_bundle_for_prompt,
                gather_ops_tool_context,
            )

            tool_bundle = gather_ops_tool_context(
                db,
                merchant_id=merchant_id,
                include_sla_queue=include_sla_queue,
                context=context,
            )
            grounded = f"{context.strip()}\n\n{format_tool_bundle_for_prompt(tool_bundle)}"
        except Exception as exc:  # noqa: BLE001
            logger.warning("ops tool gather failed: %s", exc)

    status = nim_client.nim_status()
    if status["configured"] and db is not None and not status["circuit_open"]:
        try:
            result = _suggest_via_nim(
                db,
                grounded,
                actor_type=actor_type,
                actor_id=actor_id,
            )
            if tool_bundle is not None:
                result["tools"] = tool_bundle
            return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("NIM copilot failed, falling back to stub: %s", exc)
            if db is not None:
                from porterchain_api.intelligence_engine.usage import record_ai_usage
                from porterchain_shared.config.settings import get_platform_settings

                settings = get_platform_settings()
                record_ai_usage(
                    db,
                    provider="nvidia_nim",
                    model=getattr(settings, "nvidia_model", "unknown") or "unknown",
                    feature="ops_copilot",
                    status="error",
                    error=str(exc),
                    actor_type=actor_type,
                    actor_id=actor_id,
                )

    stub = _stub_suggestions(grounded, nim_status=status)
    if tool_bundle is not None:
        stub["tools"] = tool_bundle
    return stub


def _stub_suggestions(context: str, *, nim_status: dict[str, Any]) -> dict[str, Any]:
    return {
        "suggestions": [
            {
                "action": "review_fleetbase_console",
                "rationale": (
                    "Verify active drivers near the exception zone in the Fleetbase "
                    "live map before reassign."
                ),
                "priority": "p1",
                "confidence": 0.55,
                "auto_apply": False,
            },
            {
                "action": "check_sla_queue",
                "rationale": "Confirm SLA at-risk / breached cards on the control tower before paging.",
                "priority": "p1",
                "confidence": 0.5,
                "auto_apply": False,
            },
        ],
        "status": "stub",
        "provider": "template",
        "nim": nim_status,
        "context_preview": context[:200],
    }


def _suggest_via_nim(
    db: Session,
    context: str,
    *,
    actor_type: str | None,
    actor_id: str | None,
) -> dict[str, Any]:
    from porterchain_api.intelligence_engine import nim_client
    from porterchain_api.intelligence_engine.usage import record_ai_usage

    result = nim_client.chat_completion(
        messages=[
            {"role": "system", "content": _SYSTEM_PLAYBOOK},
            {"role": "user", "content": context[:4000]},
        ],
        temperature=0.15,
        max_tokens=700,
        json_object=True,
    )
    record_ai_usage(
        db,
        provider="nvidia_nim",
        model=result["model"],
        feature="ops_copilot",
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        latency_ms=result["latency_ms"],
        status="ok",
        actor_type=actor_type,
        actor_id=actor_id,
        meta={"raw_id": result.get("raw_id")},
    )
    suggestions = _parse_suggestions(result["content"])
    return {
        "suggestions": suggestions,
        "status": "ok",
        "provider": "nvidia_nim",
        "model": result["model"],
        "latency_ms": result["latency_ms"],
        "nim": nim_client.nim_status(),
        "context_preview": context[:200],
    }


def _normalize_action(raw: str) -> str | None:
    slug = re.sub(r"[^a-z0-9_]+", "_", raw.strip().lower()).strip("_")
    if slug in ALLOWED_ACTIONS:
        return slug
    aliases = {
        "check_fleetbase": "review_fleetbase_console",
        "open_fleetbase": "review_fleetbase_console",
        "reassign": "reassign_candidate",
        "reassign_driver": "reassign_candidate",
        "call_merchant": "contact_merchant",
        "escalate": "escalate_ops_lead",
        "pod": "verify_pod_exception",
        "sync_retry": "retry_fleetbase_sync",
    }
    mapped = aliases.get(slug)
    return mapped if mapped in ALLOWED_ACTIONS else None


def _parse_suggestions(content: str) -> list[dict[str, Any]]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    # Extract first JSON object if model wrapped prose
    if not text.startswith("{") and not text.startswith("["):
        match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if match:
            text = match.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return [
            {
                "action": "review_ops_notes",
                "rationale": text[:400] or "NIM returned non-JSON; review context manually.",
                "priority": "p2",
                "confidence": 0.3,
                "auto_apply": False,
            }
        ]
    rows = data.get("suggestions") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows[:6]:
        if not isinstance(row, dict):
            continue
        action = _normalize_action(str(row.get("action") or ""))
        if not action:
            continue
        priority = str(row.get("priority") or "p2").lower()
        if priority not in {"p0", "p1", "p2"}:
            priority = "p2"
        try:
            confidence = float(row.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))
        out.append(
            {
                "action": action[:80],
                "rationale": str(row.get("rationale") or "")[:500],
                "priority": priority,
                "confidence": confidence,
                "auto_apply": False,
            }
        )
        if len(out) >= 4:
            break
    priority_rank = {"p0": 0, "p1": 1, "p2": 2}
    out.sort(key=lambda s: (priority_rank.get(s["priority"], 9), -s["confidence"]))
    return out
