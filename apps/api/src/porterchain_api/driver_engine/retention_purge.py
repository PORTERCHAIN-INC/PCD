"""Apply the dispatch retention policy to driver-owned data (GPS pings, POD refs)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

CLOSED_STATES = ("DELIVERED", "COMPLETED", "CANCELLED", "RETURNED", "FAILED")


def purge(db: Session, policy: dict[str, Any], *, now: datetime | None = None, dry_run: bool = True) -> dict[str, Any]:
    from porterchain_api.booking_models import Order
    from porterchain_api.driver_models import DriverLocationPing, DriverStopMeta

    now = now or datetime.now(UTC)
    cut = {
        "gps_before": now - timedelta(days=int(policy["gps_days"])),
        "pod_before": now - timedelta(days=int(policy["pod_days"])),
    }
    gps_q = db.query(DriverLocationPing).filter(DriverLocationPing.created_at < cut["gps_before"])
    gps = gps_q.count()

    pod_rows = (
        db.query(DriverStopMeta)
        .join(Order, Order.id == DriverStopMeta.order_id)
        .filter(Order.state.in_(CLOSED_STATES), Order.updated_at < cut["pod_before"])
        .all()
    )
    from porterchain_api.driver_engine import pod_store

    pod = files = file_bytes = files_deleted = 0
    for row in pod_rows:
        proofs = list((row.meta or {}).get("proofs", []))
        live = [p for p in proofs if p.get("value") != "redacted"]
        if not live:
            continue
        pod += len(live)
        refs = [str(p.get("value")) for p in live if pod_store.is_ref(p.get("value"))]
        files += len(refs)
        file_bytes += sum(pod_store.size(r) for r in refs)
        if not dry_run and policy.get("enabled", True):
            # File first, then the reference — a crash leaves a ref to a missing file, never an orphan file.
            files_deleted += sum(1 for r in refs if pod_store.delete(r))
        if not dry_run:
            meta = dict(row.meta or {})
            meta["proofs"] = [{"type": p.get("type"), "value": "redacted", "redacted_at": now.isoformat()} for p in proofs]
            row.meta = meta

    if not dry_run and policy.get("enabled", True):
        gps_q.delete(synchronize_session=False)
        db.commit()
    elif not dry_run:
        db.rollback()
        return {"dry_run": False, "enabled": False, "gps_pings": 0, "pod_refs": 0, "pod_files": 0,
                "pod_file_bytes": 0, "pod_files_deleted": 0}
    return {
        "dry_run": dry_run,
        "enabled": bool(policy.get("enabled", True)),
        "gps_pings": gps,
        "pod_refs": pod,
        "pod_files": files,
        "pod_file_bytes": file_bytes,
        "pod_files_deleted": files_deleted,
        "gps_before": cut["gps_before"].isoformat(),
        "pod_before": cut["pod_before"].isoformat(),
    }
