"""Launch blockers: mock paths are hard-off outside local, billing is Interac-only,
and Interac mark-paid requires the invoice payment reference."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from porterchain_api.admin_engine.ar_payments import check_interac_reference
from porterchain_api.routers import quotes
from porterchain_api.routers.driver import verification
from porterchain_api.routers.merchant import billing
from porterchain_api.schemas_booking import CheckoutMockCompleteRequest

PROD = SimpleNamespace(app_env="production", allow_stripe_mock=True)  # even if mis-flagged
STAGING = SimpleNamespace(app_env="staging", allow_stripe_mock=True)


@pytest.mark.parametrize("cfg", [PROD, STAGING])
def test_driver_mock_identity_is_404_outside_local(cfg):
    with pytest.raises(HTTPException) as exc:
        verification.mock_complete_identity_verification(
            verification.MockIdentityCompleteRequest(), ctx=None, db=None, settings=cfg
        )
    assert exc.value.status_code == 404


@pytest.mark.parametrize("cfg", [PROD, STAGING])
def test_driver_mock_background_is_404_outside_local(cfg):
    with pytest.raises(HTTPException) as exc:
        verification.mock_complete_background_check(
            verification.MockBackgroundCompleteRequest(), ctx=None, db=None, settings=cfg
        )
    assert exc.value.status_code == 404


def test_driver_mock_guard_allows_local():
    verification._require_local_mock(SimpleNamespace(app_env="local"))


@pytest.mark.parametrize("cfg", [PROD, STAGING])
def test_booking_mock_complete_is_404_outside_local(cfg):
    with pytest.raises(HTTPException) as exc:
        quotes.mock_complete_checkout(CheckoutMockCompleteRequest(quote_id="q"), db=None, settings=cfg)
    assert exc.value.status_code == 404


def test_stripe_connect_cod_routes_are_removed():
    """No cash on delivery: merchant COD status/connect/enable routes no longer exist."""
    paths = {getattr(r, "path", "") for r in billing.router.routes}
    assert not any("cod" in p.split("/") for p in paths)


INV = SimpleNamespace(payment_reference="PC7K2M9Q")


def test_interac_reference_blank_uses_invoice_reference():
    assert check_interac_reference(INV, None) == "PC7K2M9Q"
    assert check_interac_reference(INV, "  ") == "PC7K2M9Q"


def test_interac_reference_matches_loosely():
    assert check_interac_reference(INV, "e-transfer msg: pc7k-2m9q thanks")


def test_interac_reference_mismatch_rejected_unless_overridden():
    with pytest.raises(ValueError, match="payment_reference_mismatch"):
        check_interac_reference(INV, "PC0000000")
    assert check_interac_reference(INV, "PC0000000", allow_mismatch=True) == "PC0000000"


def test_interac_reference_no_invoice_reference_passthrough():
    assert check_interac_reference(SimpleNamespace(payment_reference=None), "ABC") == "ABC"


def test_driver_cod_checkout_is_removed():
    """No cash on delivery: the COD service and driver Payment Link route are gone."""
    import importlib.util

    from porterchain_api.routers.driver import jobs as driver_jobs

    assert importlib.util.find_spec("porterchain_api.billing_engine.stripe_cod_service") is None
    paths = {getattr(r, "path", "") for r in driver_jobs.router.routes}
    assert not any("cod-checkout" in p for p in paths)


def test_admin_mark_paid_enforces_reference(monkeypatch):
    from porterchain_api.admin_engine import ar_payments as ref

    monkeypatch.setattr(ref, "enforce_reference", lambda *a: (_ for _ in ()).throw(ValueError("payment_reference_mismatch")))
    body = SimpleNamespace(method="interac", reference="X", allow_reference_mismatch=False, amount_cents=None, paid_at=None)
    with pytest.raises(ValueError, match="payment_reference_mismatch"):
        ref.record_admin_payment(None, None, "inv", body)


def test_enforce_reference_skips_non_interac():
    from porterchain_api.admin_engine.ar_payments import enforce_reference

    assert enforce_reference(None, "inv", "cheque", "CHQ-1", False) == "CHQ-1"
