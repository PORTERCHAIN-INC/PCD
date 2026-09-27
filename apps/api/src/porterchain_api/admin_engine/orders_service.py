"""Admin order management — extends shared OrderPlatformService (masterrule §3)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.booking_models import Order
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

    # ------------------------------------------------------------------ #
    # Proof of delivery downloads (BR)
    # ------------------------------------------------------------------ #

    def _pod_gallery(self, db: Session, settings: Settings, order_id: str) -> tuple[Order, dict]:
        from porterchain_api.reporting.pod_export import PodUnavailable

        order = self.get_order(db, order_id)
        if not order:
            raise PodUnavailable("order_not_found")
        detail = self.get_detail_360(db, settings, order_id) or {}
        gallery = detail.get("proof_of_delivery")
        return order, gallery if isinstance(gallery, dict) else {}

    def pod_bundle(self, db: Session, settings: Settings, order_id: str) -> tuple[bytes, str]:
        """Every proof for one shipment as a ZIP — the evidence a claim needs."""
        from porterchain_api.reporting.pod_export import build_bundle

        order, gallery = self._pod_gallery(db, settings, order_id)
        return build_bundle(order.tracking_number or order.order_number, gallery)

    def pod_artifact(
        self, db: Session, settings: Settings, order_id: str, slug: str
    ) -> tuple[bytes, str, str]:
        """One photo or the signature: ``(payload, media_type, filename)``."""
        from porterchain_api.reporting.pod_export import (
            artifact_bytes,
            artifact_filename,
            find_artifact,
        )

        order, gallery = self._pod_gallery(db, settings, order_id)
        artifact = find_artifact(gallery, slug)
        payload, media_type, extension = artifact_bytes(artifact)
        reference = order.tracking_number or order.order_number
        return payload, media_type, artifact_filename(reference, artifact, extension)

    def compliance_dossier_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        """§8.1.13 — printable compliance dossier for medical / food orders."""
        order = self.get_order(db, order_id)
        if not order:
            return None
        events = self.order_timeline(db, order_id)
        merchant = None
        driver = None
        if order.merchant_id:
            from porterchain_api.merchant_engine.lookups import get_merchant

            merchant = get_merchant(db, order.merchant_id)
        if order.assigned_driver_id:
            from porterchain_api.admin_engine.driver_lookups import get_driver

            driver = get_driver(db, order.assigned_driver_id)
        pdf = build_compliance_dossier_pdf(order, events, merchant=merchant, driver=driver)
        filename = f"shipment-{order.order_number}.pdf"
        return pdf, filename

    def label_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        """Deprecated — use labels_pdf (4×6 thermal)."""
        return self.labels_pdf(db, order_id)

    def labels_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        from porterchain_api.reporting.label_service import LabelService, PackagesRequired

        order = self.get_order(db, order_id)
        if not order:
            return None
        merchant_name = None
        if order.merchant_id:
            from porterchain_api.merchant_engine.lookups import company_name

            merchant_name = company_name(db, order.merchant_id)
        try:
            pdf, filename = LabelService().build_order_labels_pdf(
                db, order, merchant_name=merchant_name
            )
        except PackagesRequired:
            return None
        db.commit()
        return pdf, filename

    def labels_bulk_pdf(self, db: Session, order_ids: list[str]) -> tuple[bytes, str] | None:
        from porterchain_api.merchant_engine.lookups import company_name
        from porterchain_api.reporting.label_service import LabelService, PackagesRequired

        cleaned = [oid.strip() for oid in order_ids if oid and oid.strip()]
        if not cleaned or len(cleaned) > 100:
            return None
        orders = []
        names: dict[str, str] = {}
        for oid in cleaned:
            order = self.get_order(db, oid)
            if not order:
                continue
            orders.append(order)
            if order.merchant_id and order.merchant_id not in names:
                name = company_name(db, order.merchant_id)
                if name:
                    names[order.merchant_id] = name
        if not orders:
            return None
        try:
            pdf, filename = LabelService().build_bulk_labels_pdf(
                db, orders, merchant_names=names
            )
        except (PackagesRequired, ValueError):
            return None
        db.commit()
        return pdf, filename

    def pickup_manifest_pdf(self, db: Session, order_ids: list[str]) -> tuple[bytes, str] | None:
        from porterchain_api.merchant_engine.package_service import PackageService
        from porterchain_api.reporting.label_service import LabelService

        cleaned = [oid.strip() for oid in order_ids if oid and oid.strip()]
        if not cleaned:
            return None
        pkg = PackageService()
        orders = []
        counts: dict[str, int] = {}
        for oid in cleaned:
            order = self.get_order(db, oid)
            if not order:
                continue
            rows = pkg.ensure_for_order(db, order)
            orders.append(order)
            counts[order.id] = len(rows)
        if not orders:
            return None
        db.commit()
        return LabelService().build_pickup_manifest_pdf(orders, package_counts=counts)

    def manifest_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        from porterchain_api.reporting.order_documents import build_manifest_pdf

        order = self.get_order(db, order_id)
        if not order:
            return None
        driver_name = None
        if order.assigned_driver_id:
            from porterchain_api.admin_engine.driver_lookups import get_driver

            driver = get_driver(db, order.assigned_driver_id)
            driver_name = driver.full_name if driver else None
        return build_manifest_pdf(order, driver_name=driver_name), f"manifest-{order.tracking_number}.pdf"

    def invoice_pdf(self, db: Session, order_id: str) -> tuple[bytes, str] | None:
        from porterchain_api.booking_models import Invoice
        from porterchain_api.reporting.order_documents import pdf_for_invoice_record

        order = self.get_order(db, order_id)
        if not order:
            return None
        invoice = db.query(Invoice).filter(Invoice.order_id == order_id).first()
        if not invoice:
            return None
        return pdf_for_invoice_record(db, invoice)

    def amend_parcels(
        self,
        db: Session,
        ctx: AdminContext,
        order_id: str,
        stops: list[dict],
        *,
        vehicle_class: str | None = None,
        settings: Settings | None = None,
    ) -> dict:
        from porterchain_api.merchant_engine.lookups import get_merchant
        from porterchain_api.merchant_engine.parcel_amend_service import ParcelAmendService

        order = self.get_order(db, order_id)
        if not order:
            raise LookupError("order_not_found")
        if not order.merchant_id:
            raise ValueError("order_has_no_merchant")
        merchant = get_merchant(db, order.merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return ParcelAmendService().apply(
            db,
            order,
            stops,
            merchant,
            actor_type="admin",
            actor_id=ctx.user.id,
            vehicle_class=vehicle_class,
            settings=settings,
        )

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
        target = OrderState(to_state)
        # Only CANCELLED fans out to Fleetbase via ORDER_CANCELLED subscribers.
        event_type = (
            "order.cancelled" if target == OrderState.CANCELLED else "order.admin_override"
        )
        return transition_order_state(
            db,
            order,
            target,
            event_type=event_type,
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

    def timeline_payload(self, db: Session, order_id: str) -> list[dict]:
        return [
            {
                "event_type": e.event_type,
                "from_state": e.from_state,
                "to_state": e.to_state,
                "occurred_at": e.occurred_at.isoformat(),
                "payload": e.payload,
            }
            for e in self.order_timeline(db, order_id)
        ]

    def require_detail_360(self, db: Session, settings: Settings, order_id: str) -> dict:
        detail = self.get_detail_360(db, settings, order_id)
        if not detail:
            raise LookupError("order_not_found")
        return detail

    def require_tracking(self, db: Session, settings: Settings, order_id: str) -> dict:
        tracking = self.order_tracking(db, settings, order_id)
        if not tracking:
            raise LookupError("order_not_found")
        return tracking

    def require_audit_export(self, db: Session, order_id: str) -> dict:
        payload = self.audit_export(db, order_id)
        if not payload:
            raise LookupError("order_not_found")
        return payload

    def require_pdf(self, result: tuple | None, missing: str = "order_not_found") -> tuple:
        if not result:
            raise LookupError(missing)
        return result

    def labels_bulk_from_body(self, db: Session, body: dict) -> tuple[bytes, str]:
        order_ids = body.get("order_ids") if isinstance(body, dict) else None
        if not isinstance(order_ids, list):
            raise ValueError("order_ids_required")
        return self.require_pdf(self.labels_bulk_pdf(db, order_ids))

    def create_built(self, db: Session, settings: Settings, ctx: AdminContext, body) -> dict:
        from porterchain_api.admin_engine.order_builder_service import OrderBuilderService

        return OrderBuilderService().create(db, settings, ctx, body)

    def bulk_results(self, db: Session, settings: Settings, ctx: AdminContext, body) -> dict:
        return {
            "results": self.bulk_action(
                db, settings, ctx, body.order_ids, body.action, driver_id=body.driver_id
            )
        }

    def record_admin_temperature(
        self, db: Session, settings: Settings, ctx: AdminContext, order_id: str, celsius: float
    ) -> dict:
        from porterchain_api.booking_engine.medical_compliance import MedicalComplianceService

        return MedicalComplianceService().record_temperature(
            db, settings, order_id, celsius=celsius, actor_type="admin", actor_id=ctx.user.id
        )

    def manual_invoice_payload(self, db: Session, order_id: str) -> dict:
        from porterchain_api.booking_engine.invoice_service import InvoiceService

        invoice = InvoiceService().manual_invoice(db, order_id, commit=True)
        return {
            "order_id": order_id,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "receipt_number": invoice.receipt_number,
            "amount_cents": invoice.amount_cents,
        }

    def resend_receipt_committed(self, db: Session, order_id: str) -> dict:
        from porterchain_api.booking_engine.invoice_service import InvoiceService

        return InvoiceService().resend_receipt(db, order_id, commit=True)

    def assist(self, db: Session, settings: Settings, order_id: str) -> dict:
        from porterchain_api.admin_engine.order_assist_service import OrderAssistService

        return OrderAssistService().assist(db, settings, order_id)

    def assist_decide_from_body(
        self, db: Session, settings: Settings, ctx: AdminContext, order_id: str, body: dict
    ) -> dict:
        from porterchain_api.admin_engine.order_assist_service import OrderAssistService

        proposal_id = str(body.get("proposal_id") or "")
        decision = str(body.get("decision") or "")
        payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
        if not proposal_id or not decision:
            raise ValueError("proposal_id_and_decision_required")
        return OrderAssistService().decide(
            db, settings, ctx, order_id, proposal_id=proposal_id, decision=decision, payload=payload
        )

    def run_playbook_from_body(
        self,
        db: Session,
        settings: Settings,
        ctx: AdminContext,
        order_id: str,
        playbook_id: str,
        body: dict,
    ) -> dict:
        from porterchain_api.admin_engine.order_assist_service import OrderAssistService

        confirm = bool(body.get("confirm"))
        note = body.get("note") if isinstance(body.get("note"), str) else None
        return OrderAssistService().run_playbook(
            db, settings, ctx, order_id, playbook_id, confirm=confirm, note=note
        )

    def compliance_dossier_required(self, db: Session, order_id: str) -> tuple[bytes, str]:
        return self.require_pdf(self.compliance_dossier_pdf(db, order_id), "That order was not found.")

    def labels_pdf_required(self, db: Session, order_id: str) -> tuple[bytes, str]:
        return self.require_pdf(self.labels_pdf(db, order_id))

    def manifest_pdf_required(self, db: Session, order_id: str) -> tuple[bytes, str]:
        return self.require_pdf(self.manifest_pdf(db, order_id))

    def invoice_pdf_required(self, db: Session, order_id: str) -> tuple[bytes, str]:
        return self.require_pdf(self.invoice_pdf(db, order_id), "invoice_not_found")

    def pickup_manifest_required(self, db: Session, ids: list[str]) -> tuple[bytes, str]:
        return self.require_pdf(self.pickup_manifest_pdf(db, ids))
