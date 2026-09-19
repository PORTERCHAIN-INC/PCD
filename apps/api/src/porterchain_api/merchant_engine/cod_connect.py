"""Persist Stripe Connect / COD flags on the merchants row."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def persist_connect_account_id(db: Session, merchant: Any, account_id: str) -> None:
    merchant.stripe_connect_account_id = account_id
    db.add(merchant)
    db.commit()


def persist_cod_enabled(db: Session, merchant: Any, *, enabled: bool) -> Any:
    merchant.cod_enabled = enabled
    db.add(merchant)
    db.commit()
    db.refresh(merchant)
    return merchant
