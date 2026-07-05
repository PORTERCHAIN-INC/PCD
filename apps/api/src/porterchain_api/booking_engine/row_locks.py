"""Pessimistic row locks for payment and order state paths (DD-08)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.models import Order, Payment, Quote


def lock_quote(db: Session, quote_id: str) -> Quote | None:
    return db.query(Quote).filter(Quote.id == quote_id).with_for_update().first()


def lock_order(db: Session, order_id: str) -> Order | None:
    return db.query(Order).filter(Order.id == order_id).with_for_update().first()


def lock_order_by_quote(db: Session, quote_id: str) -> Order | None:
    return db.query(Order).filter(Order.quote_id == quote_id).with_for_update().first()


def lock_payment(db: Session, payment_id: str) -> Payment | None:
    return db.query(Payment).filter(Payment.id == payment_id).with_for_update().first()


def lock_active_payment(db: Session, quote_id: str) -> Payment | None:
    return (
        db.query(Payment)
        .filter(Payment.quote_id == quote_id)
        .order_by(Payment.created_at.desc())
        .with_for_update()
        .first()
    )
