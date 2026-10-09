"""Writer for the pricing version counter (admin_models are owned by admin_engine)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_models import SystemConfig
from porterchain_api.domain.pricing_version import VERSION_KEY, format_version


def bump_price_version(db: Session, ctx: Any, *, source: str, reason: str | None = None) -> str:
    """Next version (flushed, not committed — the caller's commit carries it)."""
    row = db.query(SystemConfig).filter(SystemConfig.key == VERSION_KEY).first()
    old = dict(row.value) if row and isinstance(row.value, dict) else {"version": 0}
    try:
        n = int(old.get("version") or 0) + 1
    except (TypeError, ValueError):
        n = 1
    user = getattr(ctx, "user", None)
    new = {
        "version": n,
        "updated_at": datetime.now(UTC).isoformat(),
        "updated_by": getattr(user, "id", None),
        "source": source,
        "reason": reason,
    }
    if row:
        row.value = new
    else:
        db.add(SystemConfig(key=VERSION_KEY, value=new))
    log_admin_audit(
        db,
        ctx if user is not None else None,
        action="pricing.version.bump",
        resource_type="system_config",
        resource_id=VERSION_KEY,
        payload={"old": old, "new": new, "reason": reason},
    )
    db.flush()
    return format_version(new)
