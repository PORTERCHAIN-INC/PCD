"""CRM contact queries shared across merchant and collaboration surfaces."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmContact


def list_company_contacts(
    db: Session,
    *,
    company_id: str,
    search: str | None = None,
    limit: int = 500,
) -> list[CrmContact]:
    q = db.query(CrmContact).filter(CrmContact.company_id == company_id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                CrmContact.first_name.ilike(like),
                CrmContact.last_name.ilike(like),
                CrmContact.email.ilike(like),
            )
        )
    return q.order_by(CrmContact.created_at.desc()).limit(limit).all()
