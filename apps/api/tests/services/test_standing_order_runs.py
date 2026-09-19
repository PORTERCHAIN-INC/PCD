"""Recurring standing orders — English last_error and skip inactive merchants."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.standing_order_service import (
    MerchantStandingOrderService,
    standing_error_message,
)
from porterchain_api.merchant_models import MerchantBookingTemplate, StandingOrder


def _template(db, merchant_id: str, name: str = "Weekly King") -> MerchantBookingTemplate:
    row = MerchantBookingTemplate(
        merchant_id=merchant_id,
        name=name,
        payload={"vehicle_class": "cargoVan"},
    )
    db.add(row)
    db.flush()
    return row


def test_missing_template_sets_english_last_error(db, settings, merchant_ctx, monkeypatch) -> None:
    template = _template(db, merchant_ctx.merchant.id)
    standing = StandingOrder(
        merchant_id=merchant_ctx.merchant.id,
        booking_template_id=template.id,
        recurrence_rule="weekly",
        next_run_at=datetime.now(UTC) - timedelta(minutes=5),
        is_active=True,
    )
    db.add(standing)
    db.commit()
    monkeypatch.setattr(MerchantStandingOrderService, "_load_template", lambda self, db, tid: None)
    result = MerchantStandingOrderService().run_due_orders(db, settings)
    db.refresh(standing)
    assert result["skipped"] >= 1
    assert standing.is_active is False
    assert standing.last_error == standing_error_message("template_not_found")
    assert "deleted" in standing.last_error.lower()


def test_inactive_merchant_skips_with_english_last_error(db, settings, merchant_ctx) -> None:
    template = _template(db, merchant_ctx.merchant.id)
    standing = StandingOrder(
        merchant_id=merchant_ctx.merchant.id,
        booking_template_id=template.id,
        recurrence_rule="weekly",
        next_run_at=datetime.now(UTC) - timedelta(minutes=5),
        is_active=True,
    )
    db.add(standing)
    merchant_ctx.merchant.status = MerchantStatus.SUSPENDED.value
    db.commit()
    result = MerchantStandingOrderService().run_due_orders(db, settings)
    db.refresh(standing)
    assert result["skipped"] == 1
    assert result["created"] == 0
    assert standing.is_active is True
    assert standing.last_error == standing_error_message("merchant_not_active")
    assert "reactivates" in standing.last_error.lower()


def test_serialize_includes_last_error_and_template_name(db, merchant_ctx) -> None:
    template = _template(db, merchant_ctx.merchant.id, name="Dock A weekly")
    standing = StandingOrder(
        merchant_id=merchant_ctx.merchant.id,
        booking_template_id=template.id,
        recurrence_rule="weekly",
        next_run_at=datetime.now(UTC),
        last_error=standing_error_message("no_active_seat"),
        is_active=True,
    )
    db.add(standing)
    db.commit()
    rows = MerchantStandingOrderService().list_serialized(db, merchant_ctx.merchant.id)
    assert len(rows) == 1
    assert rows[0]["last_error"] == standing_error_message("no_active_seat")
    assert rows[0]["template_name"] == "Dock A weekly"


def test_create_standing_order_rejects_inactive_merchant(db, merchant_ctx) -> None:
    template = _template(db, merchant_ctx.merchant.id)
    merchant_ctx.merchant.status = MerchantStatus.CLOSED.value
    db.commit()
    with pytest.raises(ValueError, match="merchant_not_active"):
        MerchantStandingOrderService().create_standing_order(
            db,
            merchant_ctx,
            booking_template_id=template.id,
            recurrence_rule="weekly",
        )
