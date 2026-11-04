"""Admin: register / change / end our GST/HST registration (append-only history).

The single source is ``platform/tax_registration.py``; this module only adds the
admin write path (audit + price-version bump + commit). Routers stay thin.
Rules: docs/compliance/INVOICE_ADJUSTMENTS_CANADA.md §10 (small supplier, ETA s.148).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.pricing_versioning import bump_price_version
from porterchain_api.platform import tax_registration as reg


def change_registration(
    db: Session,
    ctx: Any,
    *,
    gst_hst_number: str | None,
    legal_name: str | None,
    effective_from: str,
    note: str | None = None,
) -> dict[str, Any]:
    before = reg.registration_status(db)
    row = reg.record_registration(
        db,
        gst_hst_number=gst_hst_number,
        legal_name=legal_name,
        effective_from=effective_from,
        actor_id=ctx.user.id if ctx else None,
        note=note,
    )
    log_admin_audit(
        db,
        ctx,
        action="finance.tax_registration.changed",
        resource_type="tax_registration",
        resource_id=row.id,
        payload={
            "from": {
                "gst_hst_number": before["gst_hst_number"] or None,
                "legal_name": before["legal_name"],
                "effective_from": before["effective_from"],
            },
            "to": {
                "gst_hst_number": row.gst_hst_number,
                "legal_name": row.legal_name,
                "effective_from": row.effective_from.isoformat(),
            },
            "note": row.note,
        },
    )
    # Quotes priced from now on must pick up (or drop) tax.
    bump_price_version(db, ctx, source="finance:tax_registration", reason=row.note)
    db.commit()
    reg.clear_cache(db)
    return reg.registration_status(db)
