"""Merchant contacts — portal façade over collaboration CRM."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.domain.contacts import TEAM_ROLE_TAG, list_company_contacts
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_engine.rbac import ROLE_LABELS, MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantUser


def _role_label(role: str) -> str:
    try:
        return ROLE_LABELS.get(MerchantRole(role), role.replace("_", " ").title())
    except ValueError:
        return role.replace("_", " ").title()


class MerchantContactsService:
    def _crm(self):
        from porterchain_api.collaboration_engine.crm_service import CrmSalesService

        return CrmSalesService()

    def ensure_company(self, db: Session, merchant: Merchant) -> Any:
        return self._crm().ensure_company_for_merchant(db, merchant)

    def sync_team_contacts(self, db: Session, merchant: Merchant) -> None:
        crm = self._crm()
        company = crm.ensure_company_for_merchant(db, merchant)
        users = (
            db.query(MerchantUser)
            .filter(MerchantUser.merchant_id == merchant.id, MerchantUser.is_active.is_(True))
            .all()
        )
        for user in users:
            if not user.email:
                continue
            crm.upsert_team_contact(
                db,
                company.id,
                email=user.email,
                role=user.role,
                designation=_role_label(user.role),
                is_owner=user.role == MerchantRole.OWNER.value,
            )
        db.commit()

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
        payload = dict(data)
        payload["company_id"] = company.id
        contact = self._crm().create_contact(db, None, payload)
        self._audit(db, ctx, "contacts.created", contact.id, {"email": contact.email})
        db.commit()
        return self._serialize(contact, None)

    def update_contact(
        self,
        db: Session,
        ctx: MerchantContext,
        contact_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        company = self.ensure_company(db, ctx.merchant)
        crm = self._crm()
        contact = crm.get_contact_for_company(db, company.id, contact_id)
        team_user = self._team_user_for_contact(db, ctx, contact)
        payload = dict(data)
        if team_user and payload.get("email") and payload["email"].lower() != (contact.email or "").lower():
            raise ValueError("team_contact_email_managed_by_team")
        if team_user and TEAM_ROLE_TAG in (contact.roles or []) and "roles" in payload:
            merged = list(payload.get("roles") or [])
            if TEAM_ROLE_TAG not in merged:
                merged.append(TEAM_ROLE_TAG)
            if team_user.role not in merged:
                merged.append(team_user.role)
            payload["roles"] = merged
        contact = crm.update_contact(db, contact_id, payload)
        self._audit(db, ctx, "contacts.updated", contact.id, {"email": contact.email})
        db.commit()
        return self._serialize(contact, team_user)

    def delete_contact(self, db: Session, ctx: MerchantContext, contact_id: str) -> None:
        company = self.ensure_company(db, ctx.merchant)
        crm = self._crm()
        contact = crm.get_contact_for_company(db, company.id, contact_id)
        if self._team_user_for_contact(db, ctx, contact):
            raise ValueError("team_contact_remove_via_team")
        email = contact.email
        crm.delete_contact(db, contact_id)
        self._audit(db, ctx, "contacts.deleted", contact_id, {"email": email})
        db.commit()

    def _team_user_for_contact(
        self,
        db: Session,
        ctx: MerchantContext,
        contact: Any,
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

    def _serialize(self, contact: Any, team_user: MerchantUser | None) -> dict[str, Any]:
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


def record_portal_signup_lead(
    db: Session, *, merchant_id: str, email: str | None, company_name: str | None
) -> None:
    """Merchant portal sign-up → CRM lead (dedup-linked). Writes live in collaboration_engine."""
    from porterchain_api.collaboration_engine.signup_leads import record_signup_lead

    record_signup_lead(
        db,
        kind="merchant_signup",
        external_id=merchant_id,
        email=email,
        company_name=company_name,
        extra={"merchant_id": merchant_id},
    )
