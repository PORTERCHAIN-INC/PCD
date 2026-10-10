"""Merchant webhook delivery SLO tests (§5.3.7)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.webhook_delivery_health import (
    MERCHANT_WEBHOOK_DELIVERY_SLO_TARGET_PCT,
    assess_merchant_webhook_delivery,
    build_merchant_webhook_delivery_alerts,
)
from porterchain_api.merchant_models import (
    Merchant,
    MerchantWebhook,
    MerchantWebhookDelivery,
)


def _seed_delivery(
    db: Session,
    *,
    merchant_id: str,
    webhook_id: str,
    order_id: str,
    success: bool,
    attempt: int = 1,
) -> None:
    db.add(
        MerchantWebhookDelivery(
            merchant_id=merchant_id,
            webhook_id=webhook_id,
            event_type="order.created",
            request_body={"order_id": order_id, "event_type": "order.created"},
            response_status=200 if success else 500,
            attempt=attempt,
            success=success,
            duration_ms=12,
        )
    )


def test_assess_merchant_webhook_delivery_empty(db: Session) -> None:
    result = assess_merchant_webhook_delivery(db, merchant_id=str(uuid4()))
    assert result["meets_slo"] is True
    assert result["success_pct"] == 100.0
    assert result["total_deliveries"] == 0


def test_assess_merchant_webhook_delivery_meets_slo(db: Session) -> None:
    merchant = Merchant(
        id=str(uuid4()),
        company_name="Webhook SLO Merchant",
        email="webhook-slo@test.porterchain.com",
        status="active",
    )
    webhook = MerchantWebhook(
        id=str(uuid4()),
        merchant_id=merchant.id,
        url="https://example.com/hook",
        events=["order.*"],
        secret_hash="hash",
        encrypted_signing_secret="enc",
    )
    db.add_all([merchant, webhook])
    db.flush()

    for idx in range(10):
        _seed_delivery(
            db,
            merchant_id=merchant.id,
            webhook_id=webhook.id,
            order_id=f"ord_{idx}",
            success=True,
        )
    db.commit()

    result = assess_merchant_webhook_delivery(db, merchant_id=merchant.id)
    assert result["total_deliveries"] == 10
    assert result["success_pct"] == 100.0
    assert result["meets_slo"] is True
    assert result["alerts"] == []


def test_assess_merchant_webhook_delivery_below_slo(db: Session) -> None:
    merchant = Merchant(
        id=str(uuid4()),
        company_name="Webhook Fail Merchant",
        email="webhook-fail@test.porterchain.com",
        status="active",
    )
    webhook = MerchantWebhook(
        id=str(uuid4()),
        merchant_id=merchant.id,
        url="https://example.com/hook",
        events=["order.*"],
        secret_hash="hash",
        encrypted_signing_secret="enc",
    )
    db.add_all([merchant, webhook])
    db.flush()

    _seed_delivery(db, merchant_id=merchant.id, webhook_id=webhook.id, order_id="ord_ok", success=True)
    _seed_delivery(db, merchant_id=merchant.id, webhook_id=webhook.id, order_id="ord_bad", success=False, attempt=3)
    db.commit()

    result = assess_merchant_webhook_delivery(db, merchant_id=merchant.id)
    assert result["total_deliveries"] == 2
    assert result["success_pct"] == 50.0
    assert result["meets_slo"] is False
    codes = {alert["code"] for alert in build_merchant_webhook_delivery_alerts(result)}
    assert "merchant_webhook_delivery_below_slo" in codes
    assert result["slo_target_pct"] == MERCHANT_WEBHOOK_DELIVERY_SLO_TARGET_PCT


def test_assess_merchant_webhook_delivery_uses_final_attempt(db: Session) -> None:
    merchant = Merchant(
        id=str(uuid4()),
        company_name="Retry Merchant",
        email="webhook-retry@test.porterchain.com",
        status="active",
    )
    webhook = MerchantWebhook(
        id=str(uuid4()),
        merchant_id=merchant.id,
        url="https://example.com/hook",
        events=["order.*"],
        secret_hash="hash",
        encrypted_signing_secret="enc",
    )
    db.add_all([merchant, webhook])
    db.flush()

    order_id = "ord_retry"
    _seed_delivery(
        db,
        merchant_id=merchant.id,
        webhook_id=webhook.id,
        order_id=order_id,
        success=False,
        attempt=1,
    )
    _seed_delivery(
        db,
        merchant_id=merchant.id,
        webhook_id=webhook.id,
        order_id=order_id,
        success=True,
        attempt=2,
    )
    db.commit()

    result = assess_merchant_webhook_delivery(db, merchant_id=merchant.id)
    assert result["total_deliveries"] == 1
    assert result["success_pct"] == 100.0
    assert result["meets_slo"] is True
