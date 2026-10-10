"""Merchant scheduled pickups → planning batches + day plans.

Planning layer: group open scheduled orders by merchant + date.
Execution layer: accepted sequences in ``sequence_store`` (one van).
Creating a plan remains Optimize Accept — not rebuilt here.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.states import OrderType
from porterchain_api.merchant_models import Merchant
from porterchain_api.booking_models import Order

logger = logging.getLogger(__name__)

# Local copy avoids importing order_engine.buckets (circular with booking_engine).
TERMINAL = frozenset(
    {
        "DELIVERED",
        "POD_COMPLETED",
        "INVOICED",
        "CLOSED",
        "CANCELLED",
        "FAILED",
        "LOST",
        "DAMAGED",
        "RETURN_TO_SENDER",
    }
)


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=UTC).replace(tzinfo=None)
    end = start + timedelta(days=1)
    return start, end


def _is_scheduled_pickup(order: Order) -> bool:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    kind = str(meta.get("order_kind") or "").lower()
    if kind == "scheduled_pickup":
        return True
    if str(order.order_type or "").upper() == OrderType.SCHEDULED.value:
        return True
    mode = str(meta.get("schedule_mode") or "").lower()
    return mode in {"scheduled", "later", "schedule"}


def _stop_count(order: Order) -> int:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    rich = meta.get("stops")
    if isinstance(rich, list) and rich:
        return len([s for s in rich if isinstance(s, dict)])
    extras = meta.get("additional_stops") or []
    return 2 + (len(extras) if isinstance(extras, list) else 0)


def _pickup_window(order: Order) -> tuple[str | None, str | None]:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    rich = meta.get("stops")
    if isinstance(rich, list):
        pickups = [
            s
            for s in rich
            if isinstance(s, dict) and str(s.get("type") or "").lower() == "pickup"
        ]
        if pickups:
            p = sorted(pickups, key=lambda s: s.get("sequence", 0))[0]
            return p.get("time_window_start"), p.get("time_window_end")
    window = meta.get("delivery_window") if isinstance(meta.get("delivery_window"), dict) else {}
    return window.get("start"), window.get("end")


def _order_row(order: Order) -> dict[str, Any]:
    pickup = order.pickup or {}
    win_start, win_end = _pickup_window(order)
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    return {
        "id": order.id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "state": order.state,
        "scheduled_at": order.scheduled_at.isoformat() if order.scheduled_at else None,
        "pickup": pickup.get("formatted") or pickup.get("city"),
        "stop_count": _stop_count(order),
        "order_kind": meta.get("order_kind"),
        "amount_cents": order.amount_cents,
        "pickup_window_start": win_start,
        "pickup_window_end": win_end,
    }


class ScheduledBatchesService:
    def list_batches(
        self,
        db: Session,
        *,
        day: date | None = None,
        merchant_id: str | None = None,
    ) -> dict[str, Any]:
        target = day or datetime.now(UTC).date()
        start, end = _day_bounds(target)

        q = db.query(Order).filter(
            Order.scheduled_at >= start,
            Order.scheduled_at < end,
            Order.state.notin_(TERMINAL),
        )
        if merchant_id:
            q = q.filter(Order.merchant_id == merchant_id)

        candidates = q.order_by(Order.scheduled_at.asc()).limit(500).all()
        orders = [o for o in candidates if _is_scheduled_pickup(o)]

        merchant_ids = {o.merchant_id for o in orders if o.merchant_id}
        merchants = {
            m.id: m.company_name
            for m in db.query(Merchant).filter(Merchant.id.in_(merchant_ids)).all()
        } if merchant_ids else {}

        grouped: dict[str, list[Order]] = defaultdict(list)
        for o in orders:
            grouped[o.merchant_id or "_unassigned"].append(o)

        batches: list[dict[str, Any]] = []
        for mid, rows in grouped.items():
            rows_sorted = sorted(rows, key=lambda o: o.scheduled_at or datetime.min)
            windows = [_pickup_window(o) for o in rows_sorted]
            starts = [w[0] for w in windows if w[0]]
            ends = [w[1] for w in windows if w[1]]
            pickup = rows_sorted[0].pickup or {}
            batches.append(
                {
                    "merchant_id": None if mid == "_unassigned" else mid,
                    "merchant_name": merchants.get(mid) if mid != "_unassigned" else "Unassigned",
                    "pickup_address": pickup.get("formatted") or pickup.get("city"),
                    "pickup_window_start": min(starts) if starts else None,
                    "pickup_window_end": max(ends) if ends else None,
                    "order_count": len(rows_sorted),
                    "amount_cents": sum(o.amount_cents or 0 for o in rows_sorted),
                    "orders": [_order_row(o) for o in rows_sorted],
                }
            )

        batches.sort(key=lambda b: (-b["order_count"], b.get("merchant_name") or ""))
        return {
            "date": target.isoformat(),
            "batch_count": len(batches),
            "order_count": sum(b["order_count"] for b in batches),
            "batches": batches,
        }

    def list_manifests(
        self,
        db: Session,
        *,
        scheduled_date: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """The day's PorterChain pickup batches. A person still assigns the van."""
        del status
        day = scheduled_date or datetime.now(UTC).date().isoformat()
        try:
            target = datetime.fromisoformat(day).date()
        except ValueError:
            target = datetime.now(UTC).date()
        batches = self.list_batches(db, day=target)
        manifests = [
            {
                "id": batch.get("merchant_id"),
                "public_id": batch.get("merchant_name") or "Unassigned",
                "status": "scheduled",
                "scheduled_date": batches.get("date"),
                "stop_count": batch.get("order_count"),
                "driver_name": None,
                "vehicle_name": None,
            }
            for batch in batches.get("batches") or []
        ]
        return {
            "date": batches.get("date") or day,
            "source": "porterchain",
            "manifest_count": len(manifests),
            "manifests": manifests,
            "note": "PorterChain scheduled pickups. Assign a van, then Optimize orders that van.",
        }

    def get_manifest(self, db: Session, manifest_id: str) -> dict[str, Any] | None:
        listed = self.list_manifests(db)
        for row in listed.get("manifests") or []:
            if str(row.get("id") or "") == manifest_id:
                return row
        return None
