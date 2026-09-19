"""COD / Stripe Connect — mock-path unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.billing_engine.stripe_cod_service import StripeCodService
from porterchain_api.domain.states import CodStatus


@pytest.fixture
def settings_mock():
    return SimpleNamespace(
        allow_stripe_mock=True,
        stripe_secret="",
        stripe_cod_platform_fee_bps=500,
        stripe_connect_refresh_url="http://localhost:3001/billing",
        stripe_connect_return_url="http://localhost:3001/billing?connect=return",
        driver_portal_url="http://localhost:3003",
    )


def test_connect_account_link_mock(settings_mock):
    db = MagicMock()
    merchant = SimpleNamespace(id="m1", email="m@example.com", stripe_connect_account_id=None)
    out = StripeCodService().create_connect_account_link(db, settings_mock, merchant)
    assert out["account_id"].startswith("acct_mock_")
    assert "url" in out
    db.commit.assert_called()


def test_issue_cod_checkout_mock(settings_mock, monkeypatch):
    db = MagicMock()
    merchant = SimpleNamespace(
        id="m1",
        cod_enabled=True,
        stripe_connect_account_id="acct_mock_m1",
    )
    order = SimpleNamespace(
        id="o1",
        tracking_number="PC123",
        order_number="ORD1",
        currency="cad",
        cod_amount_cents=45000,
        cod_status=CodStatus.PENDING_COLLECTION.value,
        cod_stripe_session_id=None,
    )
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.scan_gate_service.ScanGateService.assert_cod_scans",
        lambda self, db, order: None,
    )
    out = StripeCodService().issue_cod_checkout(db, settings_mock, order, merchant)
    assert out["mock"] is True
    assert out["amount_cents"] == 45000
    assert order.cod_status == CodStatus.LINK_ISSUED.value
    assert order.cod_stripe_session_id


def test_issue_cod_requires_enabled(settings_mock):
    db = MagicMock()
    merchant = SimpleNamespace(id="m1", cod_enabled=False, stripe_connect_account_id="acct_x")
    order = SimpleNamespace(
        id="o1",
        cod_amount_cents=100,
        cod_status=None,
        currency="cad",
        tracking_number="T",
        order_number="O",
    )
    with pytest.raises(ValueError, match="cod_not_enabled"):
        StripeCodService().issue_cod_checkout(db, settings_mock, order, merchant)
