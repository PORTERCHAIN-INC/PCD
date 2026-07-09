"""CRM contacts."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.config import Settings
from porterchain_api.crm_models import (
    CrmActivity,
    CrmCompany,
    CrmContact,
    CrmContract,
    CrmDeal,
    CrmInvoice,
    CrmLead,
    CrmQuotation,
    CrmSalesTask,
)
from porterchain_api.domain.crm_states import (
    PIPELINE_STAGES,
    STAGE_PROBABILITY,
    CompanyMerchantStatus,
    ContractStatus,
    DealStage,
    LeadStatus,
    QuotationStatus,
    TaskStatus,
)
from porterchain_api.merchant_models import Merchant
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.db_json import json_text, json_text_lower
from porterchain_api.collaboration_engine.crm_helpers import _actor, _now, _today, _to_int



class CrmContactsMixin:
    def list_contacts(
        self, db: Session, *, company_id: str | None = None, search: str | None = None, limit: int = 500
    ) -> list[CrmContact]:
        q = db.query(CrmContact)
        if company_id:
            q = q.filter(CrmContact.company_id == company_id)
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

    def get_contact(self, db: Session, contact_id: str) -> CrmContact | None:
        return db.get(CrmContact, contact_id)

    def create_contact(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmContact:
        contact = CrmContact(**data)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        if contact.company_id:
            self.log_activity(
                db,
                entity_type="company",
                entity_id=contact.company_id,
                activity_type="system",
                subject=f"Contact added: {contact.first_name} {contact.last_name or ''}".strip(),
                actor_id=_actor(ctx),
            )
        return contact

    def update_contact(self, db: Session, contact_id: str, data: dict) -> CrmContact:
        contact = db.get(CrmContact, contact_id)
        if not contact:
            raise LookupError("contact_not_found")
        for key, value in data.items():
            setattr(contact, key, value)
        db.commit()
        db.refresh(contact)
        return contact

    def delete_contact(self, db: Session, contact_id: str) -> None:
        contact = db.get(CrmContact, contact_id)
        if not contact:
            raise LookupError("contact_not_found")
        db.delete(contact)
        db.commit()

