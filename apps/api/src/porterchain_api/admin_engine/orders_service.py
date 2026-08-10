"""Admin order management — extends shared OrderPlatformService (masterrule §3)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Order
from porterchain_api.order_engine.filters import AdminOrderFilters, OrderFilters
from porterchain_api.order_engine.platform_service import OrderPlatformService
from porterchain_api.reporting.compliance_dossier import build_compliance_dossier_pdf

__all__ = ["AdminOrderFilters", "AdminOrdersService", "OrderFilters"]


class AdminOrdersService(OrderPlatformService):
    """Admin-scoped order platform — RBAC-gated overrides and bulk ops."""

    def audit_export(self, db: Session, order_id: str) -> dict | None:
        """§8.1.4 — chain-of-custody + timeline export for compliance review."""
        order = self.get_order(db, order_id)
        if not order:
            return None
        events = self.order_timeline(db, order_id)
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "merchant_id": order.merchant_id,
            "compliance_metadata": order.compliance_metadata,
            "exported_at": datetime.now(UTC).isoformat(),
            "events": [
                {
                    "event_type": e.event_type,
                    "from_state": e.from_state,
                    "to_state": e.to_state,
                    "occurred_at": e.occurred_at.isoformat(),
                    "actor_type": e.actor_type,
                    "actor_id": e.actor_id,
                    "payload": e.payload,
                }
                for e in events
            ],
        }

    def compliance_dossier_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        """§8.1.13 — printable compliance dossier for medical / food orders."""
        order = self.get_order(db, order_id)
        if not order:
            return None
        events = self.order_timeline(db, order_id)
        merchant = None
        driver = None
        if order.merchant_id:
            from porterchain_api.merchant_models import Merchant

            merchant = db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
        if order.assigned_driver_id:
            from porterchain_api.admin_models import Driver

            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
        pdf = build_compliance_dossier_pdf(order, events, merchant=merchant, driver=driver)
        filename = f"compliance-{order.order_number}.pdf"
        return pdf, filename

    def label_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        from porterchain_api.reporting.order_documents import build_label_pdf

        order = self.get_order(db, order_id)
        if not order:
            return None
        return build_label_pdf(order), f"label-{order.tracking_number}.pdf"

    def manifest_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        from porterchain_api.reporting.order_documents import build_manifest_pdf

        order = self.get_order(db, order_id)
        if not order:
            return None
        driver_name = None
        if order.assigned_driver_id:
            from porterchain_api.admin_models import Driver

            driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
            driver_name = driver.full_name if driver else None
        return build_manifest_pdf(order, driver_name=driver_name), f"manifest-{order.tracking_number}.pdf"

    def invoice_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        from porterchain_api.booking_models import Invoice
        from porterchain_api.reporting.order_documents import build_invoice_pdf

        order = self.get_order(db, order_id)
        if not order:
            return None
        invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
        if not invoice:
            return None
        merchant_name = None
        customer_email = None
        if order.merchant_id:
            from porterchain_api.merchant_models import Merchant

            m = db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
            merchant_name = m.company_name if m else None
        if order.customer_id:
            from porterchain_api.models import Customer

            c = db.query(Customer).filter(Customer.id == order.customer_id).first()
            customer_email = c.email if c else None
        pdf = build_invoice_pdf(
            order,
            invoice_number=invoice.invoice_number,
            amount_cents=int(invoice.amount_cents or 0),
            currency=invoice.currency or "cad",
            receipt_number=invoice.receipt_number,
            merchant_name=merchant_name,
            customer_email=customer_email,
        )
        return pdf, f"invoice-{invoice.invoice_number}.pdf"

    def force_transition(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        to_state: str,
    ) -> Order:
        order = self.get_order(db, order_id)
        if not order:
            raise LookupError("order_not_found")
        return transition_order_state(
            db,
            order,
            OrderState(to_state),
            event_type="order.admin_override",
            actor_type="admin",
            actor_id=ctx.user.id,
            payload={"forced": True},
        )

    def bulk_action(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_ids: list[str],
        action: str,
        *,
        driver_id: str | None = None,
    ) -> list[dict[str, str]]:
        from porterchain_api.admin_engine.operations_service import AdminOperationsService

        ops = AdminOperationsService()
        results: list[dict[str, str]] = []
        for oid in order_ids:
            try:
                if action == "assign" and driver_id:
                    ops.assign_driver(db, settings, ctx, oid, driver_id)
                    results.append({"order_id": oid, "status": "assigned"})
                elif action == "cancel":
                    self.force_transition(db, ctx, oid, OrderState.CANCELLED.value)
                    results.append({"order_id": oid, "status": "cancelled"})
                else:
                    results.append({"order_id": oid, "status": "unsupported"})
            except Exception as exc:
                results.append({"order_id": oid, "status": f"error:{exc}"})
        return results
