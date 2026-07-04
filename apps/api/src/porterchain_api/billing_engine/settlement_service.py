"""Billing settlement — async queue processor and ledger writes."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry
from porterchain_api.db import SessionLocal
from porterchain_api.models import Payment

logger = logging.getLogger(__name__)


class SettlementService:
    def process_queue_job(self, payload: dict[str, Any]) -> BillingLedgerEntry | None:
        db = SessionLocal()
        try:
            return self._process(db, payload)
        finally:
            db.close()

    def _process(self, db: Session, payload: dict[str, Any]) -> BillingLedgerEntry | None:
        action = payload.get("action", "unknown")
        if action == "payment_settled":
            return self._record_payment_settled(db, payload)
        if action == "payment_succeeded":
            return self._record_stripe_success(db, payload)
        logger.info("billing: unhandled action=%s", action)
        entry = BillingLedgerEntry(kind=action, status="ignored", metadata_json=payload)
        db.add(entry)
        db.commit()
        return entry

    def _record_payment_settled(self, db: Session, payload: dict[str, Any]) -> BillingLedgerEntry:
        payment_id = payload.get("aggregate_id")
        payment = db.query(Payment).filter(Payment.id == payment_id).first() if payment_id else None
        entry = BillingLedgerEntry(
            kind="payment_settled",
            payment_id=payment_id,
            order_id=payment.order_id if payment else None,
            amount_cents=payment.amount_cents if payment else None,
            currency=payment.currency if payment else "cad",
            metadata_json=payload.get("payload") or {},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("billing ledger: payment_settled payment_id=%s", payment_id)
        return entry

    def _record_stripe_success(self, db: Session, payload: dict[str, Any]) -> BillingLedgerEntry:
        data = payload.get("data") or {}
        entry = BillingLedgerEntry(
            kind="stripe_payment_succeeded",
            status="recorded",
            metadata_json={"stripe_session_id": data.get("id"), "raw": data},
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("billing ledger: stripe session=%s", data.get("id"))
        return entry


def process_billing_job(payload: dict[str, Any]) -> None:
    SettlementService().process_queue_job(payload)
