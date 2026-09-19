"""Recurring standing orders — merchant registration + worker materialization (§8.1.11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.fleetbase_engine.merchant_sync_service import BookingValidationError
from porterchain_api.merchant_engine.booking_service import MerchantBookingService
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role
from porterchain_api.merchant_models import Merchant, MerchantBookingTemplate, MerchantUser, StandingOrder
from porterchain_api.schemas_merchant import MerchantBookDeliveryRequest

STANDING_ERROR_MESSAGES: dict[str, str] = {
    "template_not_found": (
        "The saved booking this schedule uses was deleted. Turn it off or save the booking again."
    ),
    "no_active_seat": "No active teammate can book this schedule. Reactivate a dispatcher or owner.",
    "merchant_not_active": "This company cannot place bookings until PorterChain reactivates it.",
    "standing_order_exists": "This saved booking already has an active schedule.",
    "invalid_recurrence_rule": "Choose daily, weekly, every two weeks, or monthly.",
    "standing_order_not_found": "That schedule was not found.",
    "run_failed": "This schedule could not run. Check the saved booking or turn the schedule off.",
}


def standing_error_message(code: str) -> str:
    return STANDING_ERROR_MESSAGES.get(code, code)


RECURRENCE_DELTAS: dict[str, timedelta] = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
    "monthly": timedelta(days=30),
}

SUPPORTED_RECURRENCE = frozenset(RECURRENCE_DELTAS)


def advance_next_run(current: datetime, rule: str) -> datetime:
    delta = RECURRENCE_DELTAS.get(rule, RECURRENCE_DELTAS["weekly"])
    return current + delta


class MerchantStandingOrderService:
    def __init__(self) -> None:
        self._booking = MerchantBookingService()

    def list_standing_orders(self, db: Session, ctx: MerchantContext) -> list[StandingOrder]:
        return (
            db.query(StandingOrder)
            .filter(StandingOrder.merchant_id == ctx.merchant.id)
            .order_by(StandingOrder.next_run_at.asc())
            .all()
        )

    def create_standing_order(
        self,
        db: Session,
        ctx: MerchantContext,
        *,
        booking_template_id: str,
        recurrence_rule: str = "weekly",
        next_run_at: datetime | None = None,
    ) -> StandingOrder:
        if recurrence_rule not in SUPPORTED_RECURRENCE:
            raise ValueError("invalid_recurrence_rule")
        if ctx.merchant.status != MerchantStatus.ACTIVE.value:
            raise ValueError("merchant_not_active")
        template = (
            db.query(MerchantBookingTemplate)
            .filter(
                MerchantBookingTemplate.id == booking_template_id,
                MerchantBookingTemplate.merchant_id == ctx.merchant.id,
            )
            .first()
        )
        if not template:
            raise LookupError("template_not_found")
        existing = (
            db.query(StandingOrder)
            .filter(
                StandingOrder.merchant_id == ctx.merchant.id,
                StandingOrder.booking_template_id == booking_template_id,
                StandingOrder.is_active.is_(True),
            )
            .first()
        )
        if existing:
            raise ValueError("standing_order_exists")
        run_at = next_run_at or datetime.now(UTC)
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=UTC)
        record = StandingOrder(
            merchant_id=ctx.merchant.id,
            booking_template_id=booking_template_id,
            recurrence_rule=recurrence_rule,
            next_run_at=run_at,
        )
        db.add(record)
        template.is_recurring = True
        template.recurrence_rule = recurrence_rule
        db.commit()
        db.refresh(record)
        return record

    def deactivate(self, db: Session, ctx: MerchantContext, standing_order_id: str) -> None:
        record = (
            db.query(StandingOrder)
            .filter(
                StandingOrder.id == standing_order_id,
                StandingOrder.merchant_id == ctx.merchant.id,
            )
            .first()
        )
        if not record:
            raise LookupError("standing_order_not_found")
        record.is_active = False
        db.commit()

    def resolve_context(self, db: Session, merchant_id: str) -> MerchantContext | None:
        merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
        if not merchant:
            return None
        user = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant_id, MerchantUser.is_active.is_(True))
            .order_by(MerchantUser.created_at.asc())
            .first()
        )
        if not user:
            return None
        return MerchantContext(
            merchant=merchant,
            user=user,
            role=parse_merchant_role(user.role),
        )

    def run_due_orders(self, db: Session, settings: Settings, *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        due = (
            db.query(StandingOrder)
            .filter(StandingOrder.is_active.is_(True), StandingOrder.next_run_at <= now)
            .order_by(StandingOrder.next_run_at.asc())
            .limit(50)
            .all()
        )
        created = 0
        failed = 0
        skipped = 0
        for standing in due:
            try:
                order_id = self._materialize_one(db, settings, standing, now=now)
                if order_id:
                    created += 1
                else:
                    skipped += 1
            except BookingValidationError as exc:
                standing.last_error = (exc.message or standing_error_message(exc.code))[:500]
                failed += 1
            except Exception:  # noqa: BLE001
                standing.last_error = standing_error_message("run_failed")
                failed += 1
        db.commit()
        return {"processed": len(due), "created": created, "failed": failed, "skipped": skipped}

    def _materialize_one(
        self,
        db: Session,
        settings: Settings,
        standing: StandingOrder,
        *,
        now: datetime,
    ) -> str | None:
        template = self._load_template(db, standing.booking_template_id)
        if not template:
            standing.is_active = False
            standing.last_error = standing_error_message("template_not_found")
            return None
        ctx = self.resolve_context(db, standing.merchant_id)
        if not ctx:
            standing.last_error = standing_error_message("no_active_seat")
            return None
        if ctx.merchant.status != MerchantStatus.ACTIVE.value:
            standing.last_error = standing_error_message("merchant_not_active")
            return None
        payload = dict(template.payload)
        payload["scheduled_at"] = standing.next_run_at.isoformat()
        payload["template_id"] = template.id
        payload["is_recurring"] = True
        payload["recurrence_rule"] = standing.recurrence_rule
        body = MerchantBookDeliveryRequest.model_validate(payload)
        order = self._booking.create_shipment(
            db,
            settings,
            ctx,
            body,
            sandbox=bool(getattr(body, "is_sandbox", False)),
        )
        standing.last_run_at = now
        standing.last_order_id = order.id
        standing.last_error = None
        standing.next_run_at = advance_next_run(standing.next_run_at, standing.recurrence_rule)
        return order.id

    def _load_template(self, db: Session, template_id: str) -> MerchantBookingTemplate | None:
        return (
            db.query(MerchantBookingTemplate)
            .filter(MerchantBookingTemplate.id == template_id)
            .first()
        )

    def template_names(self, db: Session, merchant_id: str) -> dict[str, str]:
        rows = (
            db.query(MerchantBookingTemplate.id, MerchantBookingTemplate.name)
            .filter(MerchantBookingTemplate.merchant_id == merchant_id)
            .all()
        )
        return {str(row[0]): str(row[1]) for row in rows}

    def serialize(self, record: StandingOrder, *, template_name: str | None = None) -> dict[str, Any]:
        return {
            "id": record.id,
            "merchant_id": record.merchant_id,
            "booking_template_id": record.booking_template_id,
            "template_name": template_name,
            "recurrence_rule": record.recurrence_rule,
            "next_run_at": record.next_run_at,
            "last_run_at": record.last_run_at,
            "last_order_id": record.last_order_id,
            "last_error": record.last_error,
            "is_active": record.is_active,
            "created_at": record.created_at,
        }

    def list_serialized(self, db: Session, merchant_id: str) -> list[dict[str, Any]]:
        rows = (
            db.query(StandingOrder)
            .filter(StandingOrder.merchant_id == merchant_id)
            .order_by(StandingOrder.next_run_at.asc())
            .all()
        )
        names = self.template_names(db, merchant_id)
        return [
            self.serialize(row, template_name=names.get(row.booking_template_id))
            for row in rows
        ]
