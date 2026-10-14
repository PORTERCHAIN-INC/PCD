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


def test_stripe_connect_cod_is_retired(monkeypatch):
    monkeypatch.setattr(billing, "require_module", lambda ctx, m: None)
    status = billing.billing_cod_status(ctx=None)
    assert status["interac_only"] is True and status["connect_ready"] is False
    for call in (lambda: billing.billing_cod_connect(ctx=None), lambda: billing.billing_cod_enable({"enabled": True}, ctx=None)):
        with pytest.raises(HTTPException) as exc:
            call()
        assert exc.value.status_code == 410


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


def test_driver_cod_checkout_is_retired():
    from porterchain_api.billing_engine.stripe_cod_service import StripeCodService

    with pytest.raises(PermissionError, match="interac"):
        StripeCodService().issue_cod_checkout_for_order(None, None, SimpleNamespace(merchant_id="m"))


def test_admin_mark_paid_enforces_reference(monkeypatch):
    from porterchain_api.admin_engine import ar_payments as ref

    monkeypatch.setattr(ref, "enforce_reference", lambda *a: (_ for _ in ()).throw(ValueError("payment_reference_mismatch")))
    body = SimpleNamespace(method="interac", reference="X", allow_reference_mismatch=False, amount_cents=None, paid_at=None)
    with pytest.raises(ValueError, match="payment_reference_mismatch"):
        ref.record_admin_payment(None, None, "inv", body)


def test_enforce_reference_skips_non_interac():
    from porterchain_api.admin_engine.ar_payments import enforce_reference

    assert enforce_reference(None, "inv", "cheque", "CHQ-1", False) == "CHQ-1"
