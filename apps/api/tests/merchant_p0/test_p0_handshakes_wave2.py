"""Wave-2 merchant handshakes: Clerk gate, Fleetbase enqueue, Shopify OAuth, Mailpit SMTP.

Extends merchant_p0 — does not re-run shopify_phase4 HMAC or booking_sync_phase2 wholesale;
those stay the deep suites. This pack wires SSOT IDs for the merchant matrix wave.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest
from porterchain_shared.config.settings import PlatformSettings
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.diagnostics_probes import DiagnosticsProbesMixin
from porterchain_api.auth.merchant import portal_access_denied
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.booking_validation import (
    BookingValidationError,
    MerchantSyncService,
)
from porterchain_api.merchant_models import Merchant

from . import REPO_ROOT

INFRA = REPO_ROOT / "infrastructure"


@pytest.fixture(autouse=True)
def _clear_clerk_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("CLERK_"):
            monkeypatch.delenv(key, raising=False)


def _merchant(db: Session, *, status: str = MerchantStatus.ACTIVE.value) -> Merchant:
    suffix = uuid4().hex[:8]
    row = Merchant(
        company_name=f"HS Co {suffix}",
        email=f"hs-{suffix}@test.local",
        status=status,
        payment_terms="NET_30",
        profile={},
    )
    db.add(row)
    db.flush()
    return row


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-CLERK-002")
def test_hs_clerk_portal_denies_suspended_and_closed(db: Session) -> None:
    """Clerk seat alone is not enough — merchant status gates portal."""
    assert portal_access_denied(_merchant(db, status=MerchantStatus.SUSPENDED.value)) == "merchant_suspended"
    assert portal_access_denied(_merchant(db, status=MerchantStatus.CLOSED.value)) == "merchant_closed"
    assert portal_access_denied(_merchant(db, status=MerchantStatus.PENDING.value)) == "merchant_not_active"
    assert portal_access_denied(_merchant(db, status=MerchantStatus.ACTIVE.value)) is None
    assert portal_access_denied(_merchant(db, status=MerchantStatus.ONBOARDING.value)) is None


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-FB-VALIDATE")
def test_hs_fb_merchant_sync_rejects_suspended(db: Session) -> None:
    merchant = _merchant(db, status=MerchantStatus.SUSPENDED.value)
    with pytest.raises(BookingValidationError, match="merchant_suspended"):
        MerchantSyncService().validate_booking(db, merchant, amount_cents=2500)


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-SHOP-001")
def test_hs_shop_install_url_oauth_shape() -> None:
    settings = Settings(
        _env_file=None,
        jwt_secret="a" * 32,
        shopify_api_key="shp_key_test",
        shopify_api_secret="shp_secret_test",
        shopify_api_scopes="read_orders,write_shipping",
        porterchain_api_url="http://localhost:8001",
    )
    url = shopify.install_url("demo-shop.myshopify.com", settings, merchant_id="m-1")
    assert url.startswith("https://demo-shop.myshopify.com/admin/oauth/authorize?")
    assert "client_id=shp_key_test" in url
    assert "state=" in url
    with pytest.raises(ValueError, match="shopify_oauth_not_configured"):
        shopify.install_url(
            "demo-shop.myshopify.com",
            Settings(_env_file=None, jwt_secret="a" * 32, shopify_api_key="", shopify_api_secret=""),
            merchant_id=None,
        )


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-SHOP-PUBLIC")
def test_hs_shop_public_webhook_router_requires_hmac() -> None:
    """Public Shopify ingress keeps HMAC in shopify_service — router must pass header through."""
    path = REPO_ROOT / "apps/api/src/porterchain_api/routers/shopify.py"
    text = path.read_text(encoding="utf-8")
    assert "X-Shopify-Hmac" in text or "hmac" in text.lower()
    assert "shopify_service" in text or "as shopify" in text
    # No Fleetbase HTTP from the public Shopify router.
    assert "httpx" not in text
    assert "fleetbase" not in text.lower() or "BookingValidationError" in text


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-MAIL-001")
def test_hs_mail_local_transport_is_smtp_for_mailpit() -> None:
    """Local API uses SMTP → Mailpit; prod may flip to ZeptoMail HTTPS."""
    local = PlatformSettings.model_construct(
        app_env="local",
        smtp_host="mailpit",
        mail_transport="auto",
    )
    assert local.resolve_mail_transport() == "smtp"
    prod = PlatformSettings.model_construct(
        app_env="production",
        smtp_host="smtp.zeptomail.ca",
        mail_transport="auto",
    )
    assert prod.resolve_mail_transport() in {"https", "smtp"}


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-MAIL-PROBE")
def test_hs_mail_probe_labels_mailpit_host() -> None:
    class _Probe(DiagnosticsProbesMixin):
        pass

    probe = _Probe()
    platform = SimpleNamespace(
        smtp_host="mailpit",
        smtp_port=1025,
        smtp_from="ops@porterchain.test",
        smtp_user="",
    )
    with patch(
        "porterchain_api.admin_engine.diagnostics_probes._probe_http",
        return_value=("healthy", 12.0, None),
    ):
        result = probe._probe_email(platform)
    assert result["status"] == "healthy"
    assert result["details"]["mode"] == "mailpit"


@pytest.mark.merchant_p0
@pytest.mark.tc_id("HS-MAIL-COMPOSE")
def test_hs_mail_compose_pins_mailpit_not_mailhog() -> None:
    compose_blobs: list[str] = []
    for path in INFRA.rglob("*compose*.yml"):
        compose_blobs.append(path.read_text(encoding="utf-8", errors="ignore").lower())
    blob = "\n".join(compose_blobs)
    assert "mailpit" in blob or "axllent/mailpit" in blob
    assert "mailhog" not in blob
