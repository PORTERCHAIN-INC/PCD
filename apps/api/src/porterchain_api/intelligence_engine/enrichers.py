"""Optional NVIDIA NIM language enrichers — never decide money, dispatch, or Fleetbase writes.

Risk enums / scores stay rule-based. Fail soft to heuristics when phase2 is off,
NIM is missing, or the circuit is open.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_M360_SYSTEM = """You rewrite merchant ops next-actions for PorterChain admins.
Rules:
1. Return ONLY JSON: {"suggested_actions":["...","...","..."]}
2. Keep 2–4 short imperative sentences. Same intent as the input list — paraphrase, do not invent AR amounts, contracts, or API claims.
3. Never invent payment cents, legal terms, or driver/Fleetbase state.
4. No markdown."""

_ASSIST_SYSTEM = """You polish a customer shipment update for PorterChain.
Rules:
1. Return ONLY JSON: {"sms":string,"email_body":string}
2. Keep tracking number and state accurate. SMS ≤160 chars. Email stays plain text, professional, short.
3. Do not invent ETAs, driver names, addresses, or payment info.
4. Sign email as PorterChain. No markdown."""

_RATIONALE_SYSTEM = """You write one short dispatcher rationale sentence for PorterChain ops.
Rules:
1. Return ONLY JSON: {"narrative":string}
2. Narrative ≤180 chars. Use only the provided reason bits and ETA facts — do not invent GPS or scores.
3. Do not recommend a different driver. Explain ≠ decide."""


def _phase2_ready(flags: dict[str, bool] | None) -> bool:
    from porterchain_api.intelligence_engine import phase2_intelligence_enabled

    return phase2_intelligence_enabled(flags or {})


def _can_call_nim(db: Session | None) -> bool:
    if db is None:
        return False
    from porterchain_api.intelligence_engine import nim_client

    status = nim_client.nim_status()
    return bool(status.get("configured") and not status.get("circuit_open"))


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(1)
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def _call_nim(
    db: Session,
    *,
    feature: str,
    system: str,
    user: str,
    max_tokens: int = 400,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any] | None:
    from porterchain_api.db import SessionLocal
    from porterchain_api.intelligence_engine import nim_client
    from porterchain_api.intelligence_engine.usage import record_ai_usage

    def _persist_usage(**kwargs: Any) -> None:
        # Isolated session so read-only routes still persist metering without
        # committing the request unit of work.
        log_db = SessionLocal()
        try:
            record_ai_usage(log_db, **kwargs)
            log_db.commit()
        except Exception as persist_exc:  # noqa: BLE001
            logger.debug("ai_usage persist failed: %s", persist_exc)
            log_db.rollback()
        finally:
            log_db.close()

    del db  # request session reserved for domain reads; metering is isolated
    try:
        result = nim_client.chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user[:3500]},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            timeout_s=12.0,
            json_object=True,
            max_retries=1,
        )
        _persist_usage(
            provider="nvidia_nim",
            model=result["model"],
            feature=feature,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            latency_ms=result["latency_ms"],
            status="ok",
            actor_type=actor_type,
            actor_id=actor_id,
            meta={"raw_id": result.get("raw_id")},
        )
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("NIM enricher %s failed: %s", feature, exc)
        try:
            from porterchain_shared.config.settings import get_platform_settings

            settings = get_platform_settings()
            _persist_usage(
                provider="nvidia_nim",
                model=getattr(settings, "nvidia_model", "unknown") or "unknown",
                feature=feature,
                status="error",
                error=str(exc),
                actor_type=actor_type,
                actor_id=actor_id,
            )
        except Exception:  # noqa: BLE001
            pass
        return None


def paraphrase_merchant_actions(
    insights: dict[str, Any],
    *,
    flags: dict[str, bool] | None = None,
    db: Session | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Keep risk enums; optionally paraphrase suggested_actions via NIM."""
    out = dict(insights)
    out.setdefault("actions_source", "heuristic")
    actions = [str(a) for a in (insights.get("suggested_actions") or []) if str(a).strip()]
    if not actions or not _phase2_ready(flags) or not _can_call_nim(db):
        return out
    assert db is not None
    payload = {
        "risk_score": insights.get("risk_score"),
        "payment_risk": insights.get("payment_risk"),
        "renewal_risk": insights.get("renewal_risk"),
        "revenue_trend": insights.get("revenue_trend"),
        "suggested_actions": actions,
    }
    result = _call_nim(
        db,
        feature="merchant360_actions",
        system=_M360_SYSTEM,
        user=json.dumps(payload),
        max_tokens=350,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    if not result:
        return out
    try:
        data = _parse_json_object(result["content"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return out
    rewritten = data.get("suggested_actions")
    if not isinstance(rewritten, list):
        return out
    cleaned = [str(row).strip()[:240] for row in rewritten if str(row).strip()][:4]
    if not cleaned:
        return out
    out["suggested_actions"] = cleaned
    out["actions_source"] = "nvidia_nim"
    out["actions_model"] = result.get("model")
    return out


def polish_message_draft(
    *,
    sms: str,
    email_body: str,
    tracking_number: str,
    state: str,
    flags: dict[str, bool] | None = None,
    db: Session | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> dict[str, Any]:
    """Return polished sms/email_body + draft_source; falls back to inputs."""
    base: dict[str, Any] = {"sms": sms, "email_body": email_body, "draft_source": "heuristic"}
    if not _phase2_ready(flags) or not _can_call_nim(db):
        return base
    assert db is not None
    result = _call_nim(
        db,
        feature="order_assist_draft",
        system=_ASSIST_SYSTEM,
        user=json.dumps(
            {
                "tracking_number": tracking_number,
                "state": state,
                "sms": sms,
                "email_body": email_body,
            }
        ),
        max_tokens=450,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    if not result:
        return base
    try:
        data = _parse_json_object(result["content"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return base
    new_sms = str(data.get("sms") or "").strip()
    new_email = str(data.get("email_body") or "").strip()
    if tracking_number and tracking_number not in new_sms and tracking_number not in new_email:
        return base
    if new_sms:
        base["sms"] = new_sms[:160]
    if new_email:
        base["email_body"] = new_email[:2000]
    if new_sms or new_email:
        base["draft_source"] = "nvidia_nim"
    return base


def explain_dispatch_rationale(
    reason_bits: list[str],
    *,
    flags: dict[str, bool] | None = None,
    db: Session | None = None,
    actor_type: str | None = None,
    actor_id: str | None = None,
) -> str | None:
    """Optional one-line narrative after score — never changes ranking."""
    bits = [str(b).strip() for b in reason_bits if str(b).strip()]
    if not bits or not _phase2_ready(flags) or not _can_call_nim(db):
        return None
    assert db is not None
    result = _call_nim(
        db,
        feature="dispatch_rationale",
        system=_RATIONALE_SYSTEM,
        user=json.dumps({"reasons": bits}),
        max_tokens=120,
        actor_type=actor_type,
        actor_id=actor_id,
    )
    if not result:
        return None
    try:
        data = _parse_json_object(result["content"])
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    narrative = str(data.get("narrative") or "").strip()
    return narrative[:180] or None
