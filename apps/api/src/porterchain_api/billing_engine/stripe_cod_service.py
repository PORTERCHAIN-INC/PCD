"""COD via Stripe Connect — Payment Link / Checkout Session at the door (no Terminal v1)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.states import CodStatus
from porterchain_api.booking_models import Order
from porterchain_api.services.stripe_service import (
    create_cod_checkout_session,
    create_connect_account_link,
    create_connect_express_account,
    is_dummy_stripe_id,
)

logger = logging.getLogger(__name__)


def _fee_cents(amount_cents: int, bps: int) -> int:
    return max(0, min(amount_cents, (amount_cents * bps) // 10_000))


class StripeCodService:
    """Merchant Connect onboarding + driver-issued COD Checkout sessions."""

    def create_connect_account_link(
        self,
        db: Session,
        settings: Settings,
        merchant: Any,
    ) -> dict[str, str]:
        from porterchain_api.merchant_engine.cod_connect import persist_connect_account_id

        if settings.allow_stripe_mock:
            if not merchant.stripe_connect_account_id:
                persist_connect_account_id(
                    db, merchant, f"acct_mock_{merchant.id[:8]}"
                )
            return {
                "url": f"{settings.stripe_connect_return_url}&mock=1",
                "account_id": merchant.stripe_connect_account_id,
                "mock": "true",
            }
        if not settings.stripe_secret:
            raise RuntimeError("stripe_not_configured")
        if not merchant.stripe_connect_account_id:
            persist_connect_account_id(
                db,
                merchant,
                create_connect_express_account(
                    settings, email=merchant.email, merchant_id=merchant.id
                ),
            )
        url = create_connect_account_link(settings, account_id=merchant.stripe_connect_account_id)
        return {"url": url, "account_id": merchant.stripe_connect_account_id}

    def set_cod_enabled(self, db: Session, merchant: Any, *, enabled: bool) -> Any:
        from porterchain_api.merchant_engine.cod_connect import persist_cod_enabled

        if enabled and not merchant.stripe_connect_account_id:
            raise ValueError("connect_account_required")
        return persist_cod_enabled(db, merchant, enabled=enabled)

    def issue_cod_checkout(
        self,
        db: Session,
        settings: Settings,
        order: Order,
        merchant: Any,
    ) -> dict[str, Any]:
        amount = int(order.cod_amount_cents or 0)
        if amount <= 0:
            raise ValueError("cod_amount_required")
        if not merchant.cod_enabled:
            raise ValueError("cod_not_enabled")
        if not merchant.stripe_connect_account_id:
            raise ValueError("connect_account_required")
        status = (order.cod_status or CodStatus.NONE.value).lower()
        if status == CodStatus.COLLECTED.value or status == CodStatus.PAYOUT_PROCESSED.value:
            raise ValueError("cod_already_collected")

        from porterchain_api.merchant_engine.scan_gate_service import (
            PackagesIncomplete,
            ScanGateService,
        )

        try:
            ScanGateService().assert_cod_scans(db, order)
        except PackagesIncomplete:
            raise

        destination = (merchant.stripe_connect_account_id or "").strip()
        if settings.allow_stripe_mock or is_dummy_stripe_id(destination):
            session_id = f"cs_mock_cod_{uuid.uuid4().hex[:12]}"
            url = f"{settings.driver_portal_url.rstrip('/')}/jobs?cod_mock={order.id}"
            order.cod_stripe_session_id = session_id
            order.cod_status = CodStatus.LINK_ISSUED.value
            db.add(order)
            db.commit()
            return {"checkout_url": url, "session_id": session_id, "mock": True, "amount_cents": amount}

        if not settings.stripe_secret:
            raise RuntimeError("stripe_not_configured")
        fee = _fee_cents(amount, settings.stripe_cod_platform_fee_bps)
        currency = (order.currency or "cad").lower()
        metadata = {
            "purpose": "cod",
            "order_id": order.id,
            "merchant_id": merchant.id,
            "cod_amount_cents": str(amount),
        }
        success = f"{settings.driver_portal_url.rstrip('/')}/jobs?cod=success&order_id={order.id}"
        cancel = f"{settings.driver_portal_url.rstrip('/')}/jobs?cod=cancel&order_id={order.id}"
        url, session_id = create_cod_checkout_session(
            settings,
            amount_cents=amount,
            currency=currency,
            application_fee_cents=fee,
            destination_account_id=merchant.stripe_connect_account_id,
            metadata=metadata,
            success_url=success,
            cancel_url=cancel,
            product_name=f"COD · {order.tracking_number or order.order_number}",
            product_description="Cash on delivery — PorterChain",
        )
        order.cod_stripe_session_id = session_id
        order.cod_status = CodStatus.LINK_ISSUED.value
        db.add(order)
        db.commit()
        return {
            "checkout_url": url,
            "session_id": session_id,
            "mock": False,
            "amount_cents": amount,
            "platform_fee_cents": fee,
        }

    def mark_cod_collected(
        self,
        db: Session,
        order: Order,
        *,
        payment_intent_id: str | None,
        session_id: str | None = None,
    ) -> None:
        if session_id and order.cod_stripe_session_id and session_id != order.cod_stripe_session_id:
            logger.warning(
                "cod_session_mismatch order=%s expected=%s got=%s",
                order.id,
                order.cod_stripe_session_id,
                session_id,
            )
        order.cod_status = CodStatus.COLLECTED.value
        if payment_intent_id:
            # Keep retail PI field separate when possible; store COD PI in compliance bag.
            extra = dict(order.compliance_metadata or {})
            cod_meta = dict(extra.get("cod") or {})
            cod_meta["payment_intent_id"] = payment_intent_id
            if session_id:
                cod_meta["session_id"] = session_id
            extra["cod"] = cod_meta
            order.compliance_metadata = extra
        db.add(order)
        db.commit()

    def issue_cod_checkout_for_order(
        self,
        db: Session,
        settings: Settings,
        order: Order,
    ) -> dict[str, Any]:
        """Resolve the merchant then issue a COD Checkout session."""
        from porterchain_api.merchant_engine.lookups import get_merchant

        if not order.merchant_id:
            raise ValueError("merchant_required")
        merchant = get_merchant(db, order.merchant_id)
        if not merchant:
            raise LookupError("merchant_not_found")
        return self.issue_cod_checkout(db, settings, order, merchant)

    def list_collection_queue(self, db: Session, *, status: str | None = None, limit: int = 200) -> dict:
        """Orders with a COD amount — admin collection queue."""
        q = db.query(Order).filter(Order.cod_amount_cents.isnot(None), Order.cod_amount_cents > 0)
        if status:
            q = q.filter(Order.cod_status == status)
        rows = q.order_by(Order.created_at.desc()).limit(limit).all()
        return {
            "items": [
                {
                    "order_id": o.id,
                    "order_number": o.order_number,
                    "tracking_number": o.tracking_number,
                    "merchant_id": o.merchant_id,
                    "cod_amount_cents": o.cod_amount_cents,
                    "cod_status": o.cod_status,
                    "currency": o.currency,
                    "state": o.state,
                }
                for o in rows
            ]
        }
