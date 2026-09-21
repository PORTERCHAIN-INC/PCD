"""Driver wallet — balance, transactions, payouts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from porterchain_driver.types import WalletTransactionView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class WalletService:
    def balance_cents(self, driver: Any, db: Session | None = None) -> int:
        if db is not None:
            from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

            return wallet_balance_cents(
                db, driver.id, cached_cents=int(driver.wallet_balance_cents or 0)
            )
        return int(driver.wallet_balance_cents or 0)

    def list_transactions(self, db: Session, driver_id: str, *, limit: int = 50) -> list[WalletTransactionView]:
        from porterchain_api.driver_models import DriverWalletTransaction

        rows = (
            db.query(DriverWalletTransaction)
            .filter(DriverWalletTransaction.driver_id == driver_id)
            .order_by(DriverWalletTransaction.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            WalletTransactionView(
                id=r.id,
                type=r.tx_type,
                amount_cents=r.amount_cents,
                balance_after_cents=r.balance_after_cents,
                description=r.description or "",
                reference_id=r.reference_id,
                created_at=r.created_at,
            )
            for r in rows
        ]

    def list_payouts(self, db: Session, driver_id: str, *, limit: int = 20) -> list[dict]:
        from porterchain_api.admin_models import DriverPayout

        rows = (
            db.query(DriverPayout)
            .filter(DriverPayout.driver_id == driver_id)
            .order_by(DriverPayout.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": p.id,
                "amount_cents": p.amount_cents,
                "currency": p.currency,
                "status": p.status,
                "reference": p.reference,
                "created_at": p.created_at.isoformat(),
            }
            for p in rows
        ]

    def credit(
        self,
        db: Session,
        driver: Any,
        *,
        amount_cents: int,
        tx_type: str,
        reference_id: str | None = None,
        description: str = "",
    ) -> int:
        from porterchain_api.driver_engine.wallet_ledger import record_transaction, wallet_balance_cents

        remaining = wallet_balance_cents(
            db, driver.id, cached_cents=int(driver.wallet_balance_cents or 0)
        )
        new_balance = remaining + amount_cents
        record_transaction(
            db,
            driver_id=driver.id,
            tx_type=tx_type,
            amount_cents=amount_cents,
            balance_after_cents=new_balance,
            reference_id=reference_id,
            description=description,
        )
        return new_balance

    def debit(
        self,
        db: Session,
        driver: Any,
        *,
        amount_cents: int,
        tx_type: str,
        reference_id: str | None = None,
        description: str = "",
    ) -> int:
        if amount_cents > self.balance_cents(driver, db):
            raise ValueError("insufficient_wallet_balance")
        return self.credit(
            db,
            driver,
            amount_cents=-amount_cents,
            tx_type=tx_type,
            reference_id=reference_id,
            description=description,
        )
