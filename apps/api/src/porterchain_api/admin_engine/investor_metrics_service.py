"""§10.1 — investor metrics snapshot (counts vs Series A targets)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Order
from porterchain_api.reporting.data_moat import margin_intelligence

TARGETS = {
    "arr_cents": 1_000_000_00,
    "yoy_growth_multiplier": 3.0,
    "software_gross_margin_pct": 75.0,
    "nrr_pct": 110.0,
    "cac_payback_months": 18,
    "icp_logos": 15,
    "acv_cents": 2_400_000,
    "burn_multiple": 2.0,
}


def _partner_logo_count() -> int:
    partners_file = Path(__file__).resolve().parents[5] / "website" / "src" / "content" / "partners.json"
    if not partners_file.is_file():
        return 0
    data = json.loads(partners_file.read_text(encoding="utf-8"))
    logos = data.get("partners") or data.get("logos") or []
    return len(logos) if isinstance(logos, list) else 0


def investor_metrics(db: Session) -> dict[str, Any]:
    now = datetime.now(UTC)
    window_30 = now - timedelta(days=30)
    window_365 = now - timedelta(days=365)

    revenue_30d = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(Order.is_sandbox.is_(False), Order.created_at >= window_30)
        .scalar()
        or 0
    )
    arr_cents = int(revenue_30d) * 12

    revenue_prior = (
        db.query(func.coalesce(func.sum(Order.amount_cents), 0))
        .filter(
            Order.is_sandbox.is_(False),
            Order.created_at >= window_365 - timedelta(days=30),
            Order.created_at < window_365,
        )
        .scalar()
        or 0
    )
    yoy_multiplier = round(arr_cents / int(revenue_prior) / 12, 2) if revenue_prior else 0.0

    active_merchants = (
        db.query(func.count(Merchant.id))
        .filter(Merchant.status == MerchantStatus.ACTIVE.value)
        .scalar()
        or 0
    )
    margin = margin_intelligence(db, window_days=30)
    icp_logos = _partner_logo_count()

    metrics = {
        "arr_cents": {
            "value": arr_cents,
            "target": TARGETS["arr_cents"],
            "meets_target": arr_cents >= TARGETS["arr_cents"],
            "note": "Annualized from trailing 30d platform order revenue",
        },
        "yoy_growth_multiplier": {
            "value": yoy_multiplier,
            "target": TARGETS["yoy_growth_multiplier"],
            "meets_target": yoy_multiplier >= TARGETS["yoy_growth_multiplier"],
        },
        "software_gross_margin_pct": {
            "value": margin["gross_margin_pct"],
            "target": TARGETS["software_gross_margin_pct"],
            "meets_target": margin["gross_margin_pct"] >= TARGETS["software_gross_margin_pct"],
        },
        "nrr_pct": {
            "value": None,
            "target": TARGETS["nrr_pct"],
            "meets_target": False,
            "note": "Requires cohort billing history — wire in Phase 2",
        },
        "cac_payback_months": {
            "value": None,
            "target": TARGETS["cac_payback_months"],
            "meets_target": False,
            "note": "Requires sales spend ledger",
        },
        "icp_logos": {
            "value": icp_logos,
            "target": TARGETS["icp_logos"],
            "meets_target": icp_logos >= TARGETS["icp_logos"],
        },
        "acv_cents": {
            "value": int(arr_cents / active_merchants) if active_merchants else 0,
            "target": TARGETS["acv_cents"],
            "meets_target": (arr_cents / active_merchants) >= TARGETS["acv_cents"] if active_merchants else False,
        },
        "burn_multiple": {
            "value": None,
            "target": TARGETS["burn_multiple"],
            "meets_target": False,
            "note": "Requires finance burn export",
        },
    }
    return {
        "as_of": now.isoformat(),
        "active_merchants": int(active_merchants),
        "metrics": metrics,
        "materials": {
            "deck_outline": "docs/investor/DECK_OUTLINE.md",
            "demo_script": "docs/DEMO_SCRIPT.md",
            "data_room": "docs/investor/DATA_ROOM_INDEX.md",
            "tech_diligence": "docs/investor/TECH_DILIGENCE_PACK.md",
        },
    }


class InvestorMetricsService:
    def snapshot(self, db: Session) -> dict[str, Any]:
        return investor_metrics(db)
