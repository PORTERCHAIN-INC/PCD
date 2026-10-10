"""Customer fast-book: guest checkout, tracking actions, Send again, email preferences."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService
from porterchain_api.booking_engine.quote_service import QuoteService
from porterchain_api.booking_models import Customer, CustomerConsent, Order, OrderRating, Quote
from porterchain_api.config import Settings, get_settings
from porterchain_api.customer_experience.links import make_manage_token
from porterchain_api.customer_fast import guard, service, tokens
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.notification_engine.templates import render_email
from porterchain_api.schemas import AddressInput, CreateQuoteRequest


def _quote(db: Session, settings: Settings) -> Quote:
    return QuoteService().create_quote(
        db,
        settings,
        CreateQuoteRequest(
            anonymous_session_id=f"fast-{uuid4().hex[:8]}",
            pickup=AddressInput(formatted="100 King St W, Toronto ON M5X 1A9", lat=43.6488, lng=-79.3817),
            dropoff=AddressInput(formatted="200 Bay St, Toronto ON M5J 2J2", lat=43.6476, lng=-79.3797),
            vehicle_class="sedan_suv",
            weight_kg=5.0,
            scheduled_at=datetime.now(UTC) + timedelta(hours=2),
            schedule_mode="now",
        ),
        ip_address="127.0.0.1",
    )


def _body(quote_id: str, **over) -> SimpleNamespace:
    base = dict(
        quote_id=quote_id,
        name="Asha Guest",
        email=f"guest-{uuid4().hex[:8]}@example.ca",
        phone="+1 416 555 0199",
        terms_accepted=True,
        privacy_accepted=True,
        dangerous_goods_confirmed=True,
        marketing_opt_in=False,
        anonymous_session_id=None,
        website="",
        form_elapsed_ms=9000,
    )
    base.update(over)
    return SimpleNamespace(**base)


def _paid_guest_order(db: Session, settings: Settings, **over) -> tuple[Order, Customer]:
    quote = _quote(db, settings)
    out = service.express_checkout(db, settings, _body(quote.id, **over), ip=f"10.0.{uuid4().int % 250}.1")
    assert out["mock_checkout"] is True
    order = BookingConfirmationService().mock_complete_checkout(db, settings, quote.id)
    return order, db.get(Customer, order.customer_id)


def _token(settings: Settings, order: Order) -> str:
    return make_manage_token(settings.jwt_secret, order_id=order.id, tracking_number=order.tracking_number)


# ------------------------------------------------------------------ guest checkout


def test_guest_checkout_books_without_account(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings, marketing_opt_in=True)
    assert order.tracking_number
    assert customer.clerk_user_id.startswith("pending")
    consent = service.latest_consent(db, customer.id, "marketing")
    assert consent is not None and consent.granted and "unsubscribe" in (consent.wording or "")
    assert consent.ip_hash and "10.0." not in consent.ip_hash


def test_guest_checkout_reuses_customer_by_email(db: Session, settings: Settings) -> None:
    email = f"repeat-{uuid4().hex[:6]}@example.ca"
    first, c1 = _paid_guest_order(db, settings, email=email)
    second, c2 = _paid_guest_order(db, settings, email=email.upper())
    assert c1.id == c2.id and first.id != second.id


@pytest.mark.parametrize(
    "over,code",
    [
        ({"website": "http://spam"}, "rejected"),
        ({"form_elapsed_ms": 300}, "rejected"),
        ({"form_elapsed_ms": None}, "rejected"),
        ({"email": "x@mailinator.com"}, "email_disposable"),
        ({"email": "not-an-email"}, "email_invalid"),
        ({"phone": "12"}, "phone_invalid"),
        ({"terms_accepted": False}, "consent_required"),
    ],
)
def test_guest_checkout_abuse_guards(db: Session, settings: Settings, over: dict, code: str) -> None:
    quote = _quote(db, settings)
    with pytest.raises(ValueError, match=code):
        service.express_checkout(db, settings, _body(quote.id, **over), ip="10.9.9.9")


def test_guest_checkout_rate_limit(monkeypatch, settings: Settings) -> None:
    calls: dict[str, int] = {}

    def fake_window(key, limit, *, window=None):
        calls[key] = calls.get(key, 0) + 1
        return (calls[key] <= limit, calls[key], None)

    monkeypatch.setattr("porterchain_api.platform.rate_limit.check_fixed_window", fake_window)
    for _ in range(guard.EMAIL_PER_MINUTE):
        guard.check_rate(settings, ip="1.2.3.4", email="a@b.ca")
    with pytest.raises(ValueError, match="rate_limited"):
        for _ in range(10):
            guard.check_rate(settings, ip="1.2.3.4", email="a@b.ca")


def test_guest_checkout_rate_limit_fails_closed_in_production(monkeypatch) -> None:
    monkeypatch.setattr(
        "porterchain_api.platform.rate_limit.check_fixed_window", lambda *a, **k: (True, 0, "redis down")
    )
    prod = SimpleNamespace(app_env="production")
    with pytest.raises(ValueError, match="rate_limit_unavailable"):
        guard.check_rate(prod, ip="1.2.3.4", email="a@b.ca")  # type: ignore[arg-type]


def test_unknown_quote_rejected(db: Session, settings: Settings) -> None:
    with pytest.raises(ValueError, match="quote_not_found"):
        service.express_checkout(db, settings, _body(str(uuid4())), ip="10.1.1.1")


# ------------------------------------------------------------------ confirmation email


def test_booking_confirmed_payload_has_links(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    links = service.confirmation_links(db, settings, order, customer)
    assert "?t=" in links["manage_track_url"] and "/manage" not in links["manage_track_url"]
    assert links["account_url"].startswith(settings.customer_portal_url.rstrip("/") + "/sign-in?")
    assert "/email-preferences?t=" in links["preferences_url"]
    subject, text, html = render_email(
        "booking_confirmed", {"tracking_number": order.tracking_number, **links}
    )
    assert "Track, receipt and cancel" in text and "no password" in text
    assert "Track &amp; manage" in html or "Track & manage" in html


def test_merchant_orders_get_no_fast_links(db: Session, settings: Settings) -> None:
    order = SimpleNamespace(merchant_id="m1")
    assert service.confirmation_links(db, settings, order, SimpleNamespace()) == {}  # type: ignore[arg-type]


# ------------------------------------------------------------------ tracking actions


def test_actions_receipt_cancel_and_refund(db: Session, settings: Settings) -> None:
    order, _ = _paid_guest_order(db, settings)
    t = _token(settings, order)
    actions = service.order_actions(db, settings, order.tracking_number, t)
    assert actions["retail"] and actions["can_cancel"] and actions["receipt"]["receipt_number"]
    assert actions["send_again_url"] and not actions["can_rate"]
    after = service.cancel_order(db, settings, order.tracking_number, t)
    assert after["state"] == "CANCELLED" and not after["can_cancel"]
    assert after["refund"]["status"] in {"pending_review", "refunded"}
    with pytest.raises(ValueError, match="cancel_closed"):
        service.cancel_order(db, settings, order.tracking_number, t)


def test_actions_need_valid_token(db: Session, settings: Settings) -> None:
    order, _ = _paid_guest_order(db, settings)
    with pytest.raises(ValueError, match="link_invalid"):
        service.order_actions(db, settings, order.tracking_number, "bad.token")
    other, _ = _paid_guest_order(db, settings)
    with pytest.raises(ValueError, match="link_invalid"):
        service.order_actions(db, settings, order.tracking_number, _token(settings, other))


def test_rating_after_delivery_and_low_rating_ticket(db: Session, settings: Settings) -> None:
    from porterchain_api.admin_models import SupportTicket

    order, _ = _paid_guest_order(db, settings)
    t = _token(settings, order)
    with pytest.raises(ValueError, match="rating_closed"):
        service.rate_order(db, settings, order.tracking_number, t, 5, None)
    order.state = "DELIVERED"
    db.commit()
    out = service.rate_order(db, settings, order.tracking_number, t, 2, "Late")
    assert out["rating"] == {"score": 2} and not out["can_rate"]
    assert db.query(OrderRating).filter(OrderRating.order_id == order.id).count() == 1
    assert db.query(SupportTicket).filter(SupportTicket.order_id == order.id).count() == 1
    with pytest.raises(ValueError, match="already_rated"):
        service.rate_order(db, settings, order.tracking_number, t, 5, None)


def test_retail_tracking_page_is_enhanced_with_pod(db: Session, settings: Settings) -> None:
    from porterchain_api.customer_experience.settings import cx_for_merchant

    cfg = cx_for_merchant(None)
    assert cfg["tracking"]["branded_page"] and cfg["tracking"]["show_pod_photo"]
    assert cfg["self_service"]["enabled"]
    order, _ = _paid_guest_order(db, settings)
    from porterchain_api.customer_experience import service as cx

    assert cx.experience(db, settings, order.tracking_number)["enhanced"] is True


# ------------------------------------------------------------------ send again


def test_send_again_clones_route_into_fresh_quote(db: Session, settings: Settings) -> None:
    order, customer = _paid_guest_order(db, settings)
    token = tokens.send_again_token(settings.jwt_secret, order.id)
    out = service.send_again(db, settings, token, ip="10.2.2.2")
    assert out["quote"]["quote_id"] != order.quote_id
    assert out["quote"]["dropoff"]["formatted"] == order.dropoff["formatted"]
    assert out["contact"]["email"] == customer.email
    with pytest.raises(ValueError, match="link_invalid"):
        # A preferences link must never work as a send-again link.
        service.send_again(db, settings, tokens.prefs_token(settings.jwt_secret, customer.id), ip=None)


def test_send_again_email_respects_consent_and_runs_once(db: Session, settings: Settings) -> None:
    from porterchain_api.customer_fast.mailer import enrich_send_again
    from porterchain_api.notification_engine.event_router import _specs_for_event
    from porterchain_shared.events.catalog import DomainEventType

    evt = DomainEventType.PARCEL_DELIVERED
    order, customer = _paid_guest_order(db, settings)
    payload = enrich_send_again(db, settings, evt, {"order_id": order.id})
    assert payload["send_again_eligible"] is True
    assert "/email-preferences?t=" in payload["unsubscribe_url"]
    specs = [s for s in _specs_for_event(evt, payload) if s["template_key"] == "fast_send_again"]
    assert len(specs) == 1
    assert specs[0]["category"] == "reorder" and specs[0]["recipient_address"] == customer.email
    # Once per order.
    assert "send_again_eligible" not in enrich_send_again(db, settings, evt, {"order_id": order.id})

    order2, customer2 = _paid_guest_order(db, settings)
    service.unsubscribe_all(db, settings, tokens.prefs_token(settings.jwt_secret, customer2.id), ip=None)
    assert "send_again_eligible" not in enrich_send_again(db, settings, evt, {"order_id": order2.id})


def test_send_again_template_is_casl_complete() -> None:
    subject, text, html = render_email(
        "fast_send_again",
        {"tracking_number": "PC1", "send_again_url": "https://x/book?again=1", "unsubscribe_url": "https://x/u"},
    )
    assert "PorterChain Logistics Inc." in text and "https://x/u" in text
    assert "Send again" in html and "https://x/u" in html
    from porterchain_api.notification_engine.templates import TEMPLATE_META

    assert TEMPLATE_META["fast_send_again"]["category"] == "reorder"


# ------------------------------------------------------------------ preferences


def test_preferences_marketing_needs_express_consent(db: Session, settings: Settings) -> None:
    _order, customer = _paid_guest_order(db, settings)
    t = tokens.prefs_token(settings.jwt_secret, customer.id)
    prefs = service.get_preferences(db, settings, t)
    assert prefs["preferences"] == {"tracking": True, "reorder": True, "marketing": False}
    assert "•" in prefs["email"]
    on = service.set_preferences(db, settings, t, {"marketing": True}, ip="10.3.3.3")
    assert on["preferences"]["marketing"] is True and on["marketing_consent_at"]
    off = service.unsubscribe_all(db, settings, t, ip=None)
    assert off["preferences"] == {"tracking": True, "reorder": False, "marketing": False}
    log = db.query(CustomerConsent).filter(CustomerConsent.customer_id == customer.id).count()
    assert log >= 4  # checkout + opt-in + two opt-outs: append-only proof


def test_preferences_deletion_request(db: Session, settings: Settings) -> None:
    _order, customer = _paid_guest_order(db, settings)
    t = tokens.prefs_token(settings.jwt_secret, customer.id)
    out = service.request_deletion(db, settings, t)
    assert out["reference"].startswith("DSR-")
    again = service.request_deletion(db, settings, t)
    assert again["reference"] == out["reference"]
    assert service.get_preferences(db, settings, t)["deletion_requested"] is True


def test_tokens_expire_and_bind_purpose(settings: Settings) -> None:
    old = tokens.sign(settings.jwt_secret, tokens.PREFS, {"c": "x"}, ttl=timedelta(seconds=-5))
    with pytest.raises(ValueError, match="link_expired"):
        tokens.verify(settings.jwt_secret, tokens.PREFS, old)
    good = tokens.prefs_token(settings.jwt_secret, "x")
    with pytest.raises(ValueError, match="link_invalid"):
        tokens.verify(settings.jwt_secret, tokens.SEND_AGAIN, good)


# ------------------------------------------------------------------ HTTP


@pytest.fixture
def client(db: Session, settings: Settings):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_settings, None)


def test_http_express_checkout_and_confirmation(client, db: Session, settings: Settings) -> None:
    quote = _quote(db, settings)
    res = client.post(
        "/v1/express/checkout",
        json={**vars(_body(quote.id)), "anonymous_session_id": None},
    )
    assert res.status_code == 200, res.text
    assert res.json()["mock_checkout"] is True
    assert client.get(f"/v1/express/confirmation?quote_id={quote.id}").json()["status"] == "processing"
    BookingConfirmationService().mock_complete_checkout(db, settings, quote.id)
    done = client.get(f"/v1/express/confirmation?quote_id={quote.id}").json()
    assert done["status"] == "ready" and "?t=" in done["manage_track_url"]


def test_http_honeypot_returns_clean_error(client, db: Session, settings: Settings) -> None:
    quote = _quote(db, settings)
    res = client.post("/v1/express/checkout", json={**vars(_body(quote.id)), "website": "x"})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "rejected"


def test_http_actions_require_token(client, db: Session, settings: Settings) -> None:
    order, _ = _paid_guest_order(db, settings)
    assert client.get(f"/v1/delivery-manage/{order.tracking_number}/actions").status_code == 422
    ok = client.get(
        f"/v1/delivery-manage/{order.tracking_number}/actions",
        headers={"X-Manage-Token": _token(settings, order)},
    )
    assert ok.status_code == 200 and ok.json()["can_cancel"] is True
