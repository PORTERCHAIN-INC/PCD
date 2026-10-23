"""Persist the Stripe Connect account id on the merchants row.

Cash on delivery is retired (no-COD rule): ``merchants.cod_enabled`` is no longer
read or written. The column stays until an approved drop migration.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def persist_connect_account_id(db: Session, merchant: Any, account_id: str) -> None:
    merchant.stripe_connect_account_id = account_id
    db.add(merchant)
    db.commit()
