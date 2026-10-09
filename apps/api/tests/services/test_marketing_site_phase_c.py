"""Phase C — website marketing API: instant estimate, calculator leads (CASL,
honeypot, rate limit), hero A/B config, lead attribution and signup attribution.

No real message may leave the box: queue publishing, the lead agent and nurture
are tripwired for every test.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import porterchain_api.main  # noqa: F401 — registers every ORM model (FK targets)
from porterchain_api.config import get_settings
from porterchain_api.crm_models import CrmLead
from porterchain_api.main import create_app
from porterchain_api.marketing_site import rate_limit as rl
from porterchain_api.marketing_site.config import (
    default_marketing_site,
    normalize_marketing_site,
    public_marketing_config,
)
from porterchain_api.marketing_site.fsa_geo import fsa_centroid
from porterchain_api.marketing_site.lead_stats import lead_attribution_summary
from porterchain_api.marketing_site.signup_attribution import (
    clean_signup_attribution,
    stamp_signup_attribution,
)


@pytest.fixture(autouse=True)
def no_outbound(monkeypatch):
    """Tripwire: nothing may be queued for delivery or auto-sent."""

    def _boom(*_a, **_k):
        raise AssertionError("outbound message path reached from calculator")

    from porterchain_api.collaboration_engine import lead_agent, lead_nurture

    monkeypatch.setattr(lead_agent, "run_lead_agent", _boom)
    monkeypatch.setattr(lead_nurture, "apply_nurture_after_ingest", _boom)
    import porterchain_shared.queue.publisher as pub

    monkeypatch.setattr(pub, "get_queue_publisher", _boom)


@pytest.fixture(autouse=True)
def open_limits(monkeypatch):
    monkeypatch.setattr(rl, "check_fixed_window", lambda key, limit, **_: (True, 1, None))


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("PUBLIC_INGEST_API_KEY", "")
    get_settings.cache_clear()
    yield TestClient(create_app())
    get_settings.cache_clear()


def _lead_body(**over):
    body = {
        "business_name": "Acme Pharmacy",
        "email": f"owner+{uuid4().hex[:10]}@acme-pharmacy.ca",
        # Unique phone: the ingest bus merges leads that share a phone number.
        "phone": f"+1 416 {uuid4().int % 900 + 100} {uuid4().int % 9000 + 1000}",
        "industry": "pharmacy",
        "monthly_volume": "21-100",
        "marketing_consent": False,
        "pickup_fsa": "M5V",
        "dropoff_fsa": "L5T",
        "vehicle_class": "sedan_suv",
        "estimate_cents": 9640,
        "website": "",
        "form_elapsed_ms": 9000,
        "utm_source": "google",
        "utm_medium": "cpc",
        "utm_campaign": "pharmacy-gta",
        "landing_page": "http://localhost:3000/en/delivery/pharmacy/mississauga",
        "source_page": "delivery-cost-calculator",
    }
    body.update(over)
    return body


def _lead_by_email(db, email: str) -> CrmLead | None:
    db.expire_all()
    return db.query(CrmLead).filter(CrmLead.email == email.lower()).first()


# ------------------------------------------------------------------ config


def test_marketing_config_defaults_keep_ab_off_and_no_outreach():
    cfg = default_marketing_site()
    assert cfg["hero_ab"]["enabled"] is False
    assert cfg["calculator"]["enabled"] is True
    assert cfg["calculator"]["auto_outreach"] is False
    pub = public_marketing_config(cfg)
    assert pub == {
        "hero_ab": {"enabled": False, "experiment": "hero_copy_v1", "split_percent": 50},
        "calculator": {"enabled": True},
    }


def test_marketing_config_validation():
    out = normalize_marketing_site({"hero_ab": {"enabled": True, "split_percent": 20, "experiment": "Hero V2!"}})
    assert out["hero_ab"] == {"enabled": True, "experiment": "herov2", "split_percent": 20}
    with pytest.raises(ValueError, match="hero_ab.split_percent"):
        normalize_marketing_site({"hero_ab": {"split_percent": 120}})
    with pytest.raises(ValueError, match="calculator.estimates_per_minute"):
        normalize_marketing_site({"calculator": {"estimates_per_minute": 0}})


def test_marketing_site_is_a_writable_admin_setting(db):
    from porterchain_api.admin_engine.settings_bindings import resolve_writable_config_key
    from porterchain_api.admin_engine.settings_service import AdminSettingsService

    assert resolve_writable_config_key("marketing_site") == "marketing_site"
    value = AdminSettingsService().get_config_value(db, "marketing_site")
    assert value["hero_ab"]["enabled"] is False


def test_public_marketing_config_endpoint(client):
    res = client.get("/v1/public/marketing-config")
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"hero_ab", "calculator"}
    assert "estimates_per_minute" not in body["calculator"]


# ------------------------------------------------------------------ estimate


def test_fsa_centroid_uses_registry_and_rejects_outside():
    code, lat, lng = fsa_centroid("m5v 3l9")
    assert code == "M5V" and 43 < lat < 44 and -80 < lng < -79
    assert fsa_centroid("V6B 1A1") is None  # Vancouver
    assert fsa_centroid("hello") is None


def test_estimate_returns_real_price_without_storing_anything(client, db):
    from porterchain_api.booking_models import Quote

    quotes_before = db.query(Quote).count()
    leads_before = db.query(CrmLead).count()
    res = client.post(
        "/v1/public/estimate",
        json={"pickup_postal": "M5V 2T6", "dropoff_postal": "L5T", "vehicle_class": "cargo_van"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["pickup_fsa"] == "M5V" and body["dropoff_fsa"] == "L5T"
    assert body["amount_cents"] > 0 and body["currency"] == "CAD"
    assert body["lines"] and body["subtotal_cents"] == sum(line["amount_cents"] for line in body["lines"])
    assert body["amount_cents"] == body["subtotal_cents"] + body["tax_cents"]
    assert abs(body["tax_cents"] - round(body["subtotal_cents"] * 0.13)) <= 1
    assert body["basis"] == "fsa_centroid" and "HST" in body["disclaimer"]
    db.expire_all()
    assert db.query(Quote).count() == quotes_before
    assert db.query(CrmLead).count() == leads_before


def test_estimate_matches_quote_preview_engine(client):
    est = client.post(
        "/v1/public/estimate",
        json={"pickup_postal": "M5V", "dropoff_postal": "M4W", "vehicle_class": "sedan_suv"},
    ).json()
    a, b = fsa_centroid("M5V"), fsa_centroid("M4W")
    prev = client.post(
        "/v1/quotes/preview",
        json={
            "pickup": {"formatted": "M5V, Ontario, Canada", "postal": "M5V", "lat": a[1], "lng": a[2]},
            "dropoff": {"formatted": "M4W, Ontario, Canada", "postal": "M4W", "lat": b[1], "lng": b[2]},
            "vehicle_class": "sedan_suv",
            "booking_mode": "vehicle",
            "scheduled_at": "2026-10-12T15:00:00Z",
        },
    ).json()
    assert est["amount_cents"] == prev["amount_cents"]


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"pickup_postal": "V6B", "dropoff_postal": "M5V"}, "pickup_outside_service_area"),
        ({"pickup_postal": "M5V", "dropoff_postal": "H2X"}, "dropoff_outside_service_area"),
        ({"pickup_postal": "M5V", "dropoff_postal": "M4W", "vehicle_class": "sprinter_van"}, "vehicle_class_not_available"),
    ],
)
def test_estimate_rejects_bad_input(client, payload, detail):
    res = client.post("/v1/public/estimate", json=payload)
    assert res.status_code == 400
    assert res.json()["detail"] == detail


def test_estimate_is_rate_limited(client, monkeypatch):
    seen = {}

    def _limited(key, limit, **_):
        seen["key"], seen["limit"] = key, limit
        return (False, limit + 1, None)

    monkeypatch.setattr(rl, "check_fixed_window", _limited)
    res = client.post(
        "/v1/public/estimate",
        json={"pickup_postal": "M5V", "dropoff_postal": "M4W"},
        headers={"X-Forwarded-For": "203.0.113.9"},
    )
    assert res.status_code == 429
    assert res.headers.get("Retry-After") == "60"
    assert "estimate:ip:203.0.113.9" in seen["key"] and seen["limit"] == 12


def test_rate_limit_redis_down_fails_open_locally_closed_elsewhere(monkeypatch):
    monkeypatch.setattr(rl, "check_fixed_window", lambda key, limit, **_: (True, 0, "redis down"))
    req = SimpleNamespace(headers={}, client=SimpleNamespace(host="198.51.100.1"))
    rl.enforce_public_limit(req, bucket="estimate", limit=5, app_env="local")
    with pytest.raises(HTTPException) as exc:
        rl.enforce_public_limit(req, bucket="estimate", limit=5, app_env="production")
    assert exc.value.status_code == 503


# ------------------------------------------------------------------ leads


def test_calculator_lead_lands_in_crm_with_attribution_and_no_marketing_consent(client, db):
    body = _lead_body()
    res = client.post("/v1/public/calculator-leads", json=body)
    assert res.status_code == 202, res.text
    assert res.json() == {"status": "received"}
    lead = _lead_by_email(db, body["email"])
    assert lead is not None
    assert lead.source == "website_calculator" and lead.channel == "website"
    assert lead.industry == "pharmacy"
    assert lead.estimated_deliveries_per_month == 60
    assert lead.service_area == "M5V"
    assert lead.preferred_vehicle == "sedan_suv"
    cf = lead.custom_fields
    assert cf["utm_source"] == "google" and cf["utm_campaign"] == "pharmacy-gta"
    assert cf["pickup_fsa"] == "M5V" and cf["dropoff_fsa"] == "L5T" and cf["estimate_cents"] == 9640
    assert lead.consent["marketing"] is False
    assert lead.consent["source"] == "website_calculator"
    assert "calculator" in (lead.tags or [])


def test_calculator_lead_records_separate_casl_opt_in(client, db):
    body = _lead_body(marketing_consent=True)
    assert client.post("/v1/public/calculator-leads", json=body).status_code == 202
    lead = _lead_by_email(db, body["email"])
    assert lead.consent["marketing"] is True
    assert lead.consent["legal_basis"] == "consent"
    assert lead.consent["captured_at"] and lead.consent["text_version"]


@pytest.mark.parametrize("over", [{"website": "http://spam.example"}, {"form_elapsed_ms": 300}])
def test_spam_signals_get_same_answer_but_create_nothing(client, db, over):
    body = _lead_body(**over)
    res = client.post("/v1/public/calculator-leads", json=body)
    assert res.status_code == 202 and res.json() == {"status": "received"}
    assert _lead_by_email(db, body["email"]) is None


@pytest.mark.parametrize(
    ("over", "detail"),
    [
        ({"email": "not-an-email"}, "email_invalid"),
        ({"phone": "555-0100x"}, "phone_invalid"),
        ({"industry": "casino"}, "industry_invalid"),
        ({"monthly_volume": "lots"}, "monthly_volume_invalid"),
    ],
)
def test_calculator_lead_validation(client, over, detail):
    res = client.post("/v1/public/calculator-leads", json=_lead_body(**over))
    assert res.status_code == 422
    assert res.json()["detail"] == detail


def test_calculator_lead_requires_ingest_key_when_configured(monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("PUBLIC_INGEST_API_KEY", "test-ingest-key")
    get_settings.cache_clear()
    try:
        c = TestClient(create_app())
        res = c.post("/v1/public/calculator-leads", json=_lead_body(), headers={"X-Ingest-Key": "nope"})
        assert res.status_code == 401
    finally:
        get_settings.cache_clear()


def test_lead_rate_limit_applies(client, monkeypatch):
    monkeypatch.setattr(rl, "check_fixed_window", lambda key, limit, **_: (False, limit + 1, None))
    res = client.post("/v1/public/calculator-leads", json=_lead_body())
    assert res.status_code == 429


def test_lead_ingest_outreach_default_unchanged():
    from porterchain_api.collaboration_engine.lead_ingest_service import CanonicalLeadEvent

    evt = CanonicalLeadEvent(channel="website", source="website_contact", provider="x", external_event_id="1", company_name="A")
    assert evt.skip_outreach is False


# ------------------------------------------------------------------ admin view


def test_lead_attribution_summary_groups_by_source_industry_fsa(client, db):
    body = _lead_body(industry="construction", pickup_fsa="L4K", utm_source="newsletter-x")
    assert client.post("/v1/public/calculator-leads", json=body).status_code == 202
    out = lead_attribution_summary(db, days=1)
    keys = lambda rows: {r["key"] for r in rows}  # noqa: E731
    assert "website_calculator" in keys(out["by_source"])
    assert "construction" in keys(out["by_industry"])
    assert "L4K" in keys(out["by_fsa"])
    assert "newsletter-x" in keys(out["by_utm_source"])
    assert out["calculator_leads"] >= 1 and out["total"] >= out["calculator_leads"]


def test_admin_attribution_route_requires_crm_read(monkeypatch):
    from porterchain_api.routers.admin import marketing_leads

    # Local dev staff context needs the dev bypass explicitly (CI has no .env).
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("CLERK_DEV_BYPASS", "true")
    get_settings.cache_clear()
    client = TestClient(create_app())
    res = client.get("/v1/admin/marketing/lead-attribution?days=7")  # local dev staff context
    assert res.status_code == 200 and res.json()["window_days"] == 7
    asked = []

    def _deny(ctx, module):
        asked.append(module)
        raise HTTPException(status_code=403, detail="module_forbidden")

    monkeypatch.setattr(marketing_leads, "require_module", _deny)
    assert client.get("/v1/admin/marketing/lead-attribution").status_code == 403
    assert asked == ["crm_read"]


# ------------------------------------------------------------------ signup attribution


def test_signup_attribution_is_cleaned_and_first_touch_only():
    clean = clean_signup_attribution(
        {"utm_source": " linkedin ", "utm_campaign": "x" * 300, "password": "nope", "pc_vid": "vid-1"}
    )
    assert clean == {"utm_source": "linkedin", "utm_campaign": "x" * 120, "pc_vid": "vid-1"}
    merchant = SimpleNamespace(profile={"vertical": "construction"})
    assert stamp_signup_attribution(merchant, {"utm_source": "google"}) is True
    assert merchant.profile["signup_attribution"]["utm_source"] == "google"
    assert merchant.profile["vertical"] == "construction"
    assert stamp_signup_attribution(merchant, {"utm_source": "bing"}) is False
    assert merchant.profile["signup_attribution"]["utm_source"] == "google"
    assert stamp_signup_attribution(SimpleNamespace(profile={}), {"evil": "x"}) is False


def test_vertical_request_accepts_attribution():
    from porterchain_api.schemas_auth import MerchantVerticalRequest

    req = MerchantVerticalRequest(vertical="construction", attribution={"utm_source": "google"})
    assert req.attribution == {"utm_source": "google"}
    assert MerchantVerticalRequest(vertical="construction").attribution is None
