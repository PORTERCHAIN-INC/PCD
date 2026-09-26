"""Merchant booking flow — orchestrates Booking Engine + Pricing Engine (masterrule §3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.compliance_metadata import build_compliance_metadata
from porterchain_api.booking_engine.site_access import (
    dropoff_address_fields,
    enrich_dropoff,
    extract_site_access_notes,
)
from porterchain_api.config import Settings
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.domain.states import BookingDraftState
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError, MerchantSyncService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.template_service import MerchantTemplateService
from porterchain_api.merchant_models import MerchantBookingTemplate, MerchantRecipient
from porterchain_api.booking_models import Order
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput, CreateBookingDraftRequest, UpdateBookingDraftRequest
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest, RouteImportPackageInput


class MerchantBookingFlowService:
    def __init__(self) -> None:
        self._booking = MerchantBookingService()
        self._drafts = BookingDraftService()
        self._templates = MerchantTemplateService()
        self._profile = MerchantProfileService()
        self._sync = MerchantSyncService()

    @staticmethod
    def _aware(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    def _assert_quote_fresh(self, draft, settings: Settings) -> None:
        now = datetime.now(UTC)
        expires = self._aware(getattr(draft, "expires_at", None))
        if expires is not None and now > expires:
            raise ValueError("quote_expired")
        quoted = self._aware(getattr(draft, "updated_at", None)) or self._aware(
            getattr(draft, "created_at", None)
        )
        ttl = timedelta(minutes=max(1, int(settings.quote_ttl_minutes or 30)))
        if quoted is not None and now - quoted > ttl:
            raise ValueError("quote_expired")

    def merchant_session_id(self, ctx: MerchantContext) -> str:
        return f"merchant:{ctx.merchant.id}:{ctx.user.id}"

    def validate_addresses(
        self,
        pickup: AddressInput,
        dropoff: AddressInput,
        *,
        require_coordinates: bool = True,
    ) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        for label, addr in (("pickup", pickup), ("dropoff", dropoff)):
            if not addr.formatted or not addr.formatted.strip():
                errors.append({"field": label, "error": "address_required"})
            elif require_coordinates and (addr.lat is None or addr.lng is None):
                errors.append({"field": label, "error": "coordinates_required", "hint": "Select from autocomplete"})
        return errors

    def validate_recipient(self, db: Session, ctx: MerchantContext, recipient_id: str | None) -> MerchantRecipient | None:
        if not recipient_id:
            return None
        record = (
            db.query(MerchantRecipient)
            .filter(MerchantRecipient.id == recipient_id, MerchantRecipient.merchant_id == ctx.merchant.id)
            .first()
        )
        if not record:
            raise LookupError("recipient_not_found")
        return record

    def recommend_vehicle(
        self,
        ctx: MerchantContext,
        *,
        weight_kg: float | None = None,
        package_type: str | None = None,
    ) -> dict[str, Any]:
        from porterchain_api.merchant_engine.coverage import recommend_vehicle as coverage_recommend

        return coverage_recommend(ctx.merchant, weight_kg=weight_kg, package_type=package_type)

    def preview(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
    ) -> dict[str, Any]:
        address_errors = self.validate_addresses(body.pickup, body.dropoff)
        if address_errors:
            return {"valid": False, "address_errors": address_errors}

        try:
            from porterchain_api.merchant_engine.service_area import assert_ontario_booking
            from porterchain_api.merchant_engine.booking_service import (
                _assert_credit_headroom,
                assert_pickup_window,
            )
            from porterchain_api.merchant_engine.stop_cargo import cargo_rollup

            assert_ontario_booking(body)
            assert_pickup_window(body)
            _assert_credit_headroom(db, ctx)
        except BookingValidationError as exc:
            return {"valid": False, "error": exc.code, "message": exc.message}

        if body.recipient_id:
            self.validate_recipient(db, ctx, body.recipient_id)

        weight_kg, _dimensions = cargo_rollup(body)
        vehicle_hint = self.recommend_vehicle(
            ctx, weight_kg=weight_kg, package_type=body.package_type
        )
        vehicle_class = body.vehicle_class or vehicle_hint["recommended_vehicle"]

        pricing_request = self._booking.build_pricing_request(ctx, body, vehicle_class=vehicle_class)
        breakdown = get_pricing_service(db).calculate_merchant(pricing_request)
        amount_cents = breakdown.final_cents

        try:
            validated = self._sync.validate_booking(db, ctx.merchant, amount_cents=amount_cents)
            contract_pricing = bool(validated.contract_id)
            warnings = list(validated.warnings)
        except BookingValidationError as exc:
            return {
                "valid": False,
                "error": exc.code,
                "message": exc.message,
            }

        pricing = get_pricing_service(db)
        from porterchain_api.merchant_engine.quote_snapshot import sanitize_pricing_breakdown

        meta = breakdown.metadata if isinstance(breakdown.metadata, dict) else {}
        routing_source = meta.get("routing_source")
        if isinstance(routing_source, str):
            routing_source = routing_source.strip().lower() or None
        else:
            routing_source = None

        return {
            "valid": True,
            "amount_cents": amount_cents,
            "currency": "cad",
            "vehicle_class": vehicle_class,
            "vehicle_recommendation": vehicle_hint,
            "contract_pricing": contract_pricing,
            "contract_id": validated.contract_id,
            "payment_terms": validated.payment_terms,
            "warnings": warnings,
            "pricing_breakdown": sanitize_pricing_breakdown(pricing.to_api_breakdown(breakdown)),
            "distance_meters": meta.get("distance_meters"),
            "estimated_duration_minutes": meta.get("estimated_duration_minutes"),
            "routing_source": routing_source,
        }

    def save_draft(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
        *,
        current_step: str = "review",
    ) -> dict[str, Any]:
        preview = self.preview(db, settings, ctx, body)
        session_id = self.merchant_session_id(ctx)
        dropoff_payload = enrich_dropoff(body.dropoff.model_dump(), body.site_access_notes)
        create_body = CreateBookingDraftRequest(
            session_id=session_id,
            pickup=body.pickup,
            dropoff=AddressInput(**dropoff_payload),
            additional_stops=body.additional_stops,
            vehicle_class=body.vehicle_class,
            package_type=body.package_type,
            weight_kg=body.weight_kg,
            dimensions=body.dimensions,
            special_instructions=body.special_instructions,
            schedule_mode=body.schedule_mode,
            current_step=current_step,
        )
        draft = self._drafts.create_or_update_draft(db, settings, create_body)
        if body.site_access_notes:
            draft.dropoff = enrich_dropoff(dict(draft.dropoff or {}), body.site_access_notes)
        draft.amount_cents = preview.get("amount_cents") if preview.get("valid") else None
        draft.pricing_breakdown = {
            **(preview.get("pricing_breakdown") or {}),
            "_merchant": {
                "internal_reference": body.internal_reference,
                "purchase_order_number": body.purchase_order_number,
                "cost_centre": body.cost_centre,
                "recipient_id": body.recipient_id,
                "saved_pickup_id": body.saved_pickup_id,
                "template_id": body.template_id,
                "consignee_email": body.consignee_email,
                "scheduled_at": body.scheduled_at.isoformat() if body.scheduled_at else None,
                "site_access_notes": body.site_access_notes,
                "requires_liftgate": body.requires_liftgate,
                "otp_required": body.otp_required,
                "custodian_name": body.custodian_name,
                "specimen_id": body.specimen_id,
                "seal_number": body.seal_number,
                "requires_cold_chain": body.requires_cold_chain,
                "temperature_min_c": body.temperature_min_c,
                "temperature_max_c": body.temperature_max_c,
                "delivery_window_start": body.delivery_window_start.isoformat()
                if body.delivery_window_start
                else None,
                "delivery_window_end": body.delivery_window_end.isoformat()
                if body.delivery_window_end
                else None,
                "pickup_window_start": body.pickup_window_start.isoformat()
                if body.pickup_window_start
                else None,
                "pickup_window_end": body.pickup_window_end.isoformat()
                if body.pickup_window_end
                else None,
                "packages": [p.model_dump() for p in (body.packages or [])],
            },
        }
        draft.estimated_pickup = body.pickup_window_start or body.scheduled_at
        db.commit()
        db.refresh(draft)
        return {"draft_id": draft.id, "state": draft.state, "preview": preview}

    def get_active_draft(self, db: Session, ctx: MerchantContext) -> dict[str, Any] | None:
        session_id = self.merchant_session_id(ctx)
        draft = self._drafts.find_active_draft(db, session_id=session_id)
        if not draft:
            return None
        meta = (draft.pricing_breakdown or {}).get("_merchant", {})
        from porterchain_api.merchant_engine.quote_snapshot import sanitize_pricing_breakdown

        return {
            "draft_id": draft.id,
            "state": draft.state,
            "current_step": draft.current_step,
            "pickup": draft.pickup,
            "dropoff": draft.dropoff,
            "vehicle_class": draft.vehicle_class,
            "package_type": draft.package_type,
            "weight_kg": draft.weight_kg,
            "dimensions": draft.dimensions,
            "special_instructions": draft.special_instructions,
            "amount_cents": draft.amount_cents,
            "pricing_breakdown": sanitize_pricing_breakdown(draft.pricing_breakdown),
            "merchant_meta": meta,
            "expires_at": draft.expires_at.isoformat(),
        }

    def draft_to_request(self, draft, meta: dict[str, Any]) -> MerchantBookDeliveryRequest:
        scheduled_raw = meta.get("scheduled_at")
        scheduled_at = (
            datetime.fromisoformat(scheduled_raw.replace("Z", "+00:00"))
            if scheduled_raw
            else datetime.now(UTC)
        )
        window_start = meta.get("delivery_window_start")
        window_end = meta.get("delivery_window_end")
        ready_from = meta.get("pickup_window_start")
        pickup_by = meta.get("pickup_window_end")
        packages = [
            RouteImportPackageInput.model_validate(p)
            for p in (meta.get("packages") or [])
            if isinstance(p, dict)
        ]
        return MerchantBookDeliveryRequest(
            pickup=draft.pickup or {},
            dropoff=dropoff_address_fields(draft.dropoff),
            additional_stops=list(draft.additional_stops or []),
            vehicle_class=persist_vehicle_class(draft.vehicle_class),
            package_type=draft.package_type or "looseParcel",
            weight_kg=draft.weight_kg,
            dimensions=draft.dimensions,
            scheduled_at=scheduled_at,
            schedule_mode=draft.schedule_mode or "now",
            special_instructions=draft.special_instructions,
            site_access_notes=extract_site_access_notes(draft.dropoff) or meta.get("site_access_notes"),
            requires_liftgate=bool(meta.get("requires_liftgate")),
            otp_required=bool(meta.get("otp_required")),
            custodian_name=meta.get("custodian_name"),
            specimen_id=meta.get("specimen_id"),
            seal_number=meta.get("seal_number"),
            requires_cold_chain=bool(meta.get("requires_cold_chain")),
            temperature_min_c=meta.get("temperature_min_c"),
            temperature_max_c=meta.get("temperature_max_c"),
            delivery_window_start=(
                datetime.fromisoformat(str(window_start).replace("Z", "+00:00")) if window_start else None
            ),
            delivery_window_end=(
                datetime.fromisoformat(str(window_end).replace("Z", "+00:00")) if window_end else None
            ),
            pickup_window_start=(
                datetime.fromisoformat(str(ready_from).replace("Z", "+00:00")) if ready_from else None
            ),
            pickup_window_end=(
                datetime.fromisoformat(str(pickup_by).replace("Z", "+00:00")) if pickup_by else None
            ),
            packages=packages or None,
            internal_reference=meta.get("internal_reference"),
            purchase_order_number=meta.get("purchase_order_number"),
            cost_centre=meta.get("cost_centre"),
            recipient_id=meta.get("recipient_id"),
            consignee_email=meta.get("consignee_email"),
            saved_pickup_id=meta.get("saved_pickup_id"),
            template_id=meta.get("template_id"),
        )

    def confirm_draft(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        draft_id: str,
    ) -> Order:
        draft = self._drafts.get_by_id(db, draft_id)
        if not draft or draft.session_id != self.merchant_session_id(ctx):
            raise LookupError("draft_not_found")
        self._assert_quote_fresh(draft, settings)
        meta = (draft.pricing_breakdown or {}).get("_merchant", {})
        body = self.draft_to_request(draft, meta)
        preview = self.preview(db, settings, ctx, body)
        if not preview.get("valid"):
            raise ValueError(preview.get("error") or "preview_invalid")
        order = self._booking.create_shipment(
            db,
            settings,
            ctx,
            body,
            sandbox=bool(getattr(body, "is_sandbox", False)),
        )
        self._drafts.transition(
            db,
            draft,
            BookingDraftState.CANCELLED,
            "Merchant Booking Confirmed",
            actor_type="merchant",
            actor_id=ctx.user.id,
            payload={"order_id": order.id, "converted": True},
        )
        db.commit()
        return order

    def confirm_booking(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        body: MerchantBookDeliveryRequest,
        *,
        draft_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if draft_id:
            draft = self._drafts.get_by_id(db, draft_id)
            if draft and draft.session_id == self.merchant_session_id(ctx):
                self._assert_quote_fresh(draft, settings)
        preview = self.preview(db, settings, ctx, body)
        if not preview.get("valid"):
            raise ValueError(preview.get("error") or "preview_invalid")
        if idempotency_key:
            existing = self._booking.find_by_idempotency_key(
                db,
                ctx,
                idempotency_key,
                is_sandbox=bool(getattr(body, "is_sandbox", False)),
            )
            if existing:
                return self._confirm_payload(settings, existing, preview)
        order = self._booking.create_shipment(
            db,
            settings,
            ctx,
            body,
            idempotency_key=idempotency_key,
            sandbox=bool(getattr(body, "is_sandbox", False)),
        )
        if draft_id:
            draft = self._drafts.get_by_id(db, draft_id)
            if draft and draft.session_id == self.merchant_session_id(ctx):
                self._drafts.transition(
                    db,
                    draft,
                    BookingDraftState.CANCELLED,
                    "Merchant Booking Confirmed",
                    actor_type="merchant",
                    actor_id=ctx.user.id,
                    payload={"order_id": order.id, "converted": True},
                )
                db.commit()
        return self._confirm_payload(settings, order, preview)

    @staticmethod
    def _confirm_payload(settings: Settings, order: Order, preview: dict[str, Any]) -> dict[str, Any]:
        from porterchain_api.domain.sandbox import order_is_sandbox
        from porterchain_api.merchant_engine.consignee_notify import consignee_email_from_order
        from porterchain_api.merchant_engine.tracking_service import public_track_url

        email = consignee_email_from_order(order)
        sandbox = order_is_sandbox(order)
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "amount_cents": order.amount_cents,
            "preview": preview,
            "is_sandbox": sandbox,
            "public_track_url": public_track_url(
                settings, order.tracking_number, is_sandbox=sandbox
            ),
            "consignee_email": email,
            "consignee_emailed": bool(email) and not sandbox,
        }

    @staticmethod
    def parcel_idempotency_key(batch_key: str | None, index: int) -> str | None:
        """One key per parcel from the batch key, so a retry books each parcel once (BH)."""
        key = (batch_key or "").strip()
        return f"{key}:{index}" if key else None

    def confirm_multi(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        pickup: AddressInput,
        parcels: list[MerchantBookDeliveryRequest],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for index, parcel in enumerate(parcels, start=1):
            body = parcel.model_copy(update={"pickup": pickup})
            parcel_key = self.parcel_idempotency_key(idempotency_key, index)
            parcel_sandbox = bool(getattr(body, "is_sandbox", False))
            try:
                if parcel_key:
                    existing = self._booking.find_by_idempotency_key(
                        db, ctx, parcel_key, is_sandbox=parcel_sandbox
                    )
                    if existing:
                        results.append(self._parcel_row(index, existing, replayed=True))
                        continue
                preview = self.preview(db, settings, ctx, body)
                if not preview.get("valid"):
                    errors.append({"parcel": index, "error": preview.get("error")})
                    continue
                try:
                    order = self._booking.create_shipment(
                        db,
                        settings,
                        ctx,
                        body,
                        idempotency_key=parcel_key,
                        sandbox=parcel_sandbox,
                    )
                except IntegrityError:
                    # A concurrent retry won the unique index — report its order.
                    db.rollback()
                    winner = (
                        self._booking.find_by_idempotency_key(
                            db, ctx, parcel_key, is_sandbox=parcel_sandbox
                        )
                        if parcel_key
                        else None
                    )
                    if not winner:
                        raise
                    results.append(self._parcel_row(index, winner, replayed=True))
                    continue
                results.append(self._parcel_row(index, order))
            except Exception as exc:  # noqa: BLE001
                errors.append({"parcel": index, "error": str(exc)})
        return {"orders": results, "errors": errors, "total_amount_cents": sum(r["amount_cents"] for r in results)}

    @staticmethod
    def _parcel_row(index: int, order: Order, *, replayed: bool = False) -> dict[str, Any]:
        return {
            "parcel": index,
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "amount_cents": order.amount_cents,
            "already_booked": replayed,
        }

    def list_templates(self, db: Session, ctx: MerchantContext) -> list[MerchantBookingTemplate]:
        return self._templates.list_templates(db, ctx)

    def save_template(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        name: str,
        payload: dict[str, Any],
        is_recurring: bool = False,
        recurrence_rule: str | None = None,
    ) -> MerchantBookingTemplate:
        return self._templates.create_template(
            db, ctx, name=name, payload=payload, is_recurring=is_recurring, recurrence_rule=recurrence_rule
        )

    def delete_template(self, db: Session, ctx: MerchantContext, template_id: str) -> None:
        self._templates.delete_template(db, ctx, template_id)

    def list_saved_addresses(self, db: Session, ctx: MerchantContext):
        return self._profile.list_saved_addresses(db, ctx)

    def list_recipients(self, db: Session, ctx: MerchantContext):
        return self._profile.list_recipients(db, ctx)
