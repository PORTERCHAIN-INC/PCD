"""Merchant contacts — CRM-backed, synced with portal team members."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmCompany, CrmContact
from porterchain_api.domain.contacts import list_company_contacts
from porterchain_api.domain.crm_states import CompanyMerchantStatus
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import ROLE_LABELS, MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantUser

TEAM_ROLE_TAG = "portal_team"


def _name_from_email(email: str) -> tuple[str, str | None]:
    local = email.split("@")[0]
    parts = local.replace(".", " ").replace("_", " ").split()
    if len(parts) >= 2:
        return parts[0].title(), " ".join(p.title() for p in parts[1:])
    return local.title(), None


def _role_label(role: str) -> str:
    try:
        return ROLE_LABELS.get(MerchantRole(role), role.replace("_", " ").title())
    except ValueError:
        return role.replace("_", " ").title()


class MerchantContactsService:
    def ensure_company(self, db: Session, merchant: Merchant) -> CrmCompany:
        company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant.id).first()
        if company:
            return company

        company = CrmCompany(
            legal_name=merchant.company_name or merchant.email or "Merchant",
            operating_name=merchant.company_name,
            email=merchant.email,
            phone=merchant.phone,
            merchant_id=merchant.id,
            merchant_status=CompanyMerchantStatus.ACTIVE_MERCHANT.value,
        )
        db.add(company)
        db.flush()
        return company

    def sync_team_contacts(self, db: Session, merchant: Merchant) -> None:
        company = self.ensure_company(db, merchant)
        users = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.is_active.is_(True))
            .all()
        )
        for user in users:
            self._upsert_team_contact(db, company, user)
        db.commit()

    def sync_for_merchant(self, db: Session, merchant_id: str) -> None:
        merchant = db.get(Merchant, merchant_id)
        if not merchant:
            return
        self.sync_team_contacts(db, merchant)

    def list_contacts(self, db: Session, ctx: MerchantContext) -> list[dict[str, Any]]:
        self.sync_team_contacts(db, ctx.merchant)
        company = self.ensure_company(db, ctx.merchant)
        contacts = list_company_contacts(db, company_id=company.id)
        team_by_email = {
            u.email.lower(): u
            for u in db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == ctx.merchant.id, MerchantUser.is_active.is_(True))
            .all()
            if u.email
        }
        return [self._serialize(c, team_by_email.get((c.email or "").lower())) for c in contacts]

    def create_contact(self, db: Session, ctx: MerchantContext, data: dict[str, Any]) -> dict[str, Any]:
        company = self.ensure_company(db, ctx.merchant)
        roles = list(data.get("roles") or [])
        if TEAM_ROLE_TAG in roles:
            raise ValueError("team_contacts_are_synced")
        contact = CrmContact(company_id=company.id, **data)
        db.add(contact)
        self._audit(db, ctx, "contacts.created", contact.id, {"email": contact.email})
        db.commit()
        db.refresh(contact)
        return self._serialize(contact, None)

    def update_contact(
        self,
        db: Session,
        ctx: MerchantContext,
        contact_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        company = self.ensure_company(db, ctx.merchant)
        contact = self._get_contact(db, company.id, contact_id)
        team_user = self._team_user_for_contact(db, ctx, contact)
        if team_user and data.get("email") and data["email"].lower() != (contact.email or "").lower():
            raise ValueError("team_contact_email_managed_by_team")
        for key, value in data.items():
            if key == "roles" and team_user and TEAM_ROLE_TAG in (contact.roles or []):
                merged = list(value or [])
                if TEAM_ROLE_TAG not in merged:
                    merged.append(TEAM_ROLE_TAG)
                if team_user.role not in merged:
                    merged.append(team_user.role)
                setattr(contact, key, merged)
                continue
            setattr(contact, key, value)
        self._audit(db, ctx, "contacts.updated", contact.id, {"email": contact.email})
        db.commit()
        db.refresh(contact)
        return self._serialize(contact, team_user)

    def delete_contact(self, db: Session, ctx: MerchantContext, contact_id: str) -> None:
        company = self.ensure_company(db, ctx.merchant)
        contact = self._get_contact(db, company.id, contact_id)
        if self._team_user_for_contact(db, ctx, contact):
            raise ValueError("team_contact_remove_via_team")
        db.delete(contact)
        self._audit(db, ctx, "contacts.deleted", contact_id, {"email": contact.email})
        db.commit()

    def _upsert_team_contact(self, db: Session, company: CrmCompany, user: MerchantUser) -> CrmContact:
        email = user.email.lower().strip()
        contact = (
            db.query(CrmContact)
            .filter(CrmContact.company_id == company.id, CrmContact.email.ilike(email))
            .first()
        )
        first_name, last_name = _name_from_email(email)
        roles = [TEAM_ROLE_TAG, user.role]
        designation = _role_label(user.role)
        if contact:
            contact.first_name = contact.first_name or first_name
            contact.last_name = contact.last_name or last_name
            contact.email = user.email
            contact.designation = designation
            merged_roles = list(dict.fromkeys([*(contact.roles or []), *roles]))
            contact.roles = merged_roles
            return contact

        contact = CrmContact(
            company_id=company.id,
            first_name=first_name,
            last_name=last_name,
            email=user.email,
            designation=designation,
            roles=roles,
            is_primary=user.role == MerchantRole.OWNER.value,
        )
        db.add(contact)
        return contact

    def _get_contact(self, db: Session, company_id: str, contact_id: str) -> CrmContact:
        contact = (
            db.query(CrmContact)
            .filter(CrmContact.id == contact_id, CrmContact.company_id == company_id)
            .first()
        )
        if not contact:
            raise LookupError("contact_not_found")
        return contact

    def _team_user_for_contact(
        self,
        db: Session,
        ctx: MerchantContext,
        contact: CrmContact,
    ) -> MerchantUser | None:
        if not contact.email:
            return None
        return (
            db.query(MerchantUser)
            .filter(
                MerchantUser.merchant_id == ctx.merchant.id,
                MerchantUser.email.ilike(contact.email.strip()),
                MerchantUser.is_active.is_(True),
            )
            .first()
        )

    def _serialize(self, contact: CrmContact, team_user: MerchantUser | None) -> dict[str, Any]:
        is_team = team_user is not None or TEAM_ROLE_TAG in (contact.roles or [])
        return {
            "id": contact.id,
            "company_id": contact.company_id,
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "designation": contact.designation,
            "department": contact.department,
            "phone": contact.phone,
            "mobile": contact.mobile,
            "email": contact.email,
            "linkedin": contact.linkedin,
            "birthday": contact.birthday.isoformat() if contact.birthday else None,
            "roles": contact.roles or [],
            "is_primary": contact.is_primary,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "source": "team" if is_team else "manual",
            "team_user_id": team_user.id if team_user else None,
            "team_role": team_user.role if team_user else None,
            "can_delete": not is_team,
        }

    def _audit(
        self,
        db: Session,
        ctx: MerchantContext,
        action: str,
        resource_id: str,
        payload: dict[str, Any],
    ) -> None:
        db.add(
            MerchantAuditLog(
                merchant_id=ctx.merchant.id,
                actor_user_id=ctx.user.id,
                action=action,
                resource_type="crm_contact",
                resource_id=resource_id,
                payload=payload,
            )
        )
