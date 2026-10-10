"""Wave 4 Batch F: seat roles, scoring empty class, lead upsert, rebook vehicle, ref retry."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.control_tower.scoring import hard_filter_driver
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.team_service import assert_not_last_owner, ensure_merchant_seat


def test_ensure_seat_rejects_invalid_role() -> None:
    db = MagicMock()
    with pytest.raises(ValueError, match="invalid_team_role"):
        ensure_merchant_seat(db, merchant_id="m1", email="a@b.com", role="superuser")


def test_last_owner_cannot_be_removed() -> None:
    owner = SimpleNamespace(
        id="u1",
        is_active=True,
        role=MerchantRole.OWNER.value,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [owner]
    with pytest.raises(ValueError, match="last_owner_required"):
        assert_not_last_owner(db, merchant_id="m1", user=owner, next_role=None)


def test_last_owner_can_stay_owner() -> None:
    owner = SimpleNamespace(id="u1", is_active=True, role=MerchantRole.OWNER.value)
    db = MagicMock()
    assert_not_last_owner(db, merchant_id="m1", user=owner, next_role=MerchantRole.OWNER.value)


def test_hard_filter_empty_vehicles_when_class_required() -> None:
    d = SimpleNamespace(
        license_verified=True,
        insurance_verified=True,
        background_check_status="passed",
        medical_transport_certified=False,
        documents={},
        full_name="A",
        id="1",
    )
    reason = hard_filter_driver(
        d,
        medical_required=False,
        required_class="cargoVan",
        classes=set(),
        skills_needed=[],
    )
    assert reason and "No vehicles registered" in reason


def test_create_lead_upserts_by_quote() -> None:
    from porterchain_api.booking_engine.customer_service import CustomerService

    existing = SimpleNamespace(
        id="lead-1",
        quote_id="q1",
        email="old@x.com",
        phone=None,
        customer_id="c1",
        stage="booking_started",
        crm_lead_id="crm-already",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    out = CustomerService().create_lead(
        db, email="new@x.com", phone="1", quote_id="q1", customer_id="c1"
    )
    assert out is existing
    assert existing.email == "new@x.com"
    db.commit.assert_called()


def test_rebook_uses_quote_vehicle() -> None:
    from porterchain_api.booking_engine.customer_service import CustomerService

    order = SimpleNamespace(
        id="o1",
        quote_id="q1",
        pickup={"street": "1 Main"},
        dropoff={},
        tracking_number="T1",
    )
    quote = SimpleNamespace(vehicle_class="highRoof")
    db = MagicMock()
    db.get.return_value = quote

    with patch(
        "porterchain_api.booking_engine.repositories.order_repository.OrderRepository.get_for_customer",
        return_value=order,
    ):
        out = CustomerService().rebook_payload(db, "c1", "o1")
    assert out["vehicle_class"] == "highRoof"


def test_assign_customer_reference_retries_collision() -> None:
    from porterchain_api.booking_engine.confirmation_service import BookingConfirmationService

    customer = SimpleNamespace(id="c1", customer_reference=None)
    db = MagicMock()
    # First probe hits, second free
    db.query.return_value.filter.return_value.first.side_effect = [("taken",), None]
    nested = MagicMock()
    nested.__enter__ = MagicMock(return_value=None)
    nested.__exit__ = MagicMock(return_value=False)
    db.begin_nested.return_value = nested

    BookingConfirmationService._assign_customer_reference(db, customer)
    assert customer.customer_reference and customer.customer_reference.startswith("CUST-")


def test_support_idempotency_returns_prior() -> None:
    from porterchain_api.booking_engine.customer_service import CustomerService

    prior = SimpleNamespace(
        id="t1",
        ticket_data={"idempotency_key": "k-9"},
        customer_id="c1",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        prior
    ]
    out = CustomerService().create_support_ticket(
        db,
        customer_id="c1",
        subject="Help",
        idempotency_key="k-9",
    )
    assert out is prior
