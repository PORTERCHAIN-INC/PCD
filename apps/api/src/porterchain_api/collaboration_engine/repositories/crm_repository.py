"""CRM bounded-context persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmCompany, CrmContact


class CrmRepository:
    def get_company_by_id(self, db: Session, company_id: str) -> CrmCompany | None:
        return db.query(CrmCompany).filter(CrmCompany.id == company_id).first()

    def get_company_by_merchant_id(self, db: Session, merchant_id: str) -> CrmCompany | None:
        return db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()

    def get_contact_by_id(self, db: Session, contact_id: str) -> CrmContact | None:
        return db.query(CrmContact).filter(CrmContact.id == contact_id).first()

    def list_contacts_for_company(self, db: Session, company_id: str) -> list[CrmContact]:
        return (
            db.query(CrmContact)
            .filter(CrmContact.company_id == company_id)
            .order_by(CrmContact.created_at.desc())
            .all()
        )
