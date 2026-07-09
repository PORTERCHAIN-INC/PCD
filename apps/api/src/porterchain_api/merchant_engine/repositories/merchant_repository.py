"""Merchant bounded-context persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant, MerchantUser


class MerchantRepository:
    def get_by_id(self, db: Session, merchant_id: str) -> Merchant | None:
        return db.query(Merchant).filter(Merchant.id == merchant_id).first()

    def get_by_clerk_org_id(self, db: Session, clerk_org_id: str) -> Merchant | None:
        return db.query(Merchant).filter(Merchant.clerk_org_id == clerk_org_id).first()

    def get_user_by_clerk_id(self, db: Session, clerk_user_id: str) -> MerchantUser | None:
        return db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).first()

    def list_active(self, db: Session, *, limit: int = 100) -> list[Merchant]:
        return (
            db.query(Merchant)
            .filter(Merchant.status == "ACTIVE")
            .order_by(Merchant.created_at.desc())
            .limit(limit)
            .all()
        )
