"""Merchant booking flow — orchestrates Booking Engine + Pricing Engine (masterrule §3)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_engine.booking_draft_service import BookingDraftService
from porterchain_api.booking_engine.site_access import (
    dropoff_address_fields,
    enrich_dropoff,
    extract_site_access_notes,
)
from porterchain_api.config import Settings
from porterchain_api.domain.states import BookingDraftState
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError, MerchantSyncService
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.template_service import MerchantTemplateService
from porterchain_api.merchant_models import MerchantBookingTemplate, MerchantRecipient
from porterchain_api.models import Order
from porterchain_api.pricing_engine import get_pricing_service
from porterchain_api.schemas import AddressInput, CreateBookingDraftRequest, UpdateBookingDraftRequest
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest
from porterchain_pricing.catalog import VEHICLE_MINIMUM_CENTS, WEIGHT_THRESHOLD_KG


class MerchantBookingFlowService:
    def __init__(self) -> None:
        self._booking = MerchantBookingService()
        self._drafts = BookingDraftService()
        self._templates = MerchantTemplateService()
        self._profile = MerchantProfileService()
        self._sync = MerchantSyncService()

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
        preferred = list(ctx.merchant.preferred_vehicles or [])
        candidates = list(VEHICLE_MINIMUM_CENTS.keys())
        recommended = preferred[0] if preferred else "cargoVan"

        if weight_kg:
            if weight_kg > 1000:
                recommended = "box20" if "box20" in candidates else "box16"
            elif weight_kg > WEIGHT_THRESHOLD_KG:
                recommended = "highRoof" if "highRoof" in candidates else "cargoVan"
            elif weight_kg > 50:
                recommended = "cargoVan"
            else:
                recommended = preferred[0] if preferred else "sedan"

        if package_type in ("ltlPallet", "ftlLoad"):
            recommended = "box20"
        elif package_type == "furniture":
            recommended = "highRoof"

        if preferred and recommended not in preferred:
            alternatives = [v for v in preferred if v in candidates]
            if alternatives:
                recommended = alternatives[0]

        return {
            "recommended_vehicle": recommended,
            "preferred_vehicles": preferred,
            "alternatives": [v for v in candidates if v != recommended][:3],
        }

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

        if body.recipient_id:
            self.validate_recipient(db, ctx, body.recipient_id)

        vehicle_hint = self.recommend_vehicle(
            ctx, weight_kg=body.weight_kg, package_type=body.package_type
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
            "pricing_breakdown": pricing.to_api_breakdown(breakdown),
            "distance_meters": breakdown.metadata.get("distance_meters"),
            "estimated_duration_minutes": breakdown.metadata.get("estimated_duration_minutes"),
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
                "scheduled_at": body.scheduled_at.isoformat() if body.scheduled_at else None,
                "site_access_notes": body.site_access_notes,
                "requires_liftgate": body.requires_liftgate,
            },
        }
        draft.estimated_pickup = body.scheduled_at
        db.commit()
        db.refresh(draft)
        return {"draft_id": draft.id, "state": draft.state, "preview": preview}

    def get_active_draft(self, db: Session, ctx: MerchantContext) -> dict[str, Any] | None:
        session_id = self.merchant_session_id(ctx)
        draft = self._drafts.find_active_draft(db, session_id=session_id)
        if not draft:
            return None
        meta = (draft.pricing_breakdown or {}).get("_merchant", {})
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
            "pricing_breakdown": draft.pricing_breakdown,
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
        return MerchantBookDeliveryRequest(
            pickup=AddressInput(**(draft.pickup or {})),
            dropoff=AddressInput(**dropoff_address_fields(draft.dropoff)),
            additional_stops=[AddressInput(**s) for s in (draft.additional_stops or [])],
            vehicle_class=draft.vehicle_class or "cargoVan",
            package_type=draft.package_type or "looseParcel",
            weight_kg=draft.weight_kg,
            dimensions=draft.dimensions,
            scheduled_at=scheduled_at,
            schedule_mode=draft.schedule_mode or "now",
            special_instructions=draft.special_instructions,
            site_access_notes=extract_site_access_notes(draft.dropoff) or meta.get("site_access_notes"),
            requires_liftgate=bool(meta.get("requires_liftgate")),
            internal_reference=meta.get("internal_reference"),
            purchase_order_number=meta.get("purchase_order_number"),
            cost_centre=meta.get("cost_centre"),
            recipient_id=meta.get("recipient_id"),
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
        meta = (draft.pricing_breakdown or {}).get("_merchant", {})
        body = self.draft_to_request(draft, meta)
        preview = self.preview(db, settings, ctx, body)
        if not preview.get("valid"):
            raise ValueError(preview.get("error") or "preview_invalid")
        order = self._booking.create_shipment(db, settings, ctx, body)
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
    ) -> dict[str, Any]:
        preview = self.preview(db, settings, ctx, body)
        if not preview.get("valid"):
            raise ValueError(preview.get("error") or "preview_invalid")
        order = self._booking.create_shipment(db, settings, ctx, body)
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
        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "amount_cents": order.amount_cents,
            "preview": preview,
        }

    def confirm_multi(
        self,
        db: Session,
        settings: Settings,
        ctx: MerchantContext,
        pickup: AddressInput,
        parcels: list[MerchantBookDeliveryRequest],
    ) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for index, parcel in enumerate(parcels, start=1):
            body = parcel.model_copy(update={"pickup": pickup})
            try:
                preview = self.preview(db, settings, ctx, body)
                if not preview.get("valid"):
                    errors.append({"parcel": index, "error": preview.get("error")})
                    continue
                order = self._booking.create_shipment(db, settings, ctx, body)
                results.append(
                    {
                        "parcel": index,
                        "order_id": order.id,
                        "tracking_number": order.tracking_number,
                        "amount_cents": order.amount_cents,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"parcel": index, "error": str(exc)})
        return {"orders": results, "errors": errors, "total_amount_cents": sum(r["amount_cents"] for r in results)}

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
