"""Guest checkout, tracking-page actions, Send-again and email preferences."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote as urlquote
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from porterchain_api.booking_models import (
    Customer,
    CustomerConsent,
    Invoice,
    Order,
    OrderRating,
    Quote,
)
from porterchain_api.config import Settings
from porterchain_api.customer_fast import guard, tokens

logger = logging.getLogger(__name__)

MARKETING_WORDING = (
    "Yes, PorterChain Logistics Inc. may email me delivery tips and offers. "
    "I can unsubscribe at any time."
)
TERMS_VERSION = "2026-10"
#: Up to 5 drops per booking = the main drop-off + 4 extra stops.
MAX_DROPS = 5
MAX_EXTRA_STOPS = MAX_DROPS - 1

ERROR_STATUS: dict[str, int] = {
    "rejected": 400,
    "email_invalid": 422,
    "email_disposable": 422,
    "phone_invalid": 422,
    "consent_required": 422,
    "rate_limited": 429,
    "rate_limit_unavailable": 503,
    "quote_not_found": 404,
    "quote_expired": 410,
    "quote_not_bookable": 409,
    "booking_self_service_disabled": 403,
    "link_invalid": 403,
    "link_expired": 410,
    "order_not_found": 404,
    "cancel_closed": 409,
    "rating_closed": 409,
    "already_rated": 409,
    "score_invalid": 422,
    "too_many_stops": 422,
    "problem_invalid": 422,
    "address_invalid": 422,
    "address_book_full": 409,
    "address_not_found": 404,
}
ERROR_COPY: dict[str, str] = {
    "rejected": "We could not accept this booking. Please try again.",
    "email_invalid": "Enter a valid email address.",
    "email_disposable": "Use an email address you can receive mail at.",
    "phone_invalid": "Enter a valid phone number.",
    "consent_required": "Accept the terms and privacy policy to book.",
    "rate_limited": "Too many attempts. Wait a minute and try again.",
    "rate_limit_unavailable": "Booking is busy right now. Try again in a minute.",
    "quote_not_found": "This price has expired. Get a new price.",
    "quote_expired": "This price has expired. Get a new price.",
    "quote_not_bookable": "This price was already used. Get a new price.",
    "booking_self_service_disabled": "Online booking is paused. Call or email us to book.",
    "link_invalid": "This link is not valid. Use the latest link we sent you.",
    "link_expired": "This link has expired. Use the latest link we sent you.",
    "order_not_found": "We could not find that delivery.",
    "cancel_closed": "The driver is already on the way, so this delivery can no longer be cancelled online.",
    "rating_closed": "You can rate this delivery once it is delivered.",
    "already_rated": "Thanks, this delivery is already rated.",
    "score_invalid": "Pick a rating from 1 to 5.",
    "too_many_stops": "Up to 5 drops per booking.",
    "problem_invalid": "Tell us what went wrong in a few words.",
    "address_invalid": "Enter a full street address.",
    "address_book_full": "Your address book is full. Remove one first.",
    "address_not_found": "That address is no longer saved.",
}


# --------------------------------------------------------------------------- links


def _website(settings: Settings) -> str:
    return (settings.website_url or "").rstrip("/")


def manage_track_url(settings: Settings, order: Order) -> str:
    from porterchain_api.customer_experience.links import make_manage_token

    token = make_manage_token(
        settings.jwt_secret,
        order_id=order.id,
        tracking_number=order.tracking_number,
        ttl_hours=tokens.MANAGE_TTL_HOURS,
    )
    # Locale-prefixed on purpose: the website's locale redirect (/track → /en/track) drops the
    # query string, which would silently strip the token. The track page shows the actions.
    return f"{_website(settings)}/en/track/{urlquote(order.tracking_number, safe='')}?t={urlquote(token, safe='')}"


def preferences_url(settings: Settings, customer: Customer) -> str:
    return f"{_website(settings)}/en/email-preferences?t={urlquote(tokens.prefs_token(settings.jwt_secret, customer.id), safe='')}"


def send_again_url(settings: Settings, order: Order) -> str:
    return f"{_website(settings)}/en/book?again={urlquote(tokens.send_again_token(settings.jwt_secret, order.id), safe='')}"


def account_url(settings: Settings, customer: Customer) -> str:
    """Magic sign-in link to the customer portal.

    With a Clerk secret (prod) we mint a Clerk sign-in token for the email (creating the
    Clerk user when needed) and link to the portal's ``/welcome`` page, which redeems it with
    the ``ticket`` strategy: one tap, signed in, on Orders. No code, no password. Otherwise we
    fall back to the portal sign-in with the email prefilled (Clerk emails a one-time code).
    The pending customer row is adopted on that first sign-in (C-14).
    """
    portal = (settings.customer_portal_url or "").rstrip("/")
    fallback = f"{portal}/sign-in?{urlencode({'email': customer.email, 'redirect_url': '/orders'})}"
    secret = ""
    try:
        from porterchain_api.auth.clerk_registry import clerk_app_for_kind

        app = clerk_app_for_kind(settings, "customer")
        secret = (app.secret_key if app else "") or ""
    except Exception:  # registry shape differs per env; fall back to the platform key
        secret = ""
    secret = secret or getattr(settings, "clerk_secret_key", "") or ""
    if not secret or settings.app_env in ("local", "test"):
        return fallback
    try:
        import httpx

        headers = {"Authorization": f"Bearer {secret}"}
        with httpx.Client(base_url="https://api.clerk.com/v1", headers=headers, timeout=6) as client:
            found = client.get("/users", params={"email_address": customer.email}).json()
            user_id = found[0]["id"] if isinstance(found, list) and found else None
            if not user_id:
                made = client.post(
                    "/users",
                    json={"email_address": [customer.email], "skip_password_requirement": True},
                )
                made.raise_for_status()
                user_id = made.json()["id"]
            ticket = client.post(
                "/sign_in_tokens", json={"user_id": user_id, "expires_in_seconds": 7 * 24 * 3600}
            )
            ticket.raise_for_status()
            token = ticket.json().get("token")
            return f"{portal}/welcome?{urlencode({'ticket': token})}" if token else fallback
    except Exception as exc:
        logger.warning("guest magic link fell back to sign-in: %s", exc)
        return fallback


def confirmation_links(db: Session, settings: Settings, order: Order, customer: Customer | None) -> dict[str, str]:
    """Extra context for the booking-confirmed email (tracking, receipt, account, prefs)."""
    if customer is None or order.merchant_id:
        return {}
    links = {
        "manage_track_url": manage_track_url(settings, order),
        "preferences_url": preferences_url(settings, customer),
        "unsubscribe_url": preferences_url(settings, customer),
    }
    if str(customer.clerk_user_id or "").startswith("pending"):
        links["account_url"] = account_url(settings, customer)
    from porterchain_api.customer_fast.rules import order_locale

    links["locale"] = order_locale(order)
    if links["locale"] == "fr":
        for k in ("manage_track_url", "preferences_url", "unsubscribe_url"):
            links[k] = links[k].replace("/en/", "/fr/", 1)
    return links


# --------------------------------------------------------------------------- consent


def record_consent(
    db: Session, customer: Customer, *, kind: str, granted: bool, source: str, wording: str | None, ip: str | None
) -> None:
    db.add(
        CustomerConsent(
            customer_id=customer.id,
            kind=kind,
            granted=granted,
            source=source,
            wording=(wording or "")[:500] or None,
            ip_hash=guard.ip_hash(ip),
        )
    )


def latest_consent(db: Session, customer_id: str, kind: str) -> CustomerConsent | None:
    return (
        db.query(CustomerConsent)
        .filter(CustomerConsent.customer_id == customer_id, CustomerConsent.kind == kind)
        .order_by(CustomerConsent.created_at.desc(), CustomerConsent.id.desc())
        .first()
    )


# --------------------------------------------------------------------------- guest checkout


def express_checkout(db: Session, settings: Settings, body: Any, *, ip: str | None) -> dict[str, Any]:
    from porterchain_api.admin_engine.platform_settings import booking_self_service
    from porterchain_api.booking_engine import BookingService

    guard.check_bot(honeypot=body.website, form_elapsed_ms=body.form_elapsed_ms)
    email, phone = guard.check_contact(body.email, body.phone)
    if not (body.terms_accepted and body.privacy_accepted):
        raise ValueError("consent_required")
    guard.check_rate(settings, ip=ip, email=email)
    if not booking_self_service(db):
        raise ValueError("booking_self_service_disabled")
    quote_row = db.get(Quote, body.quote_id)
    if quote_row is None:
        raise ValueError("quote_not_found")
    from porterchain_api.customer_fast import geo, rules

    # Self-hosted coordinates so the tracking map can draw even without a geocoder hit.
    if geo.fill_quote_coords(quote_row):
        db.flush()
    if len(quote_row.additional_stops or []) > MAX_EXTRA_STOPS:
        raise ValueError("too_many_stops")

    now = datetime.now(UTC).isoformat()
    try:
        quote, customer, checkout_url = BookingService().start_booking(
            db,
            settings,
            quote_id=body.quote_id,
            email=email,
            phone=phone,
            clerk_user_id=None,
            anonymous_session_id=body.anonymous_session_id,
            consent={
                "terms_accepted": True,
                "privacy_accepted": True,
                "dangerous_goods_confirmed": bool(body.dangerous_goods_confirmed),
                "consent_at": now,
                "terms_version": TERMS_VERSION,
                "channel": "guest_express",
            },
            checkout_channel="retail",
            full_name=body.name,
        )
    except LookupError as exc:
        raise ValueError("quote_not_found") from exc

    record_consent(db, customer, kind="marketing", granted=bool(body.marketing_opt_in),
                   source="guest_checkout", wording=MARKETING_WORDING if body.marketing_opt_in else None, ip=ip)
    rules.flag_order_risk(db, quote, customer)
    from porterchain_api.customer_fast import account

    for stop in [quote.pickup, quote.dropoff, *(quote.additional_stops or [])]:
        account.learn_address(db, customer.id, stop)
    if getattr(body, "locale", None) in ("en", "fr"):
        rules.remember_locale(quote, body.locale)
    db.commit()
    return {
        "quote_id": quote.id,
        "state": quote.state,
        "checkout_url": checkout_url,
        "mock_checkout": bool(settings.allow_stripe_mock and checkout_url is None),
    }


def express_confirmation(db: Session, settings: Settings, quote_id: str) -> dict[str, Any]:
    from porterchain_api.booking_engine import BookingConfirmationService

    order = db.query(Order).filter(Order.quote_id == quote_id).first()
    if order is None or order.merchant_id:
        return {"status": "processing"}
    data = BookingConfirmationService().build_confirmation_response(db, order)
    return {
        "status": "ready",
        "tracking_number": order.tracking_number,
        "order_number": order.order_number,
        "amount_cents": order.amount_cents,
        "currency": order.currency,
        "receipt_url": data.get("receipt_url"),
        "receipt_number": data.get("receipt_number"),
        "manage_track_url": manage_track_url(settings, order),
    }


def owner_track_url(db: Session, settings: Settings, customer_id: str, tracking_number: str) -> str | None:
    order = (
        db.query(Order)
        .filter(Order.tracking_number == tracking_number, Order.customer_id == customer_id)
        .first()
    )
    return manage_track_url(settings, order) if order is not None else None


# --------------------------------------------------------------------------- tracking actions


def _order_for_manage(db: Session, settings: Settings, tracking_number: str, token: str) -> Order:
    from porterchain_api.customer_experience.service import _managed

    return _managed(db, settings, tracking_number, token)


def _receipt(db: Session, order: Order) -> dict[str, Any] | None:
    inv = db.query(Invoice).filter(Invoice.order_id == order.id).order_by(Invoice.created_at.desc()).first()
    if inv is None:
        return None
    return {
        "receipt_number": inv.receipt_number,
        "invoice_number": inv.invoice_number,
        "amount_cents": inv.amount_cents,
        "currency": inv.currency,
        "url": inv.stripe_receipt_url,
    }


def order_actions(db: Session, settings: Settings, tracking_number: str, token: str) -> dict[str, Any]:
    from porterchain_api.customer_experience.context import DELIVERED_STATES
    from porterchain_api.merchant_engine.cancel_policy import (
        cancel_allowed,
        cancel_rule,
    )

    order = _order_for_manage(db, settings, tracking_number, token)
    rating = db.query(OrderRating).filter(OrderRating.order_id == order.id).first()
    retail = not order.merchant_id
    delivered = order.state in DELIVERED_STATES
    return {
        "tracking_number": order.tracking_number,
        "state": order.state,
        "retail": retail,
        "can_cancel": retail and order.state != "CANCELLED" and cancel_allowed(order.state),
        "cancel_rule": cancel_rule(order.state),
        "refund": (order.compliance_metadata or {}).get("customer_cancel") if isinstance(order.compliance_metadata, dict) else None,
        "receipt": _receipt(db, order) if retail else None,
        "can_rate": delivered and rating is None,
        "rating": {"score": rating.score} if rating else None,
        "send_again_url": send_again_url(settings, order) if retail and order.customer_id else None,
    }


def cancel_order(db: Session, settings: Settings, tracking_number: str, token: str) -> dict[str, Any]:
    from porterchain_api.booking_engine.order_transitions import transition_order_state
    from porterchain_api.domain.states import OrderState
    from porterchain_api.merchant_engine.cancel_policy import cancel_allowed

    order = _order_for_manage(db, settings, tracking_number, token)
    if order.merchant_id or order.state == "CANCELLED" or not cancel_allowed(order.state):
        raise ValueError("cancel_closed")
    transition_order_state(
        db, order, OrderState.CANCELLED, event_type="order.cancelled", actor_type="customer",
        actor_id=order.customer_id, payload={"reason": "customer_self_service"},
    )
    refund: dict[str, Any] = {"status": "pending_review", "amount_cents": order.amount_cents,
                              "at": datetime.now(UTC).isoformat()}
    try:
        from porterchain_api.services.stripe_service import create_refund

        refund_id = create_refund(settings, order, idempotency_key=f"customer-cancel:{order.id}")
        if refund_id:
            refund.update({"status": "refunded", "stripe_refund_id": refund_id})
    except Exception as exc:
        logger.warning("customer cancel refund failed for %s: %s", order.id, exc)
    meta = dict(order.compliance_metadata or {}) if isinstance(order.compliance_metadata, dict) else {}
    meta["customer_cancel"] = refund
    order.compliance_metadata = meta
    db.commit()
    return order_actions(db, settings, tracking_number, token)


def rate_order(
    db: Session, settings: Settings, tracking_number: str, token: str, score: int, comment: str | None
) -> dict[str, Any]:
    from porterchain_api.customer_experience.context import DELIVERED_STATES

    order = _order_for_manage(db, settings, tracking_number, token)
    if not 1 <= int(score) <= 5:
        raise ValueError("score_invalid")
    if order.state not in DELIVERED_STATES:
        raise ValueError("rating_closed")
    if db.query(OrderRating).filter(OrderRating.order_id == order.id).first():
        raise ValueError("already_rated")
    text = (comment or "").strip()[:1000] or None
    db.add(OrderRating(order_id=order.id, score=int(score), comment=text))
    db.flush()
    if int(score) <= 3 and order.customer_id:
        # Rule: a low rating is a support case, not a statistic.
        from porterchain_api.booking_engine import CustomerService

        try:
            CustomerService().create_support_ticket(
                db,
                customer_id=order.customer_id,
                subject=f"Low rating ({score}/5) on {order.tracking_number}",
                description=text or "Customer left a low rating with no comment.",
                order_id=order.id,
                idempotency_key=f"low-rating:{order.id}",
            )
        except Exception as exc:
            logger.warning("low-rating ticket failed for %s: %s", order.id, exc)
    db.commit()
    return order_actions(db, settings, tracking_number, token)


# --------------------------------------------------------------------------- send again


def send_again(db: Session, settings: Settings, token: str, *, ip: str | None) -> dict[str, Any]:
    """Clone a past retail order into a fresh quote (new price, same addresses + parcels)."""
    from porterchain_api.booking_engine import CustomerService, QuoteService
    from porterchain_api.routers.quotes import _quote_response
    from porterchain_api.schemas_booking import CreateQuoteRequest

    claims = tokens.verify(settings.jwt_secret, tokens.SEND_AGAIN, token)
    order = db.get(Order, str(claims.get("o") or ""))
    if order is None or order.merchant_id or not order.customer_id or order.is_sandbox:
        raise ValueError("order_not_found")
    payload = CustomerService().rebook_payload(db, order.customer_id, order.id)

    def addr(raw: Any) -> dict[str, Any]:
        raw = raw if isinstance(raw, dict) else {}
        keep = {k: raw.get(k) for k in ("formatted", "place_id", "lat", "lng", "postal") if raw.get(k) is not None}
        keep.setdefault("formatted", str(raw.get("formatted") or ""))
        return keep

    source_quote = db.get(Quote, order.quote_id) if order.quote_id else None
    body = CreateQuoteRequest(
        package_type=str(getattr(source_quote, "package_type", None) or "looseParcel"),
        weight_kg=getattr(source_quote, "weight_kg", None),
        dimensions=getattr(source_quote, "dimensions", None),
        pickup=addr(payload["pickup"]),
        dropoff=addr(payload["dropoff"]),
        vehicle_class=str(payload.get("vehicle_class") or "sedan_suv"),
        booking_mode=payload.get("booking_mode") or "parcels",
        parcels=payload.get("parcels") or None,
        declared_value_cents=payload.get("declared_value_cents"),
        additional_stops=[addr(s) for s in payload.get("additional_stops") or [] if isinstance(s, dict)] or None,
        scheduled_at=datetime.now(UTC) + timedelta(minutes=5),
        schedule_mode="now",
    )
    try:
        quote = QuoteService().create_quote(db, settings, body, ip_address=ip)
    except ValueError:
        # Parcels derived from a weight-only booking carry no dimensions: re-price from weight.
        db.rollback()
        quote = QuoteService().create_quote(db, settings, body.model_copy(update={"parcels": None}), ip_address=ip)
    customer = db.get(Customer, order.customer_id)
    return {
        "quote": _quote_response(quote).model_dump(mode="json"),
        "contact": {"email": customer.email if customer else "", "phone": customer.phone if customer else "",
                    "name": customer.full_name if customer else ""},
        "source_tracking_number": order.tracking_number,
    }


# --------------------------------------------------------------------------- email preferences

PREF_CATEGORIES = ("tracking", "reorder", "marketing")


def _customer_from_prefs(db: Session, settings: Settings, token: str) -> Customer:
    claims = tokens.verify(settings.jwt_secret, tokens.PREFS, token)
    customer = db.get(Customer, str(claims.get("c") or ""))
    if customer is None:
        raise ValueError("link_invalid")
    return customer


def _mask(email: str) -> str:
    name, _, domain = (email or "").partition("@")
    return f"{name[:2]}{'•' * max(1, len(name) - 2)}@{domain}" if domain else ""


def get_preferences(db: Session, settings: Settings, token: str) -> dict[str, Any]:
    from porterchain_api.notification_engine.preference_service import PreferenceService

    customer = _customer_from_prefs(db, settings, token)
    svc = PreferenceService()
    email = {c: svc.is_enabled(db, user_role="customer", user_id=customer.id, category=c, channel="email")
             for c in PREF_CATEGORIES}
    marketing = latest_consent(db, customer.id, "marketing")
    # Marketing needs CASL express consent on file, not just a toggle.
    email["marketing"] = bool(email["marketing"] and marketing and marketing.granted)
    return {
        "email": _mask(customer.email),
        "preferences": email,
        "marketing_consent_at": marketing.created_at.isoformat() if marketing and marketing.granted and marketing.created_at else None,
        "deletion_requested": customer.privacy_status == "deletion_hold",
        "portal_url": (settings.customer_portal_url or "").rstrip("/") + "/account",
    }


def set_preferences(db: Session, settings: Settings, token: str, prefs: dict[str, bool], *, ip: str | None) -> dict[str, Any]:
    from porterchain_api.notification_engine.preference_service import PreferenceService

    customer = _customer_from_prefs(db, settings, token)
    svc = PreferenceService()
    for category in PREF_CATEGORIES:
        if category not in prefs:
            continue
        on = bool(prefs[category])
        svc.upsert(db, user_role="customer", user_id=customer.id, category=category, email_enabled=on)
        if category in ("marketing", "reorder"):
            record_consent(db, customer, kind=category, granted=on, source="email_preferences",
                           wording=MARKETING_WORDING if (category == "marketing" and on) else None, ip=ip)
    db.commit()
    return get_preferences(db, settings, token)


def unsubscribe_all(db: Session, settings: Settings, token: str, *, ip: str | None) -> dict[str, Any]:
    """One-click: stop every non-essential email (reorder + marketing)."""
    return set_preferences(db, settings, token, {"reorder": False, "marketing": False}, ip=ip)


def request_deletion(db: Session, settings: Settings, token: str) -> dict[str, Any]:
    from porterchain_api.compliance_engine.privacy_service import PrivacyService

    customer = _customer_from_prefs(db, settings, token)
    if customer.privacy_status == "deletion_hold":
        return {"status": "received", "reference": customer.privacy_hold_reference, "sla_days": 30}
    return PrivacyService().request_customer_deletion(db, customer, reason="email_preferences_link")
