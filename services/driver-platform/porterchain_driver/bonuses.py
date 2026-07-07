"""Driver bonuses."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class BonusesService:
    def available_count(self, db: Session, driver_id: str) -> int:
        from porterchain_api.driver_models import DriverBonus

        return (
            db.query(DriverBonus)
            .filter(DriverBonus.driver_id == driver_id, DriverBonus.status == "available")
            .count()
        )

    def list_bonuses(self, db: Session, driver_id: str) -> list[dict]:
        from porterchain_api.driver_models import DriverBonus

        rows = (
            db.query(DriverBonus)
            .filter(DriverBonus.driver_id == driver_id)
            .order_by(DriverBonus.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": b.id,
                "title": b.title,
                "amount_cents": b.amount_cents,
                "status": b.status,
                "criteria": b.criteria,
                "expires_at": b.expires_at.isoformat() if b.expires_at else None,
            }
            for b in rows
        ]

    def claim_bonus(self, db: Session, driver: Any, bonus_id: str) -> dict:
        from porterchain_api.driver_models import DriverBonus
        from porterchain_driver.wallet import WalletService

        bonus = (
            db.query(DriverBonus)
            .filter(DriverBonus.id == bonus_id, DriverBonus.driver_id == driver.id, DriverBonus.status == "available")
            .first()
        )
        if not bonus:
            raise LookupError("bonus_not_found")
        bonus.status = "claimed"
        WalletService().credit(
            db, driver, amount_cents=bonus.amount_cents, tx_type="bonus", reference_id=bonus.id, description=bonus.title
        )
        db.flush()
        return {"bonus_id": bonus.id, "amount_cents": bonus.amount_cents, "status": "claimed"}
