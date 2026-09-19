"""Driver wallet ledger writes owned by driver_engine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.driver_models import DriverWalletTransaction


def wallet_balance_cents(db: Session, driver_id: str, *, cached_cents: int | None = None) -> int:
    """Ledger is SoT. The drivers.wallet_balance_cents column is a cache only."""
    from decimal import Decimal

    from sqlalchemy import func

    total = (
        db.query(func.coalesce(func.sum(DriverWalletTransaction.amount_cents), 0))
        .filter(DriverWalletTransaction.driver_id == driver_id)
        .scalar()
    )
    if isinstance(total, (int, float, Decimal)) and not isinstance(total, bool):
        return int(total)
    return int(cached_cents or 0)


def record_transaction(
    db: Session,
    *,
    driver_id: str,
    tx_type: str,
    amount_cents: int,
    balance_after_cents: int,
    reference_id: str | None = None,
    description: str = "",
    flush: bool = True,
) -> DriverWalletTransaction:
    row = DriverWalletTransaction(
        driver_id=driver_id,
        tx_type=tx_type,
        amount_cents=amount_cents,
        balance_after_cents=balance_after_cents,
        reference_id=reference_id,
        description=description or None,
    )
    db.add(row)
    if flush:
        db.flush()
    return row
