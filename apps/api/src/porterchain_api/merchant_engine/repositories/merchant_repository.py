"""Merchant bounded-context persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant


class MerchantRepository:
    def get_by_id(self, db: Session, merchant_id: str) -> Merchant | None:
        return db.query(Merchant).filter(Merchant.id == merchant_id).first()

    def list_active(self, db: Session, *, limit: int = 100) -> list[Merchant]:
        return (
            db.query(Merchant)
            .filter(Merchant.status == "ACTIVE")
            .order_by(Merchant.created_at.desc())
            .limit(limit)
            .all()
        )
