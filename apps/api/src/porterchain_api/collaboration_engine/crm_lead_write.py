"""CRM lead create / update / score / convert mutations."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import CrmActor, _actor, _now
from porterchain_api.crm_models import (
    CrmCompany,
    CrmContact,
    CrmDeal,
    CrmLead,
)
from porterchain_api.domain.crm_states import (
    STAGE_PROBABILITY,
    CompanyMerchantStatus,
    DealStage,
    LeadDecisionStatus,
    LeadStatus,
    normalize_lead_status,
)
from porterchain_api.collaboration_engine.lead_pipeline import stamp_status_change


class CrmLeadWriteMixin:
    @staticmethod
    def score_lead(lead: CrmLead, visitor=None, *, db: Session | None = None) -> int:
        """Deterministic fit score 0-100 (industry, volume, GTA area, channel, engagement).

        Reasons are stored on ``custom_fields._score`` for the lead page. The
        empirical prior is kept as an advisory ``predictive`` figure only.
        """
        from porterchain_api.collaboration_engine.lead_scoring import get_score_priors, predictive_score
        from porterchain_api.lead_desk.fit_score import fit_score

        fit = fit_score(lead, visitor)
        priors = get_score_priors(db) if db is not None else None
        fields = dict(lead.custom_fields) if isinstance(lead.custom_fields, dict) else {}
        fields["_score"] = {
            "heuristic": fit["score"],
            "predictive": round(predictive_score(lead, priors), 2) if priors else None,
            "method": fit["version"],
            "priors_n": priors.sample_n if priors else 0,
            "reasons": fit["reasons"],
        }
        lead.custom_fields = fields
        return int(fit["score"])

    def create_lead(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmLead:
        from porterchain_api.domain.crm_states import channel_for_source

        data = dict(data)
        if data.get("status"):
            data["status"] = normalize_lead_status(data["status"])
        data.setdefault("assigned_to", _actor(ctx))
        if not data.get("channel"):
            data["channel"] = channel_for_source(data.get("source"))
        lead = CrmLead(**data)
        visitor = self._visitor_for_lead(db, lead)
        lead.lead_score = self.score_lead(lead, visitor, db=db)
        lead.last_touch_at = _now()
        db.add(lead)
        db.commit()
        db.refresh(lead)
        self.log_activity(
            db,
            entity_type="lead",
            entity_id=lead.id,
            activity_type="system",
            subject=f"Lead created from {lead.source}",
            actor_id=_actor(ctx),
        )
        return lead

    def update_lead(self, db: Session, lead_id: str, data: dict) -> CrmLead:
        lead = db.get(CrmLead, lead_id)
        if not lead:
            raise LookupError("lead_not_found")
        prev_status = lead.status
        data = dict(data)
        if data.get("status"):
            data["status"] = normalize_lead_status(data["status"])
            stamp_status_change(lead, data["status"])
        for key, value in data.items():
            setattr(lead, key, value)
        visitor = self._visitor_for_lead(db, lead)
        lead.lead_score = self.score_lead(lead, visitor, db=db)
        db.commit()
        db.refresh(lead)
        if "status" in data and data["status"] != prev_status:
            if data["status"] in ("won", "lost"):
                from porterchain_api.collaboration_engine.lead_scoring import clear_score_priors_cache

                clear_score_priors_cache()
            self.log_activity(
                db,
                entity_type="lead",
                entity_id=lead.id,
                activity_type="status_change",
                subject=f"Status: {prev_status} → {lead.status}",
            )
        return lead

    def _visitor_for_lead(self, db: Session, lead: CrmLead):
        """Lookup visitor session — prefer first-class column, then custom_fields."""
        from porterchain_api.booking_models import VisitorSession

        session_id = lead.visitor_session_id
        if not isinstance(session_id, str) or not session_id.strip():
            fields = lead.custom_fields if isinstance(lead.custom_fields, dict) else {}
            session_id = fields.get("visitor_id") or fields.get("session_id")
        if not isinstance(session_id, str) or not session_id.strip():
            return None
        return db.query(VisitorSession).filter(VisitorSession.id == session_id.strip()).first()

    def delete_lead(self, db: Session, lead_id: str) -> None:
        lead = db.get(CrmLead, lead_id)
        if not lead:
            raise LookupError("lead_not_found")
        db.delete(lead)
        db.commit()

    def convert_lead(
        self,
        db: Session,
        ctx: CrmActor | None,
        lead_id: str,
        *,
        create_deal: bool = True,
        deal_name: str | None = None,
        expected_revenue_cents: int | None = None,
        target_stage: str | None = None,
    ) -> dict[str, str | None]:
        """Lead → Company (+ primary Contact) (+ Deal). Idempotent on company."""
        lead = db.get(CrmLead, lead_id)
        if not lead:
            raise LookupError("lead_not_found")

        company = None
        if lead.company_id:
            company = db.get(CrmCompany, lead.company_id)
        if not company:
            company = self.find_company_duplicate(db, legal_name=lead.company_name, email=lead.email)
        if not company:
            company = CrmCompany(
                legal_name=lead.company_name,
                industry=lead.industry,
                website=lead.website,
                business_type=lead.business_type,
                email=lead.email,
                phone=lead.phone,
                address=lead.address or {},
                estimated_deliveries_per_month=lead.estimated_deliveries_per_month,
                estimated_monthly_revenue_cents=lead.estimated_revenue_cents,
                preferred_vehicle=lead.preferred_vehicle,
                service_area=lead.service_area,
                current_logistics_provider=lead.current_logistics_provider,
                merchant_status=CompanyMerchantStatus.PROSPECT.value,
                owner_id=lead.assigned_to or _actor(ctx),
                tags=lead.tags or [],
            )
            db.add(company)
            db.flush()

        contact = None
        if lead.primary_contact_name:
            parts = lead.primary_contact_name.split(" ", 1)
            contact = CrmContact(
                company_id=company.id,
                first_name=parts[0],
                last_name=parts[1] if len(parts) > 1 else None,
                email=lead.email,
                phone=lead.phone,
                roles=["primary_contact"],
                is_primary=True,
            )
            db.add(contact)
            db.flush()

        deal = None
        if create_deal:
            valid_stages = set(STAGE_PROBABILITY.keys())
            stage = target_stage if target_stage in valid_stages else DealStage.QUALIFIED.value
            deal = CrmDeal(
                name=deal_name or f"{lead.company_name} — Merchant Onboarding",
                company_id=company.id,
                contact_id=contact.id if contact else None,
                stage=stage,
                probability=STAGE_PROBABILITY[stage],
                expected_revenue_cents=expected_revenue_cents
                or lead.estimated_revenue_cents
                or 0,
                expected_close_date=lead.expected_close_date,
                owner_id=lead.assigned_to or _actor(ctx),
            )
            if stage in (DealStage.WON.value, DealStage.LOST.value):
                deal.closed_at = _now()
            db.add(deal)
            db.flush()

        stamp_status_change(lead, LeadStatus.WON.value)
        lead.status = LeadStatus.WON.value
        lead.decision_status = LeadDecisionStatus.CONVERTED.value
        lead.company_id = company.id
        lead.contact_id = contact.id if contact else None
        lead.deal_id = deal.id if deal else None
        db.commit()

        self.log_activity(
            db,
            entity_type="company",
            entity_id=company.id,
            activity_type="status_change",
            subject=f"Converted from lead {lead.company_name}",
            actor_id=_actor(ctx),
        )
        return {
            "company_id": company.id,
            "contact_id": contact.id if contact else None,
            "deal_id": deal.id if deal else None,
        }

