"""Facade used by the public + merchant routers (routers stay free of ORM work)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.customer_experience import scheduling
from porterchain_api.customer_experience.context import merchant_for
from porterchain_api.customer_experience.links import read_manage_token
from porterchain_api.customer_experience.settings import (
    PRESETS,
    apply_preset,
    cx_for_merchant,
    merge_patch,
    normalize_cx,
)
from porterchain_api.customer_experience.tracking_view import (
    build_experience,
    proof_of_delivery,
)

ERROR_STATUS: dict[str, int] = {
    "order_not_found": 404,
    "link_invalid": 403,
    "link_expired": 410,
    "self_service_disabled": 403,
    "reschedule_closed": 409,
    "instructions_closed": 409,
    "window_unavailable": 409,
    "safe_place_not_allowed": 422,
}
ERROR_COPY: dict[str, str] = {
    "order_not_found": "We could not find that delivery.",
    "link_invalid": "This link is not valid. Use the latest link we sent you.",
    "link_expired": "This link has expired. Use the latest link we sent you.",
    "self_service_disabled": "Online delivery changes are not available for this sender.",
    "reschedule_closed": "This delivery can no longer be rescheduled online.",
    "instructions_closed": "Instructions can no longer be changed for this delivery.",
    "window_unavailable": "That delivery window is no longer available. Pick another.",
    "safe_place_not_allowed": "This sender requires a hand-to-hand delivery, so a safe place cannot be used.",
}


def _public_order(db: Session, tracking_number: str) -> Order:
    order = db.query(Order).filter(Order.tracking_number == tracking_number).first()
    if order is None or order.is_sandbox:
        raise LookupError("order_not_found")
    return order


def experience(db: Session, settings: Settings, tracking_number: str, token: str | None = None) -> dict[str, Any]:
    order = _public_order(db, tracking_number)
    with_photos = False
    if token:
        try:
            read_manage_token(settings.jwt_secret, token, tracking_number=tracking_number)
            with_photos = True
        except ValueError:
            with_photos = False
    return build_experience(db, order, with_photos=with_photos)


def _managed(db: Session, settings: Settings, tracking_number: str, token: str) -> Order:
    claims = read_manage_token(settings.jwt_secret, token, tracking_number=tracking_number)
    order = _public_order(db, tracking_number)
    if order.id != claims["order_id"]:
        raise ValueError("link_invalid")
    return order


def manage_options(db: Session, settings: Settings, tracking_number: str, token: str) -> dict[str, Any]:
    return scheduling.options(db, _managed(db, settings, tracking_number, token))


def manage_schedule(db: Session, settings: Settings, tracking_number: str, token: str, code: str) -> dict[str, Any]:
    return scheduling.choose_window(db, _managed(db, settings, tracking_number, token), code)


def manage_instructions(
    db: Session, settings: Settings, tracking_number: str, token: str, body: dict[str, Any]
) -> dict[str, Any]:
    return scheduling.set_instructions(db, _managed(db, settings, tracking_number, token), body)


def manage_pod(db: Session, settings: Settings, tracking_number: str, token: str) -> dict[str, Any]:
    order = _managed(db, settings, tracking_number, token)
    cfg = cx_for_merchant(merchant_for(db, order))
    return {"proof_of_delivery": proof_of_delivery(db, order, cfg, with_photos=True)}


def merchant_settings(merchant: Any) -> dict[str, Any]:
    return {"settings": cx_for_merchant(merchant), "presets": sorted(PRESETS)}


def update_merchant_settings(db: Session, ctx: Any, body: dict[str, Any]) -> dict[str, Any]:
    from porterchain_api.merchant_engine.settings_service import (
        MerchantSettingsService,
        _save_settings,
        _settings_bucket,
    )

    current = cx_for_merchant(ctx.merchant)
    preset = body.pop("preset", None) if isinstance(body, dict) else None
    merged = normalize_cx(merge_patch(current, body or {}))
    if preset:
        merged = apply_preset(merged, str(preset))
    bucket = _settings_bucket(ctx.merchant)
    bucket["customer_experience"] = merged
    _save_settings(ctx.merchant, bucket)
    MerchantSettingsService()._audit(db, ctx, "settings.customer_experience", {"preset": preset, **merged})
    db.commit()
    db.refresh(ctx.merchant)
    return merchant_settings(ctx.merchant)
