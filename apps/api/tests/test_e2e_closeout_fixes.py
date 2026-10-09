"""Close-out fixes from local E2E: OTP POD path, dummy Stripe ids, wallet cache, jobs schema."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from porterchain_api.billing_engine.stripe_cod_service import StripeCodService
from porterchain_api.domain.states import CodStatus, OrderState, can_transition_order
from porterchain_api.driver_engine.wallet_ledger import record_transaction
from porterchain_api.schemas_driver import DriverJobsListResponse, DriverNextStop
from porterchain_api.services.stripe_service import is_dummy_stripe_id
from porterchain_driver.pod import ProofOfDeliveryService


def test_dummy_stripe_ids() -> None:
    assert is_dummy_stripe_id("cus_local_priya") is True
    assert is_dummy_stripe_id("acct_local_mapleleaf") is True
    assert is_dummy_stripe_id("acct_mock_m1") is True
    assert is_dummy_stripe_id("cus_123456") is False
    assert is_dummy_stripe_id("acct_1A2B3C") is False
    assert is_dummy_stripe_id("") is False
    assert is_dummy_stripe_id(None) is False


def test_ensure_stripe_customer_skips_placeholder_and_creates(monkeypatch: pytest.MonkeyPatch) -> None:
    from porterchain_api.services.stripe_service import ensure_stripe_customer

    created = SimpleNamespace(id="cus_test_live")
    monkeypatch.setattr(
        "porterchain_api.services.stripe_service.stripe_sdk.configure", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "porterchain_api.services.stripe_service.stripe_sdk.create_customer",
        lambda **_k: created,
    )
    customer = SimpleNamespace(
        id="cust-1",
        email="customer@porterchain.com",
        phone=None,
        stripe_customer_id="cus_local_priya",
    )
    out = ensure_stripe_customer(SimpleNamespace(stripe_secret="sk_test_x"), customer)
    assert out == "cus_test_live"
    assert customer.stripe_customer_id == "cus_test_live"


def test_otp_lifecycle_allows_destination_then_delivered_then_pod() -> None:
    assert can_transition_order(OrderState.AT_DESTINATION, OrderState.DELIVERED) is True
    assert can_transition_order(OrderState.DELIVERED, OrderState.POD_COMPLETED) is True
    assert can_transition_order(OrderState.AT_DESTINATION, OrderState.POD_COMPLETED) is False


def test_complete_pod_from_at_destination_walks_delivered(monkeypatch: pytest.MonkeyPatch) -> None:
    order = SimpleNamespace(
        id="o1",
        state=OrderState.AT_DESTINATION.value,
        assigned_driver_id="d1",
        fleetbase_order_id=None,
        compliance_metadata={"otp_required": True},
    )
    calls: list[OrderState] = []

    def fake_transition(_db, _order, to_state, **_kwargs):
        calls.append(to_state)
        order.state = to_state.value
        return order

    monkeypatch.setattr("porterchain_driver.pod._order_for_stop", lambda *_a, **_k: order)
    monkeypatch.setattr(
        "porterchain_api.booking_engine.compliance_metadata.otp_required_at_delivery",
        lambda _meta: True,
    )
    monkeypatch.setattr(
        "porterchain_api.booking_engine.order_transitions.transition_order_state",
        fake_transition,
    )
    monkeypatch.setattr(ProofOfDeliveryService, "verify_otp", lambda *_a, **_k: True)
    # Proof (photo/signature) already captured and driver on shift — POD gate satisfied.
    monkeypatch.setattr("porterchain_driver.pod_policy.missing_for", lambda *_a, **_k: [])
    monkeypatch.setattr("porterchain_driver.pod_policy.assert_on_duty", lambda *_a, **_k: None)

    result = ProofOfDeliveryService().complete_pod(
        MagicMock(), SimpleNamespace(id="d1"), "o1-dropoff", otp="123456"
    )
    assert result.success is True
    assert calls == [OrderState.DELIVERED, OrderState.POD_COMPLETED]
    assert order.state == OrderState.POD_COMPLETED.value


def test_complete_pod_already_completed_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    order = SimpleNamespace(
        id="o1",
        state=OrderState.POD_COMPLETED.value,
        assigned_driver_id="d1",
        fleetbase_order_id=None,
        compliance_metadata={},
    )
    calls: list[OrderState] = []

    def fake_transition(_db, _order, to_state, **_kwargs):
        calls.append(to_state)
        order.state = to_state.value
        return order

    monkeypatch.setattr("porterchain_driver.pod._order_for_stop", lambda *_a, **_k: order)
    monkeypatch.setattr(
        "porterchain_api.booking_engine.compliance_metadata.otp_required_at_delivery",
        lambda _meta: False,
    )
    monkeypatch.setattr(
        "porterchain_api.booking_engine.order_transitions.transition_order_state",
        fake_transition,
    )

    result = ProofOfDeliveryService().complete_pod(
        MagicMock(), SimpleNamespace(id="d1"), "o1-dropoff"
    )
    assert result.success is True
    assert calls == []


def test_cod_placeholder_destination_mocks_even_with_stripe_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    settings = SimpleNamespace(
        allow_stripe_mock=False,
        stripe_secret="sk_test_dummy",
        stripe_cod_platform_fee_bps=500,
        driver_portal_url="http://localhost:3003",
    )
    merchant = SimpleNamespace(
        id="m1",
        cod_enabled=True,
        stripe_connect_account_id="acct_local_mapleleaf",
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
    called = {"stripe": False}

    def _fail_real(*_a, **_k):
        called["stripe"] = True
        raise AssertionError("must not call live Connect for dummy acct")

    monkeypatch.setattr(
        "porterchain_api.billing_engine.stripe_cod_service.create_cod_checkout_session",
        _fail_real,
    )
    out = StripeCodService().issue_cod_checkout(db, settings, order, merchant)
    assert out["mock"] is True
    assert called["stripe"] is False
    assert order.cod_status == CodStatus.LINK_ISSUED.value


def test_record_transaction_syncs_driver_wallet_cache() -> None:
    driver = SimpleNamespace(id="d1", wallet_balance_cents=23350)
    db = MagicMock()
    db.query.return_value.filter.return_value.one_or_none.return_value = driver
    row = record_transaction(
        db,
        driver_id="d1",
        tx_type="payout",
        amount_cents=-12650,
        balance_after_cents=10700,
    )
    assert driver.wallet_balance_cents == 10700
    db.add.assert_called_once()
    assert row.balance_after_cents == 10700


def test_driver_jobs_schema_accepts_next_stop_source_and_null_sequence() -> None:
    stop = DriverNextStop(
        stop_id="o1-dropoff",
        stop_type="dropoff",
        order_id="o1",
        sequence=None,
        source="haversine",
    )
    payload = DriverJobsListResponse(
        next_stop=stop,
        route_metrics={
            "distance_km": 12.4,
            "duration_minutes": 28,
            "estimated_fuel_cents": 400,
            "estimated_fuel_liters": 1.2,
            "source": "last_optimize",
        },
    )
    assert payload.next_stop is not None
    assert payload.next_stop.source == "haversine"
    assert payload.next_stop.sequence is None
    assert payload.route_metrics is not None
    assert payload.route_metrics.source == "last_optimize"
