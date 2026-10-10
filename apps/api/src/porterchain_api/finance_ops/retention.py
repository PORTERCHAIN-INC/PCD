"""Records retention for Interac e-Transfer rows (CRA books and records + PIPEDA).

Keep ``interac_retention_years`` (default 7, never below 6) from receipt; then delete.
Only closed rows go (approved / rejected / duplicate); anything still open is kept.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import InteracTransfer

MIN_YEARS = 6
CLOSED = ("approved", "rejected", "duplicate")


def purge_expired_interac(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    from porterchain_api.admin_engine.platform_settings import finance_number
    from porterchain_api.platform.admin_audit import log_admin_audit

    years = max(MIN_YEARS, int(finance_number(db, "interac_retention_years", 7)))
    cutoff = (now or datetime.now(UTC)) - timedelta(days=365 * years + years // 4)
    when = func.coalesce(InteracTransfer.received_at, InteracTransfer.created_at)
    q = db.query(InteracTransfer).filter(when < cutoff, InteracTransfer.status.in_(CLOSED))
    count = q.count()
    if count:
        q.delete(synchronize_session=False)
        log_admin_audit(db, None, action="finance.interac.retention_purge", resource_type="interac_transfer",
                        resource_id="*", payload={"deleted": count, "cutoff": cutoff.isoformat(), "years": years})
    db.commit()
    return {"deleted": count, "years": years}
