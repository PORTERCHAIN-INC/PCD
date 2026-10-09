"""Merchant orders — merchant-scoped wrapper over OrderPlatformService (masterrule §3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.order_engine import (
    ASSIGNED_STATES,
    DONE_STATES,
    FAILED_STATES,
    IN_FLIGHT,
    PICKED_UP_STATES,
    RETURNED_STATES,
    WAITING_DISPATCH,
    OrderFilters,
)
from porterchain_api.order_engine.platform_service import OrderPlatformService
from porterchain_api.config import Settings
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.orders_board import (
    bulk_action as board_bulk_action,
    dashboard_payload,
    sanitize_merchant_detail,
    tracking_timeline,
)
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.booking_models import Order


@dataclass
class MerchantOrderFilters:
    state: str | None = None
    payment_status: str | None = None
    invoice_status: str | None = None
    driver_id: str | None = None
    priority: str | None = None
    service_type: str | None = None
    city: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    search: str | None = None
    include_sandbox: bool = False
    sandbox_only: bool = False
    limit: int = 50
    offset: int = 0


class MerchantOrdersService:
    def __init__(self) -> None:
        from porterchain_api.booking_engine.repositories.order_repository import OrderRepository

        self._orders = OrderPlatformService()
        self._booking = MerchantBookingService()
        self._order_repo = OrderRepository()

    def _require_owned(self, db: Session, ctx: MerchantContext, order_id: str) -> Order:
        order = self._order_repo.get_for_merchant(db, ctx.merchant.id, order_id)
        if not order:
            raise LookupError("order_not_found")
        return order

    def _to_order_filters(self, ctx: MerchantContext, filters: MerchantOrderFilters) -> OrderFilters:
        return OrderFilters(
            state=filters.state,
            payment_status=filters.payment_status,
            invoice_status=filters.invoice_status,
            merchant_id=ctx.merchant.id,
            driver_id=filters.driver_id,
            priority=filters.priority,
            service_type=filters.service_type,
            city=filters.city,
            date_from=filters.date_from,
            date_to=filters.date_to,
            amount_min_cents=filters.amount_min_cents,
            amount_max_cents=filters.amount_max_cents,
            search=filters.search,
            include_sandbox=filters.include_sandbox,
            sandbox_only=filters.sandbox_only,
            limit=filters.limit,
            offset=filters.offset,
        )

    def list_enriched(self, db: Session, ctx: MerchantContext, filters: MerchantOrderFilters) -> list[dict[str, Any]]:
        return self.list_page(db, ctx, filters)["items"]

    def list_page(self, db: Session, ctx: MerchantContext, filters: MerchantOrderFilters) -> dict[str, Any]:
        return self._orders.list_page(db, self._to_order_filters(ctx, filters))

    def orders_dashboard(self, db: Session, ctx: MerchantContext) -> dict[str, Any]:
        from porterchain_api.support_engine.claims_service import AdminClaimsService
        from porterchain_api.support_engine.support_service import AdminSupportService

        merchant_id = ctx.merchant.id
        return dashboard_payload(
            db,
            merchant_id,
            open_claims=AdminClaimsService().open_count_for_merchant(db, merchant_id),
            open_tickets=AdminSupportService().open_count_for_merchant(db, merchant_id),
            avg_delivery_hours=self._orders._avg_duration_hours(db, "order.picked_up", "order.delivered"),
            avg_pickup_hours=self._orders._avg_duration_hours(db, "order.driver_assigned", "order.picked_up"),
            in_flight=IN_FLIGHT,
            waiting_dispatch=WAITING_DISPATCH,
            assigned=ASSIGNED_STATES,
            picked_up=PICKED_UP_STATES,
            failed=FAILED_STATES,
            returned=RETURNED_STATES,
            done_states=DONE_STATES,
        )

    def get_detail_360(self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str) -> dict[str, Any]:
        self._require_owned(db, ctx, order_id)
        detail = self._orders.get_detail_360(db, settings, order_id)
        if not detail:
            raise LookupError("order_not_found")
        return self._sanitize_merchant_detail(db, ctx, order_id, detail)

    def amend_parcels(
        self,
        db: Session,
        ctx: MerchantContext,
        order_id: str,
        stops: list[dict[str, Any]],
        *,
        vehicle_class: str | None = None,
        settings: Settings | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.merchant_engine.parcel_amend_service import ParcelAmendService

        order = self._require_owned(db, ctx, order_id)
        return ParcelAmendService().apply(
            db,
            order,
            stops,
            ctx.merchant,
            actor_type="merchant",
            actor_id=ctx.user.id,
            vehicle_class=vehicle_class,
            settings=settings,
        )

    def order_tracking(self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str) -> dict[str, Any]:
        from porterchain_api.merchant_engine.tracking_service import MerchantTrackingService

        return MerchantTrackingService().live_tracking(db, settings, ctx, order_id)

    def email_consignee_tracking(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        order_id: str,
        email: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.merchant_engine.consignee_notify import (
            consignee_email_from_order,
            send_consignee_tracking,
            store_consignee_email,
        )

        order = self._require_owned(db, ctx, order_id)
        target = (email or "").strip() or consignee_email_from_order(order)
        if not target:
            raise ValueError("consignee_email_required")
        if "@" not in target:
            raise ValueError("consignee_email_invalid")
        store_consignee_email(order, target)
        result = send_consignee_tracking(
            db, settings, order, target, merchant_name=ctx.merchant.company_name
        )
        db.commit()
        return result

    def bulk_action(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        order_ids: list[str],
        action: str,
    ) -> list[dict[str, str | bool]]:
        return board_bulk_action(self, db, settings, ctx, order_ids, action)

    def _sanitize_merchant_detail(
        self,
        db: Session,
        ctx: MerchantContext,
        order_id: str,
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        return sanitize_merchant_detail(db, ctx, self._require_owned(db, ctx, order_id), order_id, detail)

    # Legacy helpers (programmatic API + simple consumers)
    def list_orders(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        state: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        q = db.query(Order).filter(Order.merchant_id == ctx.merchant.id)
        if state:
            q = q.filter(Order.state == state)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (Order.tracking_number.ilike(pattern))
                | (Order.order_number.ilike(pattern))
                | (Order.internal_reference.ilike(pattern))
                | (Order.purchase_order_number.ilike(pattern))
                | (Order.cost_centre.ilike(pattern))
            )
        return q.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    def get_order(self, db: Session, ctx: MerchantContext, order_id: str) -> Order | None:
        return self._order_repo.get_for_merchant(db, ctx.merchant.id, order_id)

    def cancel_owned(self, db: Session, ctx: MerchantContext, order_id: str, settings: Settings):
        return self._booking.cancel_order(db, ctx, self._require_owned(db, ctx, order_id), settings)

    def duplicate_owned(self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str):
        return self._booking.duplicate_order(db, settings, ctx, self._require_owned(db, ctx, order_id))

    def create_return_owned(
        self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str
    ) -> dict[str, Any]:
        """Return pickup: customer address -> merchant, priced by the same engine."""
        from porterchain_api.merchant_engine import return_service as returns
        from porterchain_api.merchant_engine.booking_validation import BookingValidationError

        original = self._require_owned(db, ctx, order_id)
        returns.assert_can_open_return(db, original)
        key = f"portal-return:{original.id}:{len(returns.open_returns(original)) + 1}"
        try:
            order = returns.create_return_order(
                db,
                settings,
                ctx,
                original,
                source=returns.SOURCE_PORTAL,
                idempotency_key=key,
                booking=self._booking,
            )
        except BookingValidationError as exc:
            raise ValueError(exc.code) from exc
        db.commit()
        return returns.return_summary(order)

    def returns_owned(self, db: Session, ctx: MerchantContext, order_id: str) -> list[dict[str, Any]]:
        from porterchain_api.merchant_engine import return_service as returns

        return returns.returns_for(db, self._require_owned(db, ctx, order_id))

    def get_tracking_timeline(self, db: Session, ctx: MerchantContext, order_id: str) -> list[dict]:
        if not self.get_order(db, ctx, order_id):
            raise LookupError("order_not_found")
        return tracking_timeline(db, order_id)

    def get_by_tracking(self, db: Session, ctx: MerchantContext, tracking_number: str) -> Order | None:
        return self._order_repo.get_by_tracking_for_merchant(db, ctx.merchant.id, tracking_number)

    # ------------------------------------------------------------------ #
    # Proof of delivery downloads (BR)
    # ------------------------------------------------------------------ #

    def _pod_gallery(
        self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str
    ) -> tuple[Order, dict[str, Any]]:
        """The same POD the portal shows, read through the same scoped path.

        Going through ``get_detail_360`` rather than Fleetbase directly means a
        download can never contain evidence the portal would have withheld.
        """
        order = self._require_owned(db, ctx, order_id)
        detail = self.get_detail_360(db, settings, ctx, order_id)
        gallery = detail.get("proof_of_delivery")
        return order, gallery if isinstance(gallery, dict) else {}

    @staticmethod
    def _pod_reference(order: Order) -> str | None:
        return order.tracking_number or order.order_number

    def pod_bundle(
        self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str
    ) -> tuple[bytes, str]:
        """Every proof for one shipment as a ZIP."""
        from porterchain_api.reporting.pod_export import build_bundle

        order, gallery = self._pod_gallery(db, settings, ctx, order_id)
        return build_bundle(self._pod_reference(order), gallery)

    def pod_artifact(
        self, db: Session, settings: Settings, ctx: MerchantContext, order_id: str, slug: str
    ) -> tuple[bytes, str, str]:
        """One photo or the signature: ``(payload, media_type, filename)``."""
        from porterchain_api.reporting.pod_export import (
            artifact_bytes,
            artifact_filename,
            find_artifact,
        )

        order, gallery = self._pod_gallery(db, settings, ctx, order_id)
        artifact = find_artifact(gallery, slug)
        payload, media_type, extension = artifact_bytes(artifact)
        return payload, media_type, artifact_filename(self._pod_reference(order), artifact, extension)

    def compliance_dossier_pdf(
        self, db: Session, ctx: MerchantContext, order_id: str
    ) -> tuple[bytes, str]:
        """§8.1.13 — merchant-scoped compliance PDF dossier."""
        from porterchain_api.platform.driver_reads import get_driver
        from porterchain_api.reporting.compliance_dossier import build_compliance_dossier_pdf

        order = self._require_owned(db, ctx, order_id)
        events = self._orders.order_timeline(db, order_id)
        driver = get_driver(db, order.assigned_driver_id)
        pdf = build_compliance_dossier_pdf(order, events, merchant=ctx.merchant, driver=driver)
        return pdf, f"shipment-{order.order_number}.pdf"

    def print_preview_pdf(self, db: Session, ctx: MerchantContext, order_id: str) -> tuple[bytes, str]:
        from porterchain_api.reporting.order_documents import build_print_preview_pdf

        order = self._require_owned(db, ctx, order_id)
        return build_print_preview_pdf(order), f"print-preview-{order.tracking_number}.pdf"

    def labels_pdf(self, db: Session, ctx: MerchantContext, order_id: str) -> tuple[bytes, str]:
        from porterchain_api.reporting.label_service import LabelService, PackagesRequired

        order = self._require_owned(db, ctx, order_id)
        try:
            pdf, filename = LabelService().build_order_labels_pdf(
                db, order, merchant_name=ctx.merchant.company_name
            )
        except PackagesRequired as exc:
            raise LookupError(str(exc)) from exc
        db.commit()
        return pdf, filename

    def labels_bulk_pdf(
        self, db: Session, ctx: MerchantContext, order_ids: list[str]
    ) -> tuple[bytes, str]:
        from porterchain_api.reporting.label_service import LabelService, PackagesRequired

        cleaned = [oid.strip() for oid in order_ids if oid and oid.strip()]
        if not cleaned:
            raise ValueError("orders_required")
        if len(cleaned) > 100:
            raise ValueError("labels_bulk_too_many_orders")
        orders: list[Order] = []
        for oid in cleaned:
            orders.append(self._require_owned(db, ctx, oid))
        try:
            pdf, filename = LabelService().build_bulk_labels_pdf(
                db,
                orders,
                merchant_names={ctx.merchant.id: ctx.merchant.company_name},
            )
        except PackagesRequired as exc:
            raise LookupError(str(exc)) from exc
        except ValueError:
            raise
        db.commit()
        return pdf, filename

    def pickup_manifest_pdf(
        self, db: Session, ctx: MerchantContext, order_ids: list[str]
    ) -> tuple[bytes, str]:
        from porterchain_api.merchant_engine.package_service import PackageService
        from porterchain_api.reporting.label_service import LabelService

        cleaned = [oid.strip() for oid in order_ids if oid and oid.strip()]
        if not cleaned:
            raise ValueError("orders_required")
        if len(cleaned) > 100:
            raise ValueError("too_many_orders")
        pkg = PackageService()
        orders: list[Order] = []
        counts: dict[str, int] = {}
        for oid in cleaned:
            order = self._require_owned(db, ctx, oid)
            rows = pkg.ensure_for_order(db, order)
            orders.append(order)
            counts[order.id] = len(rows)
        db.commit()
        return LabelService().build_pickup_manifest_pdf(orders, package_counts=counts)

    def pickup_list_pdf(
        self, db: Session, ctx: MerchantContext, order_ids: list[str]
    ) -> tuple[bytes, str]:
        from porterchain_api.reporting.order_documents import build_pickup_list_pdf

        cleaned = [oid.strip() for oid in order_ids if oid and oid.strip()]
        if not cleaned:
            raise ValueError("orders_required")
        if len(cleaned) > 20:
            raise ValueError("too_many_orders")
        orders: list[Order] = []
        for oid in cleaned:
            orders.append(self._require_owned(db, ctx, oid))
        return (
            build_pickup_list_pdf(orders, merchant_name=ctx.merchant.company_name),
            "pickup-list.pdf",
        )


_PRINT_ERRORS = {
    "order_not_found": "That order was not found.",
    "orders_required": "Select at least one order to print.",
    "too_many_orders": "Print up to 20 orders at a time.",
    "labels_bulk_too_many_orders": "Print labels for up to 100 orders at a time.",
    "labels_bulk_too_many_pages": "Bulk labels are limited to 500 pages.",
    "packages_required": "Add packages before printing labels.",
}


def print_error_message(code: str) -> str:
    return _PRINT_ERRORS.get(code, _PRINT_ERRORS["order_not_found"])
