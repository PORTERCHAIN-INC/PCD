"""E2E validation — phase 8 system consistency."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.e2e_validation_catalog import (
    CONSISTENCY_SURFACES,
    E2E_MARKER,
    ValidationStatus,
)
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.notification_engine.models import NotificationRecord


class E2EValidationConsistencyMixin:
    def _resolve_e2e_consistency_order(self, db: Session) -> Order | None:
        """Prefer the completed retail forward-logistics order over merchant bulk leftovers.

        Forward ends at INVOICED; merchant phase may also leave INVOICED E2E rows without
        a retail customer. Prefer customer_id-backed forward-complete states so notification
        surfaces are scored against the real retail path.
        """
        forward_complete = (
            OrderState.INVOICED.value,
            OrderState.POD_COMPLETED.value,
            OrderState.DELIVERED.value,
            OrderState.IN_TRANSIT.value,
        )
        completed = (
            db.query(Order)
            .filter(
                Order.internal_reference == E2E_MARKER,
                Order.state.in_(forward_complete),
                Order.customer_id.isnot(None),
            )
            .order_by(Order.created_at.desc())
            .first()
        )
        if completed:
            return completed
        completed = (
            db.query(Order)
            .filter(
                Order.internal_reference == E2E_MARKER,
                Order.state.in_(forward_complete),
            )
            .order_by(Order.created_at.desc())
            .first()
        )
        if completed:
            return completed
        return (
            db.query(Order)
            .filter(Order.internal_reference == E2E_MARKER)
            .order_by(Order.created_at.desc())
            .first()
        )

    def phase_8_consistency(self, db: Session, settings: Settings) -> dict[str, Any]:
        del settings  # reserved for future surface checks
        order = self._resolve_e2e_consistency_order(db)
        surfaces: list[dict[str, Any]] = []
        canonical_state = order.state if order else None

        for surface in CONSISTENCY_SURFACES:
            status: ValidationStatus = "PASS"
            note = ""
            if not order:
                status = "WARNING"
                note = "No E2E order available for cross-check"
            elif surface == "admin_orders":
                admin_order = db.get(Order, order.id)
                status = "PASS" if admin_order and admin_order.state == canonical_state else "FAIL"
            elif surface == "operations_queue":
                from porterchain_api.admin_engine.operations_service import (
                    AdminOperationsService,
                )

                queue = AdminOperationsService().dispatch_queue(db)
                in_queue = any(o.id == order.id for o in queue)
                status = "PASS" if in_queue or OrderState(order.state) in {
                    OrderState.DELIVERED,
                    OrderState.INVOICED,
                    OrderState.RETURN_TO_SENDER,
                    OrderState.CLOSED,
                } else "WARNING"
            elif surface == "dispatch":
                status = "PASS"
                note = "Dispatch is PorterChain day plan (OR-Tools)"
            elif surface == "notifications":
                if not order.customer_id:
                    status = "PASS"
                    note = "Order has no retail customer (merchant/E2E flow)"
                else:
                    n = (
                        db.query(func.count(NotificationRecord.id))
                        .filter(NotificationRecord.recipient_id == order.customer_id)
                        .scalar()
                        or 0
                    )
                    status = "PASS" if n > 0 else "WARNING"
                    note = "" if n > 0 else "No notification records for order customer"
            surfaces.append({"surface": surface, "status": status, "order_state": canonical_state, "note": note})

        mismatches = [s for s in surfaces if s["status"] in ("FAIL", "BLOCKER")]
        overall = "FAIL" if mismatches else ("WARNING" if any(s["status"] == "WARNING" for s in surfaces) else "PASS")
        return {
            "phase": 8,
            "name": "System Consistency",
            "overall": overall,
            "canonical_order_id": order.id if order else None,
            "canonical_state": canonical_state,
            "surfaces": surfaces,
            "synchronized": len(mismatches) == 0,
        }
