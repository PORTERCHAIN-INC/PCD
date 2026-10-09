"""CRM bounded-context persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmCompany


class CrmRepository:

    def get_company_by_merchant_id(self, db: Session, merchant_id: str) -> CrmCompany | None:
        return db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()
