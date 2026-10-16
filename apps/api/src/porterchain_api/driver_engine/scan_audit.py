"""Driver label-scan audit + rate limit (Oct 2026).

Every scan (lookup, pickup, delivery) is written to the immutable ``domain_events``
log — staff-only, never shown to merchants or customers (GPS stays internal).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

SCAN_EVENT = "driver.label_scanned"
SCAN_LIMIT_PER_MINUTE = 90  # a fast pickup of 60 boxes still fits
TRAFFIC_DRIVER_SCAN = "driver_scan"


def _num(v: Any, lo: float, hi: float) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if lo <= f <= hi else None


def _client_time(v: Any) -> str | None:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).isoformat()
    except ValueError:
        return None


def enforce_scan_rate(driver_id: str) -> None:
    """429 when a driver exceeds the scan budget. Fails OPEN if Redis is down
    (never strand a driver at a warehouse); the miss is counted."""
    from fastapi import HTTPException

    from porterchain_api.platform.rate_limit import (
        bucket_key,
        check_fixed_window,
        incr_rate_limit_unavailable,
        incr_rate_limited,
    )

    allowed, _cur, err = check_fixed_window(
        bucket_key(TRAFFIC_DRIVER_SCAN, driver_id), SCAN_LIMIT_PER_MINUTE
    )
    if err:
        incr_rate_limit_unavailable(TRAFFIC_DRIVER_SCAN)
        return
    if not allowed:
        incr_rate_limited(TRAFFIC_DRIVER_SCAN)
        raise HTTPException(status_code=429, detail={"code": "scan_rate_limited"})


def log_scan(
    db: Session,
    *,
    driver_id: str,
    kind: str,
    result: str,
    body: dict[str, Any] | None,
    package_id: str | None = None,
    order_id: str | None = None,
) -> None:
    """Best-effort: an audit write failure must never block a delivery."""
    from porterchain_api.booking_models import DomainEvent

    b = body or {}
    payload = {
        "kind": kind,  # lookup | pickup | delivery
        "result": result,  # ok | not_yours | invalid | wrong_stop | error code
        "package_id": package_id,
        "order_id": order_id,
        "lat": _num(b.get("lat"), -90, 90),
        "lng": _num(b.get("lng"), -180, 180),
        "accuracy_m": _num(b.get("accuracy_m"), 0, 100000),
        "scanned_at_client": _client_time(b.get("scanned_at")),
        "received_at": datetime.now(UTC).isoformat(),
        "offline_replay": bool(b.get("offline_replay")),
    }
    try:
        with db.begin_nested():
            db.add(
                DomainEvent(
                    event_type=SCAN_EVENT,
                    aggregate_type="driver",
                    aggregate_id=driver_id,
                    actor_type="driver",
                    actor_id=driver_id,
                    payload=payload,
                )
            )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


def scan_history(db: Session, driver_id: str, limit: int = 50) -> list[dict[str, Any]]:
    from porterchain_api.booking_models import DomainEvent

    rows = (
        db.query(DomainEvent)
        .filter(
            DomainEvent.event_type == SCAN_EVENT,
            DomainEvent.aggregate_type == "driver",
            DomainEvent.aggregate_id == driver_id,
        )
        .order_by(DomainEvent.occurred_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    out = []
    for r in rows:
        p = r.payload or {}
        out.append(
            {
                "at": r.occurred_at.isoformat() if r.occurred_at else None,
                "kind": p.get("kind"),
                "result": p.get("result"),
                "order_id": p.get("order_id") if p.get("result") != "not_yours" else None,
                "package_id": p.get("package_id") if p.get("result") != "not_yours" else None,
            }
        )
    return out


def audited_package_scan(db: Session, driver_id: str, order_id: str, body: dict | None, run) -> Any:
    """Run a pickup/delivery scan and audit the outcome (ok / not_yours / wrong_stop / code)."""
    phase = str((body or {}).get("phase") or "pickup").lower()

    def _audit(result: str, package_id: str | None = None) -> None:
        log_scan(db, driver_id=driver_id, kind=phase, result=result, body=body,
                 package_id=package_id, order_id=None if result == "not_yours" else order_id)

    try:
        res = run()
    except PermissionError:
        _audit("not_yours")
        raise
    except LookupError as exc:
        _audit("not_yours" if str(exc) == "order_not_found" else str(exc))
        raise
    except ValueError as exc:
        # qr_order_mismatch = parcel belongs to another stop/order: wrong-stop warning.
        _audit("wrong_stop" if str(exc) == "qr_order_mismatch" else str(exc))
        raise
    _audit("ok", (res or {}).get("package_id") if isinstance(res, dict) else None)
    return res


def scan_error_code(code: str) -> str:
    """Driver app 1.0.0 (b29) shows its wrong-box message only for codes containing
    ``unknown_package``; keep the precise code as the prefix for newer clients."""
    if code in ("invalid_label_qr", "package_not_found"):
        return f"{code}_unknown_package"
    return code
