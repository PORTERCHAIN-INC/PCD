"""CRM contacts."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import CrmActor
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
from porterchain_api.db_json import json_text, json_text_lower
from porterchain_api.collaboration_engine.crm_helpers import _actor, _now, _today, _to_int
from porterchain_api.domain.contacts import TEAM_ROLE_TAG



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

    def create_contact(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmContact:
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

    def get_contact_for_company(self, db: Session, company_id: str, contact_id: str) -> CrmContact:
        contact = (
            db.query(CrmContact)
            .filter(CrmContact.id == contact_id, CrmContact.company_id == company_id)
            .first()
        )
        if not contact:
            raise LookupError("contact_not_found")
        return contact

    def upsert_team_contact(
        self,
        db: Session,
        company_id: str,
        *,
        email: str,
        role: str,
        designation: str,
        is_owner: bool,
    ) -> CrmContact:
        normalized = email.lower().strip()
        contact = (
            db.query(CrmContact)
            .filter(CrmContact.company_id == company_id, CrmContact.email.ilike(normalized))
            .first()
        )
        local = email.split("@")[0]
        parts = local.replace(".", " ").replace("_", " ").split()
        if len(parts) >= 2:
            first_name, last_name = parts[0].title(), " ".join(p.title() for p in parts[1:])
        else:
            first_name, last_name = local.title(), None
        roles = [TEAM_ROLE_TAG, role]
        if contact:
            contact.first_name = contact.first_name or first_name
            contact.last_name = contact.last_name or last_name
            contact.email = email
            contact.designation = designation
            merged_roles = list(dict.fromkeys([*(contact.roles or []), *roles]))
            contact.roles = merged_roles
            return contact
        contact = CrmContact(
            company_id=company_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            designation=designation,
            roles=roles,
            is_primary=is_owner,
        )
        db.add(contact)
        return contact

