"""Proactive recipient notifications (out for delivery, you're next, ~N min, delivered, attempted).

Only ever *queues* NotificationRecords through ``NotificationEngine.dispatch``
(recipient_type="consignee"); the worker's DeliveryService does the sending.
Off by default per merchant. Dedupe: per-kind stamp in ``cx.notified`` plus the
engine's idempotency key (event|order:kind|template|channel|recipient).
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.customer_experience.context import (
    consignee_contacts,
    cx_meta,
    merchant_for,
    update_cx_meta,
)
from porterchain_api.customer_experience.settings import cx_for_merchant
from porterchain_api.customer_experience.templates import CX_PLACEHOLDERS

#: Channels with a real transactional sender in DeliveryService today.
SUPPORTED_CHANNELS = ("email", "sms")


def in_quiet_hours(quiet: dict[str, Any], now: datetime) -> bool:
    if not quiet.get("enabled"):
        return False
    local = now.astimezone(ZoneInfo(quiet.get("timezone") or "America/Toronto")).time()
    start = time.fromisoformat(quiet["start"])
    end = time.fromisoformat(quiet["end"])
    if start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end


def manage_link(settings: Settings, order: Order, cfg: dict[str, Any], *, now: datetime | None = None) -> str | None:
    if not cfg["self_service"]["enabled"]:
        return None
    from porterchain_api.customer_experience.links import make_manage_token, manage_url

    token = make_manage_token(
        settings.jwt_secret,
        order_id=order.id,
        tracking_number=order.tracking_number,
        ttl_hours=cfg["self_service"]["link_ttl_hours"],
        now=now,
    )
    return manage_url(settings.website_url, order.tracking_number, token)


def _stops_line(stops_away: int | None) -> str:
    if stops_away is None or stops_away <= 0:
        return "You're next!"
    return f"You're {stops_away} stop{'s' if stops_away != 1 else ''} away."


def build_context(
    settings: Settings,
    order: Order,
    merchant: Any,
    cfg: dict[str, Any],
    kind: str,
    *,
    extra: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import (
        public_tracking_url,
    )

    extra = dict(extra or {})
    track = public_tracking_url(settings, order.tracking_number)
    manage = manage_link(settings, order, cfg, now=now)
    meta = cx_meta(order)
    rules = cfg["delivery_rules"]
    schedule = meta.get("schedule") if isinstance(meta.get("schedule"), dict) else {}
    help_bits = [cfg["tracking"]["support_email"], cfg["tracking"]["support_phone"]]
    decision = meta.get("reattempt") if isinstance(meta.get("reattempt"), dict) else {}
    if order.state == "RETURN_TO_SENDER" or decision.get("action") == "return_to_sender":
        attempt_line = "After repeated attempts this parcel is being returned to the sender."
    elif manage and cfg["self_service"]["allow_reschedule"]:
        attempt_line = f"Choose a new delivery time: {manage}"
    else:
        attempt_line = "We will contact you to arrange another attempt."
    ctx: dict[str, Any] = {key: "" for key in CX_PLACEHOLDERS}
    ctx.update(
        {
            "merchant_name": getattr(merchant, "company_name", None) or "Your sender",
            "tracking_number": order.tracking_number,
            "order_number": order.order_number,
            "public_track_url": track,
            "manage_url": manage or track,
            "pod_url": manage or track,
            "window_line": f" Expected {schedule['label']}." if schedule.get("label") else "",
            "manage_line": f"\nChange time or add instructions: {manage}" if manage else "",
            "stops_line": _stops_line(extra.get("stops_away")),
            "instructions_line": (
                f"\nAdd a gate code or buzzer: {manage}" if manage and cfg["self_service"]["allow_instructions"] else ""
            ),
            "eta_minutes": str(extra.get("eta_minutes") or cfg["notifications"]["eta_minutes"]),
            "id_line": " Please have photo ID ready." if rules["id_required"] else "",
            "attempt_line": attempt_line,
            "help_line": " / ".join(b for b in help_bits if b) or "reply to this message.",
            "cta_label": "View proof of delivery" if kind == "delivered" else "Track delivery",
            "cta_url": (manage or track) if kind in ("delivered", "attempted", "schedule_request") else track,
            "cx_kind": kind,
        }
    )
    return ctx


def _allow_sms_for_recipient(db: Session, order: Order) -> None:
    """SMS is opt-in per recipient in PreferenceService. The merchant turning on the
    SMS channel is the opt-in for this transactional stream; an existing row (e.g. the
    recipient replied STOP and it was set to False) is never overridden."""
    from porterchain_api.notification_engine.models import NotificationPreference

    exists = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_role == "consignee",
            NotificationPreference.user_id == order.id,
            NotificationPreference.category == "tracking",
        )
        .first()
    )
    if exists is None:
        db.add(
            NotificationPreference(
                user_role="consignee",
                user_id=order.id,
                category="tracking",
                email_enabled=True,
                sms_enabled=True,
                push_enabled=False,
                in_app_enabled=False,
            )
        )
        db.flush()


def notify(
    db: Session,
    settings: Settings,
    order: Order,
    kind: str,
    *,
    extra: dict[str, Any] | None = None,
    now: datetime | None = None,
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    """Queue one recipient notification kind. Returns {'queued': [...], 'skipped': {channel/reason}}."""
    now = now or datetime.now(UTC)
    result: dict[str, Any] = {"kind": kind, "queued": [], "skipped": {}}
    if order.is_sandbox:
        result["skipped"]["all"] = "sandbox"
        return result
    merchant = merchant_for(db, order)
    cfg = cx_for_merchant(merchant)
    ncfg = cfg["notifications"]
    if not ncfg["enabled"] or not ncfg["events"].get(kind, False):
        result["skipped"]["all"] = "disabled"
        return result
    key = dedupe_key or kind
    notified = dict(cx_meta(order).get("notified") or {})
    if key in notified:
        result["skipped"]["all"] = "duplicate"
        return result
    contacts = consignee_contacts(order)
    ctx = build_context(settings, order, merchant, cfg, kind, extra=extra, now=now)
    quiet = in_quiet_hours(ncfg["quiet_hours"], now)
    from porterchain_api.notification_engine.engine import get_notification_engine

    engine = get_notification_engine()
    for channel, on in ncfg["channels"].items():
        if not on:
            continue
        if channel not in SUPPORTED_CHANNELS:
            result["skipped"][channel] = "channel_unavailable"
            continue
        address = contacts["email"] if channel == "email" else contacts["phone"]
        if not address:
            result["skipped"][channel] = "no_address"
            continue
        if channel != "email" and quiet:
            result["skipped"][channel] = "quiet_hours"
            continue
        if channel == "sms":
            _allow_sms_for_recipient(db, order)
        record = engine.dispatch(
            db,
            event_type=f"cx.{kind}",
            template_key=f"cx_{kind}",
            channel=channel,
            recipient_type="consignee",
            recipient_id=order.id,
            recipient_address=address,
            context=ctx,
            category="tracking",
            priority="high",
            search_tags={"order_id": order.id, "tracking_number": order.tracking_number, "cx_kind": kind},
            deep_link=ctx["public_track_url"],
            # domain_events.correlation_id is 36 chars: deterministic uuid5 per order+kind.
            correlation_id=str(uuid5(NAMESPACE_URL, f"cx:{order.id}:{key}")),
        )
        if record is not None:
            result["queued"].append(channel)
        else:
            result["skipped"][channel] = "suppressed"
    if result["queued"]:
        notified[key] = now.isoformat()
        update_cx_meta(order, notified=notified)
        db.flush()
    return result
