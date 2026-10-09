"""Admin view: leads by source / industry / FSA / UTM over a window (read-only)."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead

MAX_ROWS = 20_000


def _top(counter: Counter, limit: int = 15) -> list[dict[str, Any]]:
    return [{"key": k, "count": n} for k, n in counter.most_common(limit)]


def _fsa_of(lead: CrmLead) -> str | None:
    cf = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
    for raw in (cf.get("pickup_fsa"), lead.service_area, (lead.address or {}).get("postal") if isinstance(lead.address, dict) else None):
        code = str(raw or "").strip().upper().replace(" ", "")[:3]
        if len(code) == 3 and code[0].isalpha() and code[1].isdigit() and code[2].isalpha():
            return code
    return None


def lead_attribution_summary(db: Session, *, days: int = 30) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = (
        db.execute(
            select(CrmLead).where(CrmLead.created_at >= since).order_by(CrmLead.created_at.desc()).limit(MAX_ROWS)
        )
        .scalars()
        .all()
    )
    by_source: Counter = Counter()
    by_industry: Counter = Counter()
    by_fsa: Counter = Counter()
    by_utm_source: Counter = Counter()
    by_utm_campaign: Counter = Counter()
    calculator = 0
    marketing_opt_in = 0
    for lead in rows:
        cf = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
        by_source[lead.source or "unknown"] += 1
        by_industry[(lead.industry or cf.get("industry") or "unknown")] += 1
        fsa = _fsa_of(lead)
        if fsa:
            by_fsa[fsa] += 1
        by_utm_source[str(cf.get("utm_source") or "(none)")] += 1
        if cf.get("utm_campaign"):
            by_utm_campaign[str(cf["utm_campaign"])] += 1
        if lead.source == "website_calculator":
            calculator += 1
        if isinstance(lead.consent, dict) and lead.consent.get("marketing") is True:
            marketing_opt_in += 1
    return {
        "window_days": days,
        "total": len(rows),
        "truncated": len(rows) >= MAX_ROWS,
        "calculator_leads": calculator,
        "marketing_opt_in": marketing_opt_in,
        "by_source": _top(by_source),
        "by_industry": _top(by_industry),
        "by_fsa": _top(by_fsa, 25),
        "by_utm_source": _top(by_utm_source),
        "by_utm_campaign": _top(by_utm_campaign),
    }
