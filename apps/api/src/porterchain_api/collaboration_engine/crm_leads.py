"""CRM leads."""

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



class CrmLeadsMixin:
    def list_leads(
        self,
        db: Session,
        *,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        source: str | None = None,
        industry: str | None = None,
        city: str | None = None,
        province: str | None = None,
        min_score: int | None = None,
        unassigned: bool | None = None,
        converted: bool | None = None,
        search: str | None = None,
        limit: int = 500,
    ) -> list[CrmLead]:
        q = db.query(CrmLead)
        if status:
            q = q.filter(CrmLead.status == status)
        if priority:
            q = q.filter(CrmLead.priority == priority)
        if assigned_to:
            q = q.filter(CrmLead.assigned_to == assigned_to)
        if source:
            q = q.filter(CrmLead.source == source)
        if industry:
            q = q.filter(CrmLead.industry == industry)
        if city:
            q = q.filter(json_text(CrmLead.address, "city") == city)
        if province:
            q = q.filter(json_text(CrmLead.address, "province") == province)
        if min_score is not None:
            q = q.filter(CrmLead.lead_score >= min_score)
        if unassigned:
            q = q.filter(CrmLead.assigned_to.is_(None))
        if converted is True:
            q = q.filter(CrmLead.status == LeadStatus.CONVERTED.value)
        elif converted is False:
            q = q.filter(CrmLead.status != LeadStatus.CONVERTED.value)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    CrmLead.company_name.ilike(like),
                    CrmLead.email.ilike(like),
                    CrmLead.primary_contact_name.ilike(like),
                    CrmLead.service_area.ilike(like),
                )
            )
        return q.order_by(CrmLead.created_at.desc()).limit(limit).all()

    def lead_filter_facets(self, db: Session) -> dict[str, list]:
        """Distinct values to power lead filter dropdowns."""
        industries = [
            row[0]
            for row in db.query(CrmLead.industry).filter(CrmLead.industry.isnot(None)).distinct().all()
            if row[0]
        ]
        sources = [row[0] for row in db.query(CrmLead.source).distinct().all() if row[0]]

        city_expr = json_text(CrmLead.address, "city")
        province_expr = json_text(CrmLead.address, "province")

        # Cities with counts so the UI can show the busiest markets first.
        city_rows = (
            db.query(city_expr, func.count(CrmLead.id))
            .filter(city_expr.isnot(None))
            .group_by(city_expr)
            .all()
        )
        cities = sorted(
            ({"name": c, "count": n} for c, n in city_rows if c),
            key=lambda x: (-x["count"], x["name"]),
        )

        province_rows = (
            db.query(province_expr, func.count(CrmLead.id))
            .filter(province_expr.isnot(None))
            .group_by(province_expr)
            .all()
        )
        provinces = sorted(
            ({"code": p, "count": n} for p, n in province_rows if p),
            key=lambda x: (-x["count"], x["code"]),
        )

        return {
            "industries": sorted(industries),
            "sources": sorted(sources),
            "cities": cities,
            "provinces": provinces,
        }

    def get_lead(self, db: Session, lead_id: str) -> CrmLead | None:
        return db.get(CrmLead, lead_id)

    @staticmethod
    def score_lead(lead: CrmLead) -> int:
        """Heuristic logistics lead score (0-100)."""
        score = 0
        deliveries = lead.estimated_deliveries_per_month or 0
        if deliveries >= 1000:
            score += 40
        elif deliveries >= 250:
            score += 30
        elif deliveries >= 50:
            score += 20
        elif deliveries > 0:
            score += 10
        revenue = lead.estimated_revenue_cents or 0
        if revenue >= 5_000_000:
            score += 30
        elif revenue >= 1_000_000:
            score += 20
        elif revenue > 0:
            score += 10
        if lead.current_logistics_provider:
            score += 10  # actively shipping today
        if lead.phone and lead.email:
            score += 10
        if lead.priority in ("high", "urgent"):
            score += 10
        return min(score, 100)

    def create_lead(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmLead:
        data.setdefault("assigned_to", _actor(ctx))
        lead = CrmLead(**data)
        lead.lead_score = self.score_lead(lead)
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
        for key, value in data.items():
            setattr(lead, key, value)
        lead.lead_score = self.score_lead(lead)
        db.commit()
        db.refresh(lead)
        if "status" in data and data["status"] != prev_status:
            self.log_activity(
                db,
                entity_type="lead",
                entity_id=lead.id,
                activity_type="status_change",
                subject=f"Status: {prev_status} → {lead.status}",
            )
        return lead

    def delete_lead(self, db: Session, lead_id: str) -> None:
        lead = db.get(CrmLead, lead_id)
        if not lead:
            raise LookupError("lead_not_found")
        db.delete(lead)
        db.commit()

    def convert_lead(
        self,
        db: Session,
        ctx: AdminContext | None,
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

        lead.status = LeadStatus.CONVERTED.value
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

