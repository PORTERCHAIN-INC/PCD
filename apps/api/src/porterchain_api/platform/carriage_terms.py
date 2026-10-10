"""Effective carriage terms for a merchant: global setting + their contract overrides."""

from __future__ import annotations

from typing import Any

from porterchain_pricing.contract_terms import terms_of


def merchant_carriage_terms(db: Any, merchant: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig
    from porterchain_pricing.contract_schedule import load_contract_schedule

    row = db.get(SystemConfig, "carriage_terms")
    global_terms = row.value if row is not None and isinstance(row.value, dict) else None
    sched = ((merchant.pricing_config or {}).get("schedule") or {}) if merchant else {}
    sid = sched.get("contract_schedule")
    schedule = load_contract_schedule(sid, sched.get("contract_overrides")) if sid else None
    return terms_of(schedule, global_terms)
