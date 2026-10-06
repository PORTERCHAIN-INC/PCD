"""Read-only tools for ops NIM context — never mutate Stripe, day plans, or orders.

Used to ground suggest_ops_action with live PorterChain snapshots. Tools return
JSON-serialisable dicts suitable for prompt injection only.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

READONLY_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "get_merchant_snapshot",
        "get_sla_queue",
        "get_optimize_run",
        "get_manifest_summary",
        "get_fsa_coverage",
        "get_fuel_delta",
    }
)

_MERCHANT_ID_RE = re.compile(
    r"\b(?:merchant[_ ]?id|merchant)\s*[:=]\s*([0-9a-f-]{36})\b",
    re.IGNORECASE,
)


def get_merchant_snapshot(db: Session, merchant_id: str) -> dict[str, Any]:
    """Light merchant 360 facts for language assist — no inventing AR or contracts."""
    from porterchain_api.merchant_models import Merchant

    mid = (merchant_id or "").strip()
    if not mid:
        return {"tool": "get_merchant_snapshot", "error": "merchant_id_required"}
    merchant = db.get(Merchant, mid)
    if not merchant:
        return {"tool": "get_merchant_snapshot", "error": "merchant_not_found", "merchant_id": mid}

    outstanding = overdue = 0
    try:
        from porterchain_api.billing_engine.ar import merchant_ar

        ar = merchant_ar(db, merchant)
        outstanding = int(ar.outstanding_cents)
        overdue = int(ar.overdue_cents)
    except Exception as exc:  # noqa: BLE001
        logger.debug("merchant_ar for tool failed: %s", exc)

    profile = merchant.profile if isinstance(merchant.profile, dict) else {}
    enterprise = profile.get("enterprise") if isinstance(profile.get("enterprise"), dict) else {}
    return {
        "tool": "get_merchant_snapshot",
        "merchant_id": merchant.id,
        "company_name": merchant.company_name,
        "status": merchant.status,
        "payment_terms": merchant.payment_terms,
        "billing_cycle": merchant.billing_cycle,
        "support_tier": enterprise.get("support_tier") or "standard",
        "outstanding_balance_cents": outstanding,
        "overdue_balance_cents": overdue,
        "note": "Read-only snapshot. Do not invent additional AR or contract state.",
    }


def get_sla_queue(db: Session, *, limit: int = 12) -> dict[str, Any]:
    """Compact SLA at-risk / breached cards for ops triage."""
    from porterchain_api.admin_engine.control_tower.service import ControlTowerService

    raw = ControlTowerService().sla_monitor(db, limit=max(1, min(limit, 40)))
    def _slim(card: dict[str, Any]) -> dict[str, Any]:
        return {
            "tracking_number": card.get("tracking_number") or card.get("order_number"),
            "order_id": card.get("id") or card.get("order_id"),
            "state": card.get("state"),
            "merchant": card.get("merchant_name") or card.get("merchant"),
            "eta": card.get("eta"),
            "sla": card.get("sla") or card.get("sla_status"),
        }

    breached = [_slim(c) for c in (raw.get("breached") or [])[:limit] if isinstance(c, dict)]
    at_risk = [_slim(c) for c in (raw.get("at_risk") or [])[:limit] if isinstance(c, dict)]
    return {
        "tool": "get_sla_queue",
        "breached_count": int(raw.get("breached_count") or len(breached)),
        "at_risk_count": int(raw.get("at_risk_count") or len(at_risk)),
        "breached": breached,
        "at_risk": at_risk,
        "note": "Read-only SLA queue. Prefer the live map and day plan before reassign suggestions.",
    }


def get_optimize_run(db: Session, run_id: str) -> dict[str, Any]:
    """Slim PorterChain day-plan run for NIM insert/reject narration."""
    del db  # run store is Redis — Session unused but keeps tool signature uniform
    from porterchain_api.admin_engine.orchestrator_ops_service import OrchestratorOpsService

    rid = (run_id or "").strip()
    if not rid:
        return {"tool": "get_optimize_run", "error": "run_id_required"}
    rec = OrchestratorOpsService().get_run(rid)
    if not rec:
        return {"tool": "get_optimize_run", "error": "run_not_found", "run_id": rid}
    metrics = rec.get("metrics") if isinstance(rec.get("metrics"), dict) else {}
    unassigned = [
        {
            "order_id": d.get("porterchain_order_id") or d.get("order_id"),
            "reason": d.get("reason") or d.get("code"),
        }
        for d in (rec.get("unassigned_details") or [])
        if isinstance(d, dict)
    ][:20]
    return {
        "tool": "get_optimize_run",
        "run_id": rid,
        "status": rec.get("status"),
        "mode": rec.get("mode"),
        "engine": rec.get("engine") or metrics.get("engine"),
        "shape": rec.get("shape"),
        "assigned_count": metrics.get("assigned_count"),
        "unassigned_count": metrics.get("unassigned_count"),
        "capacity_reject_count": metrics.get("capacity_reject_count"),
        "after_distance_km": metrics.get("after_distance_km"),
        "estimated_fuel_cents": metrics.get("estimated_fuel_cents"),
        "estimated_fuel_liters": metrics.get("estimated_fuel_liters"),
        "fuel_delta_cents": metrics.get("fuel_delta_cents"),
        "valhalla_costing": metrics.get("valhalla_costing"),
        "unassigned": unassigned,
        "note": (
            "Read-only. Explain insert vs capacity reject from unassigned reasons; "
            "never invent routes or commit manifests."
        ),
    }


def get_manifest_summary(db: Session, driver_id: str) -> dict[str, Any]:
    """Applied PorterChain day-plan waypoints for a driver."""
    del db
    from porterchain_driver.sequence_store import read_sequence

    did = (driver_id or "").strip()
    if not did:
        return {"tool": "get_manifest_summary", "error": "driver_id_required"}
    plan = read_sequence(did)
    if not plan:
        return {
            "tool": "get_manifest_summary",
            "driver_id": did,
            "waypoints": [],
            "note": "No accepted day plan for this driver yet.",
        }
    waypoints = plan.get("waypoints") if isinstance(plan.get("waypoints"), list) else []
    slim = [
        {
            "sequence": w.get("sequence"),
            "order_id": w.get("order_id"),
            "stop_type": w.get("stop_type"),
        }
        for w in waypoints
        if isinstance(w, dict)
    ][:40]
    return {
        "tool": "get_manifest_summary",
        "driver_id": did,
        "run_id": plan.get("run_id"),
        "engine": plan.get("engine"),
        "waypoint_count": len(slim),
        "waypoints": slim,
        "note": "Read-only accepted day plan. Optimize Accept remains commit SoT.",
    }


def get_fsa_coverage(db: Session, fsa: str) -> dict[str, Any]:
    """Whether an FSA is in the GTA150 tile + optional rate presence (Phase 1)."""
    from porterchain_pricing.components.fsa import is_ontario_fsa, normalize_fsa
    from porterchain_pricing.gta150_fsa import gta150_fsa_record, is_gta150_fsa

    code = normalize_fsa(fsa)
    if not code:
        return {"tool": "get_fsa_coverage", "error": "fsa_required"}
    record = gta150_fsa_record(code)
    rated = False
    try:
        from porterchain_api.admin_models import PricingFsaRate

        rated = (
            db.query(PricingFsaRate.id)
            .filter(
                PricingFsaRate.dest_fsa == code,
                PricingFsaRate.is_active.is_(True),
            )
            .first()
            is not None
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("fsa rate lookup failed: %s", exc)
    return {
        "tool": "get_fsa_coverage",
        "fsa": code,
        "ontario_district": is_ontario_fsa(code),
        "in_gta150_tile": is_gta150_fsa(code),
        "has_active_rate_row": rated,
        "label": (record or {}).get("label") or (record or {}).get("city"),
        "note": (
            "In-tile + no rate → Valhalla distance floor. "
            "Out-of-tile Ontario (e.g. Ottawa K*) is not PorterChain same-day tile coverage."
        ),
    }


def get_fuel_delta(
    db: Session,
    *,
    run_id: str | None = None,
    before_km: float | None = None,
    after_km: float | None = None,
    vehicle_class: str | None = None,
) -> dict[str, Any]:
    """Estimate fuel $ / liters delta from plan km (pricing_fuel). Read-only."""
    from porterchain_pricing.fuel_scorecard import fuel_delta
    from porterchain_pricing.types import FuelConfig

    fuel = FuelConfig()
    try:
        from porterchain_api.admin_models import SystemConfig

        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        if row and isinstance(row.value, dict):
            fuel = FuelConfig(
                **{
                    k: v
                    for k, v in row.value.items()
                    if k in FuelConfig.__dataclass_fields__
                }
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("pricing_fuel for get_fuel_delta failed: %s", exc)

    bkm = before_km
    akm = after_km
    vclass = vehicle_class
    rid = (run_id or "").strip()
    if rid:
        from porterchain_api.admin_engine.orchestrator_ops_service import (
            OrchestratorOpsService,
        )

        rec = OrchestratorOpsService().get_run(rid)
        if not rec:
            return {"tool": "get_fuel_delta", "error": "run_not_found", "run_id": rid}
        metrics = rec.get("metrics") if isinstance(rec.get("metrics"), dict) else {}
        if akm is None:
            try:
                akm = float(metrics.get("after_distance_km") or 0)
            except (TypeError, ValueError):
                akm = 0.0
        if bkm is None and metrics.get("before_distance_km") is not None:
            try:
                bkm = float(metrics["before_distance_km"])
            except (TypeError, ValueError):
                bkm = None
        if not vclass:
            vclass = metrics.get("fuel_vehicle_class")
        # When before unknown, narrate absolute after estimate only.
        if bkm is None:
            from porterchain_pricing.fuel_scorecard import enrich_optimize_metrics_fuel

            card = enrich_optimize_metrics_fuel(
                {"after_distance_km": akm or 0},
                fuel=fuel,
                vehicle_class=str(vclass) if vclass else None,
            )
            return {
                "tool": "get_fuel_delta",
                "run_id": rid,
                "after_km": akm,
                "estimated_fuel_cents": card.get("estimated_fuel_cents"),
                "estimated_fuel_liters": card.get("estimated_fuel_liters"),
                "valhalla_costing": metrics.get("valhalla_costing"),
                "note": (
                    "No before_km on this run — absolute estimate only. "
                    "Do not invent left-turn bans; Valhalla already biases right turns."
                ),
            }

    if bkm is None or akm is None:
        return {
            "tool": "get_fuel_delta",
            "error": "before_km_and_after_km_or_run_id_required",
        }

    delta = fuel_delta(
        before_km=float(bkm),
        after_km=float(akm),
        fuel=fuel,
        vehicle_class=str(vclass) if vclass else None,
    )
    return {"tool": "get_fuel_delta", "run_id": rid or None, **delta}


_TOOL_IMPL: dict[str, Callable[..., dict[str, Any]]] = {
    "get_merchant_snapshot": get_merchant_snapshot,
    "get_sla_queue": get_sla_queue,
    "get_optimize_run": get_optimize_run,
    "get_manifest_summary": get_manifest_summary,
    "get_fsa_coverage": get_fsa_coverage,
    "get_fuel_delta": get_fuel_delta,
}


def run_readonly_tool(name: str, db: Session, **kwargs: Any) -> dict[str, Any]:
    if name not in READONLY_TOOL_NAMES:
        return {"tool": name, "error": "unknown_or_forbidden_tool"}
    fn = _TOOL_IMPL[name]
    try:
        if name == "get_merchant_snapshot":
            return fn(db, str(kwargs.get("merchant_id") or ""))
        if name == "get_sla_queue":
            return fn(db, limit=int(kwargs.get("limit") or 12))
        if name == "get_optimize_run":
            return fn(db, str(kwargs.get("run_id") or ""))
        if name == "get_manifest_summary":
            return fn(db, str(kwargs.get("driver_id") or ""))
        if name == "get_fsa_coverage":
            return fn(db, str(kwargs.get("fsa") or ""))
        if name == "get_fuel_delta":
            return fn(
                db,
                run_id=kwargs.get("run_id"),
                before_km=kwargs.get("before_km"),
                after_km=kwargs.get("after_km"),
                vehicle_class=kwargs.get("vehicle_class"),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("readonly tool %s failed: %s", name, exc)
        return {"tool": name, "error": str(exc)[:200]}
    return {"tool": name, "error": "unhandled"}


_RUN_ID_RE = re.compile(r"\brun[_ ]?id\s*[:=]\s*([0-9a-f-]{8,})\b", re.IGNORECASE)
_DRIVER_ID_RE = re.compile(r"\bdriver[_ ]?id\s*[:=]\s*([0-9a-f-]{36})\b", re.IGNORECASE)
_FSA_RE = re.compile(r"\b(?:fsa|postal)\s*[:=]\s*([A-Za-z]\d[A-Za-z])\b")


def extract_merchant_id(context: str) -> str | None:
    match = _MERCHANT_ID_RE.search(context or "")
    return match.group(1) if match else None


def extract_run_id(context: str) -> str | None:
    match = _RUN_ID_RE.search(context or "")
    return match.group(1) if match else None


def extract_driver_id(context: str) -> str | None:
    match = _DRIVER_ID_RE.search(context or "")
    return match.group(1) if match else None


def extract_fsa(context: str) -> str | None:
    match = _FSA_RE.search(context or "")
    return match.group(1).upper() if match else None


def gather_ops_tool_context(
    db: Session,
    *,
    merchant_id: str | None = None,
    include_sla_queue: bool = True,
    context: str | None = None,
) -> dict[str, Any]:
    """Run allowed read-only tools and return a prompt-ready bundle."""
    mid = (merchant_id or "").strip() or extract_merchant_id(context or "")
    run_id = extract_run_id(context or "")
    driver_id = extract_driver_id(context or "")
    fsa = extract_fsa(context or "")
    tools_run: list[dict[str, Any]] = []
    if include_sla_queue:
        tools_run.append(run_readonly_tool("get_sla_queue", db, limit=10))
    if mid:
        tools_run.append(run_readonly_tool("get_merchant_snapshot", db, merchant_id=mid))
    if run_id:
        tools_run.append(run_readonly_tool("get_optimize_run", db, run_id=run_id))
    if driver_id:
        tools_run.append(run_readonly_tool("get_manifest_summary", db, driver_id=driver_id))
    if fsa:
        tools_run.append(run_readonly_tool("get_fsa_coverage", db, fsa=fsa))
    if run_id:
        tools_run.append(run_readonly_tool("get_fuel_delta", db, run_id=run_id))
    return {
        "tools": list(READONLY_TOOL_NAMES),
        "results": tools_run,
    }


def format_tool_bundle_for_prompt(bundle: dict[str, Any]) -> str:
    return "READ-ONLY TOOL RESULTS (ground truth — do not invent beyond this):\n" + json.dumps(
        bundle.get("results") or [],
        default=str,
    )[:3500]
