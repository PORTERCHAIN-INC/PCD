"""Porterchain Merchant CRM — sales engine.

Implements the logistics merchant-acquisition workflow: leads → companies →
deals → quotations → contracts → active merchants, plus the activity timeline,
tasks, dashboard, reporting, and CSV import.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
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


def _now() -> datetime:
    return datetime.now(UTC)


def _today() -> date:
    return _now().date()


def _actor(ctx: AdminContext | None) -> str | None:
    return ctx.user.id if ctx and ctx.user else None


# Canadian postal FSA first letter → province/territory code.
_POSTAL_PROVINCE = {
    "A": "NL",
    "B": "NS",
    "C": "PE",
    "E": "NB",
    "G": "QC",
    "H": "QC",
    "J": "QC",
    "K": "ON",
    "L": "ON",
    "M": "ON",
    "N": "ON",
    "P": "ON",
    "R": "MB",
    "S": "SK",
    "T": "AB",
    "V": "BC",
    "X": "NT",
    "Y": "YT",
}


def province_from_postal(postal: str | None) -> str | None:
    if not postal:
        return None
    first = postal.strip()[:1].upper()
    return _POSTAL_PROVINCE.get(first)


class CrmSalesService:
    # ------------------------------------------------------------------ #
    # Activity timeline
    # ------------------------------------------------------------------ #
    def log_activity(
        self,
        db: Session,
        *,
        entity_type: str,
        entity_id: str,
        activity_type: str = "note",
        subject: str | None = None,
        body: str | None = None,
        metadata: dict | None = None,
        actor_id: str | None = None,
        occurred_at: datetime | None = None,
        commit: bool = True,
    ) -> CrmActivity:
        activity = CrmActivity(
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type=activity_type,
            subject=subject,
            body=body,
            metadata_json=metadata or {},
            actor_id=actor_id,
            occurred_at=occurred_at or _now(),
        )
        db.add(activity)
        if commit:
            db.commit()
            db.refresh(activity)
        return activity

    def list_activities(
        self, db: Session, *, entity_type: str | None = None, entity_id: str | None = None, limit: int = 100
    ) -> list[CrmActivity]:
        q = db.query(CrmActivity)
        if entity_type:
            q = q.filter(CrmActivity.entity_type == entity_type)
        if entity_id:
            q = q.filter(CrmActivity.entity_id == entity_id)
        return q.order_by(CrmActivity.occurred_at.desc()).limit(limit).all()

    @staticmethod
    def activity_dict(a: CrmActivity) -> dict[str, Any]:
        return {
            "id": a.id,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "activity_type": a.activity_type,
            "subject": a.subject,
            "body": a.body,
            "metadata": a.metadata_json or {},
            "actor_id": a.actor_id,
            "occurred_at": a.occurred_at,
            "created_at": a.created_at,
        }

    # ------------------------------------------------------------------ #
    # Companies
    # ------------------------------------------------------------------ #
    def list_companies(
        self,
        db: Session,
        *,
        search: str | None = None,
        merchant_status: str | None = None,
        owner_id: str | None = None,
        industry: str | None = None,
        city: str | None = None,
        province: str | None = None,
        pinned: bool | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[CrmCompany]:
        q = db.query(CrmCompany)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    CrmCompany.legal_name.ilike(like),
                    CrmCompany.operating_name.ilike(like),
                    CrmCompany.email.ilike(like),
                    CrmCompany.industry.ilike(like),
                    CrmCompany.service_area.ilike(like),
                )
            )
        if merchant_status:
            q = q.filter(CrmCompany.merchant_status == merchant_status)
        if owner_id:
            q = q.filter(CrmCompany.owner_id == owner_id)
        if industry:
            q = q.filter(CrmCompany.industry == industry)
        if city:
            q = q.filter(func.json_extract(CrmCompany.address, "$.city") == city)
        if province:
            q = q.filter(func.json_extract(CrmCompany.address, "$.province") == province)
        if pinned is not None:
            q = q.filter(CrmCompany.is_pinned == pinned)
        return (
            q.order_by(CrmCompany.is_pinned.desc(), CrmCompany.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def company_facets(self, db: Session) -> dict[str, list]:
        industries = sorted(
            {row[0] for row in db.query(CrmCompany.industry).distinct().all() if row[0]}
        )
        status_rows = (
            db.query(CrmCompany.merchant_status, func.count(CrmCompany.id))
            .group_by(CrmCompany.merchant_status)
            .all()
        )
        statuses = [{"value": s, "count": n} for s, n in status_rows if s]

        city_expr = func.json_extract(CrmCompany.address, "$.city")
        province_expr = func.json_extract(CrmCompany.address, "$.province")
        city_rows = (
            db.query(city_expr, func.count(CrmCompany.id)).filter(city_expr.isnot(None)).group_by(city_expr).all()
        )
        cities = sorted(
            ({"name": c, "count": n} for c, n in city_rows if c), key=lambda x: (-x["count"], x["name"])
        )
        province_rows = (
            db.query(province_expr, func.count(CrmCompany.id))
            .filter(province_expr.isnot(None))
            .group_by(province_expr)
            .all()
        )
        provinces = sorted(
            ({"code": p, "count": n} for p, n in province_rows if p), key=lambda x: (-x["count"], x["code"])
        )
        return {
            "industries": industries,
            "statuses": statuses,
            "cities": cities,
            "provinces": provinces,
        }

    def company_stats(self, db: Session) -> dict[str, Any]:
        total = db.query(func.count(CrmCompany.id)).scalar() or 0
        active_merchants = (
            db.query(func.count(CrmCompany.id))
            .filter(CrmCompany.merchant_status == CompanyMerchantStatus.ACTIVE_MERCHANT.value)
            .scalar()
            or 0
        )
        with_merchant = (
            db.query(func.count(CrmCompany.id)).filter(CrmCompany.merchant_id.isnot(None)).scalar() or 0
        )
        pipeline_value = (
            db.query(func.coalesce(func.sum(CrmCompany.estimated_monthly_revenue_cents), 0)).scalar() or 0
        )
        by_status = [
            {"status": s, "count": n}
            for s, n in db.query(CrmCompany.merchant_status, func.count(CrmCompany.id))
            .group_by(CrmCompany.merchant_status)
            .all()
        ]
        by_industry = sorted(
            (
                {"industry": i or "Unknown", "count": n}
                for i, n in db.query(CrmCompany.industry, func.count(CrmCompany.id))
                .group_by(CrmCompany.industry)
                .all()
            ),
            key=lambda x: -x["count"],
        )[:8]
        province_expr = func.json_extract(CrmCompany.address, "$.province")
        by_province = sorted(
            (
                {"province": p or "—", "count": n}
                for p, n in db.query(province_expr, func.count(CrmCompany.id)).group_by(province_expr).all()
            ),
            key=lambda x: -x["count"],
        )[:8]
        top = (
            db.query(CrmCompany)
            .filter(CrmCompany.estimated_monthly_revenue_cents.isnot(None))
            .order_by(CrmCompany.estimated_monthly_revenue_cents.desc())
            .limit(8)
            .all()
        )
        top_companies = [
            {
                "id": c.id,
                "name": c.operating_name or c.legal_name,
                "value_cents": c.estimated_monthly_revenue_cents or 0,
                "merchant_status": c.merchant_status,
            }
            for c in top
        ]
        return {
            "total": total,
            "active_merchants": active_merchants,
            "converted": with_merchant,
            "conversion_rate_percent": round((with_merchant / total * 100) if total else 0.0, 1),
            "monthly_pipeline_value_cents": pipeline_value,
            "by_status": by_status,
            "by_industry": by_industry,
            "by_province": by_province,
            "top_companies": top_companies,
        }

    # ------------------------------------------------------------------ #
    # Invoices (company-scoped)
    # ------------------------------------------------------------------ #
    def list_invoices(self, db: Session, *, company_id: str | None = None, status: str | None = None, limit: int = 200):
        q = db.query(CrmInvoice)
        if company_id:
            q = q.filter(CrmInvoice.company_id == company_id)
        if status:
            q = q.filter(CrmInvoice.status == status)
        return q.order_by(CrmInvoice.created_at.desc()).limit(limit).all()

    def create_invoice(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmInvoice:
        line_items = [li if isinstance(li, dict) else li.model_dump() for li in data.get("line_items", [])]
        amount = data.get("amount_cents") or sum(
            int(li.get("amount_cents") or li.get("quantity", 1) * li.get("unit_price_cents", 0)) for li in line_items
        )
        for li in line_items:
            if not li.get("amount_cents"):
                li["amount_cents"] = int(li.get("quantity", 1) * li.get("unit_price_cents", 0))
        tax = data.get("tax_cents", 0)
        invoice = CrmInvoice(
            invoice_number=self._next_number(db, CrmInvoice, "invoice_number", "INV"),
            company_id=data.get("company_id"),
            deal_id=data.get("deal_id"),
            contract_id=data.get("contract_id"),
            amount_cents=amount,
            tax_cents=tax,
            total_cents=amount + tax,
            currency=data.get("currency", "cad"),
            net_terms=data.get("net_terms", "NET_30"),
            line_items=line_items,
            notes=data.get("notes"),
            issue_date=data.get("issue_date"),
            due_date=data.get("due_date"),
            created_by=_actor(ctx),
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        if invoice.company_id:
            self.log_activity(
                db, entity_type="company", entity_id=invoice.company_id, activity_type="system",
                subject=f"Invoice {invoice.invoice_number} created", actor_id=_actor(ctx),
            )
        return invoice

    def update_invoice(self, db: Session, ctx: AdminContext | None, invoice_id: str, data: dict) -> CrmInvoice:
        invoice = db.get(CrmInvoice, invoice_id)
        if not invoice:
            raise LookupError("invoice_not_found")
        for key, value in data.items():
            setattr(invoice, key, value)
        invoice.total_cents = invoice.amount_cents + invoice.tax_cents
        if data.get("status") == "paid" and not invoice.paid_at:
            invoice.paid_at = _now()
        db.commit()
        db.refresh(invoice)
        return invoice

    def get_company(self, db: Session, company_id: str) -> CrmCompany | None:
        return db.get(CrmCompany, company_id)

    def find_company_duplicate(self, db: Session, *, legal_name: str, email: str | None) -> CrmCompany | None:
        q = db.query(CrmCompany).filter(func.lower(CrmCompany.legal_name) == legal_name.lower())
        existing = q.first()
        if existing:
            return existing
        if email:
            return db.query(CrmCompany).filter(func.lower(CrmCompany.email) == email.lower()).first()
        return None

    def create_company(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmCompany:
        data.setdefault("owner_id", _actor(ctx))
        company = CrmCompany(**data)
        db.add(company)
        db.commit()
        db.refresh(company)
        self.log_activity(
            db,
            entity_type="company",
            entity_id=company.id,
            activity_type="system",
            subject="Company created",
            actor_id=_actor(ctx),
        )
        return company

    def update_company(self, db: Session, company_id: str, data: dict) -> CrmCompany:
        company = db.get(CrmCompany, company_id)
        if not company:
            raise LookupError("company_not_found")
        for key, value in data.items():
            setattr(company, key, value)
        db.commit()
        db.refresh(company)
        return company

    def delete_company(self, db: Session, company_id: str) -> None:
        company = db.get(CrmCompany, company_id)
        if not company:
            raise LookupError("company_not_found")
        db.delete(company)
        db.commit()

    def backfill_companies_from_leads(self, db: Session, *, batch: int = 500) -> dict[str, int]:
        """Create/link a Company for every lead that doesn't have one yet.

        Does NOT create deals and does NOT mark leads converted — it simply makes
        the underlying account visible in the Companies module and links the lead
        to it (lead.company_id).
        """
        existing: dict[str, str] = {
            (c.legal_name or "").lower(): c.id for c in db.query(CrmCompany).all()
        }
        leads = db.query(CrmLead).filter(CrmLead.company_id.is_(None)).all()

        created = 0
        linked = 0
        pending = 0
        for lead in leads:
            key = (lead.company_name or "").strip().lower()
            if not key:
                continue
            company_id = existing.get(key)
            if not company_id:
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
                    merchant_status=CompanyMerchantStatus.LEAD.value,
                    owner_id=lead.assigned_to,
                    tags=list(lead.tags or []),
                    custom_fields=dict(lead.custom_fields or {}),
                )
                db.add(company)
                db.flush()
                company_id = company.id
                existing[key] = company_id
                created += 1
                pending += 1
            lead.company_id = company_id
            linked += 1
            if pending >= batch:
                db.commit()
                pending = 0
        db.commit()
        return {"companies_created": created, "leads_linked": linked}

    # ------------------------------------------------------------------ #
    # Contacts
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Leads
    # ------------------------------------------------------------------ #
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
            q = q.filter(func.json_extract(CrmLead.address, "$.city") == city)
        if province:
            q = q.filter(func.json_extract(CrmLead.address, "$.province") == province)
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

        city_expr = func.json_extract(CrmLead.address, "$.city")
        province_expr = func.json_extract(CrmLead.address, "$.province")

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

    # ------------------------------------------------------------------ #
    # Deals / pipeline
    # ------------------------------------------------------------------ #
    def list_deals(
        self,
        db: Session,
        *,
        stage: str | None = None,
        owner_id: str | None = None,
        company_id: str | None = None,
        limit: int = 500,
    ) -> list[CrmDeal]:
        q = db.query(CrmDeal)
        if stage:
            q = q.filter(CrmDeal.stage == stage)
        if owner_id:
            q = q.filter(CrmDeal.owner_id == owner_id)
        if company_id:
            q = q.filter(CrmDeal.company_id == company_id)
        return q.order_by(CrmDeal.position.asc(), CrmDeal.updated_at.desc()).limit(limit).all()

    def get_deal(self, db: Session, deal_id: str) -> CrmDeal | None:
        return db.get(CrmDeal, deal_id)

    def deal_with_company_name(self, db: Session, deal: CrmDeal) -> dict:
        company = db.get(CrmCompany, deal.company_id) if deal.company_id else None
        data = {c.name: getattr(deal, c.name) for c in deal.__table__.columns}
        data["company_name"] = company.legal_name if company else None
        return data

    def board(self, db: Session) -> list[dict]:
        deals = self.list_deals(db, limit=1000)
        by_stage: dict[str, list] = {stage: [] for stage in PIPELINE_STAGES}
        by_stage.setdefault(DealStage.HOLD.value, [])
        companies = {c.id: c for c in db.query(CrmCompany).all()}
        for d in deals:
            company = companies.get(d.company_id)
            entry = {c.name: getattr(d, c.name) for c in d.__table__.columns}
            entry["company_name"] = company.legal_name if company else None
            by_stage.setdefault(d.stage, []).append(entry)
        columns = []
        for stage in [*PIPELINE_STAGES, DealStage.HOLD.value]:
            items = by_stage.get(stage, [])
            columns.append(
                {
                    "stage": stage,
                    "deals": items,
                    "count": len(items),
                    "value_cents": sum(i["expected_revenue_cents"] for i in items),
                }
            )
        return columns

    # Lead status → pipeline column for the unified acquisition board.
    LEAD_STATUS_TO_STAGE = {
        LeadStatus.NEW.value: DealStage.PROSPECTING.value,
        LeadStatus.CONTACTED.value: DealStage.PROSPECTING.value,
        LeadStatus.QUALIFIED.value: DealStage.QUALIFIED.value,
        LeadStatus.NURTURING.value: DealStage.QUALIFIED.value,
        LeadStatus.UNQUALIFIED.value: DealStage.LOST.value,
    }
    # Reverse: dropping a lead into one of these columns just updates its status.
    STAGE_TO_LEAD_STATUS = {
        DealStage.PROSPECTING.value: LeadStatus.CONTACTED.value,
        DealStage.QUALIFIED.value: LeadStatus.QUALIFIED.value,
        DealStage.LOST.value: LeadStatus.UNQUALIFIED.value,
    }
    LEAD_CARD_CAP = 50

    def pipeline_board(
        self,
        db: Session,
        *,
        search: str | None = None,
        card_type: str | None = None,
        min_value_cents: int | None = None,
    ) -> list[dict]:
        """Unified merchant-acquisition board: un-converted leads + deals.

        Supports advanced search applied server-side (before the per-column lead
        cap) so it reaches the full dataset, not just visible cards.
        """
        term = (search or "").strip().lower()
        companies = {c.id: c for c in db.query(CrmCompany).all()}
        all_stages = [*PIPELINE_STAGES, DealStage.HOLD.value]
        columns: dict[str, dict] = {
            stage: {
                "stage": stage,
                "cards": [],
                "count": 0,
                "value_cents": 0,
                "hidden": 0,
                "lead_count": 0,
                "deal_count": 0,
            }
            for stage in all_stages
        }

        include_deals = card_type != "lead"
        include_leads = card_type != "deal"

        # Deals (always shown when not filtered out).
        for d in self.list_deals(db, limit=2000) if include_deals else []:
            company = companies.get(d.company_id)
            company_name = company.legal_name if company else None
            if min_value_cents and d.expected_revenue_cents < min_value_cents:
                continue
            if term and term not in d.name.lower() and term not in (company_name or "").lower():
                continue
            col = columns.setdefault(
                d.stage,
                {"stage": d.stage, "cards": [], "count": 0, "value_cents": 0, "hidden": 0, "lead_count": 0, "deal_count": 0},
            )
            col["cards"].append(
                {
                    "type": "deal",
                    "id": d.id,
                    "title": d.name,
                    "company_name": company.legal_name if company else None,
                    "value_cents": d.expected_revenue_cents,
                    "secondary": f"{d.probability}% win",
                    "stage": d.stage,
                    "probability": d.probability,
                    "location": None,
                }
            )
            col["count"] += 1
            col["deal_count"] += 1
            col["value_cents"] += d.expected_revenue_cents

        # Leads grouped by mapped stage, capped per column (sorted by score).
        leads = []
        if include_leads:
            leads_q = db.query(CrmLead).filter(CrmLead.status != LeadStatus.CONVERTED.value)
            if min_value_cents:
                leads_q = leads_q.filter(
                    func.coalesce(CrmLead.estimated_revenue_cents, 0) >= min_value_cents
                )
            if term:
                like = f"%{term}%"
                leads_q = leads_q.filter(
                    or_(
                        func.lower(CrmLead.company_name).like(like),
                        func.lower(func.json_extract(CrmLead.address, "$.city")).like(like),
                        func.lower(func.json_extract(CrmLead.address, "$.province")).like(like),
                        func.lower(func.coalesce(CrmLead.service_area, "")).like(like),
                    )
                )
            leads = leads_q.order_by(CrmLead.lead_score.desc(), CrmLead.created_at.desc()).all()
        for lead in leads:
            stage = self.LEAD_STATUS_TO_STAGE.get(lead.status, DealStage.PROSPECTING.value)
            col = columns[stage]
            col["count"] += 1
            col["lead_count"] += 1
            col["value_cents"] += lead.estimated_revenue_cents or 0
            if col["lead_count"] <= self.LEAD_CARD_CAP:
                addr = lead.address or {}
                location = ", ".join(p for p in [addr.get("city"), addr.get("province")] if p) or None
                col["cards"].append(
                    {
                        "type": "lead",
                        "id": lead.id,
                        "title": lead.company_name,
                        "company_name": location,
                        "value_cents": lead.estimated_revenue_cents or 0,
                        "secondary": f"Score {lead.lead_score}",
                        "stage": stage,
                        "score": lead.lead_score,
                        "location": location,
                    }
                )
            else:
                col["hidden"] += 1

        return [columns[stage] for stage in all_stages]

    def create_deal(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmDeal:
        data.setdefault("owner_id", _actor(ctx))
        if "probability" not in data or data.get("probability") is None:
            data["probability"] = STAGE_PROBABILITY.get(data.get("stage", DealStage.PROSPECTING.value), 10)
        deal = CrmDeal(**data)
        db.add(deal)
        db.commit()
        db.refresh(deal)
        self.log_activity(
            db, entity_type="deal", entity_id=deal.id, activity_type="system",
            subject="Deal created", actor_id=_actor(ctx),
        )
        return deal

    def update_deal(self, db: Session, ctx: AdminContext | None, deal_id: str, data: dict) -> CrmDeal:
        deal = db.get(CrmDeal, deal_id)
        if not deal:
            raise LookupError("deal_not_found")
        prev_stage = deal.stage
        for key, value in data.items():
            setattr(deal, key, value)
        if "stage" in data and data["stage"] != prev_stage:
            self._apply_stage_change(db, ctx, deal, prev_stage)
        db.commit()
        db.refresh(deal)
        return deal

    def move_deal(self, db: Session, ctx: AdminContext | None, deal_id: str, stage: str, position: int) -> CrmDeal:
        deal = db.get(CrmDeal, deal_id)
        if not deal:
            raise LookupError("deal_not_found")
        prev_stage = deal.stage
        deal.stage = stage
        deal.position = position
        if stage != prev_stage:
            self._apply_stage_change(db, ctx, deal, prev_stage)
        db.commit()
        db.refresh(deal)
        return deal

    def _apply_stage_change(self, db: Session, ctx: AdminContext | None, deal: CrmDeal, prev_stage: str) -> None:
        deal.probability = STAGE_PROBABILITY.get(deal.stage, deal.probability)
        if deal.stage in (DealStage.WON.value, DealStage.LOST.value):
            deal.closed_at = _now()
        self.log_activity(
            db,
            entity_type="deal",
            entity_id=deal.id,
            activity_type="status_change",
            subject=f"Stage: {prev_stage} → {deal.stage}",
            actor_id=_actor(ctx),
            commit=False,
        )
        # Auto-advance company status as the deal matures.
        if deal.company_id and deal.stage == DealStage.WON.value:
            company = db.get(CrmCompany, deal.company_id)
            if company and company.merchant_status != CompanyMerchantStatus.ACTIVE_MERCHANT.value:
                company.merchant_status = CompanyMerchantStatus.NEGOTIATING.value

    def delete_deal(self, db: Session, deal_id: str) -> None:
        deal = db.get(CrmDeal, deal_id)
        if not deal:
            raise LookupError("deal_not_found")
        db.delete(deal)
        db.commit()

    # ------------------------------------------------------------------ #
    # Quotations
    # ------------------------------------------------------------------ #
    def _next_number(self, db: Session, model, attr: str, prefix: str) -> str:
        year = _today().year
        count = db.query(func.count()).select_from(model).scalar() or 0
        return f"{prefix}-{year}-{count + 1:04d}"

    def list_quotations(
        self, db: Session, *, deal_id: str | None = None, company_id: str | None = None, limit: int = 200
    ) -> list[CrmQuotation]:
        q = db.query(CrmQuotation)
        if deal_id:
            q = q.filter(CrmQuotation.deal_id == deal_id)
        if company_id:
            q = q.filter(CrmQuotation.company_id == company_id)
        return q.order_by(CrmQuotation.created_at.desc()).limit(limit).all()

    def get_quotation(self, db: Session, quotation_id: str) -> CrmQuotation | None:
        return db.get(CrmQuotation, quotation_id)

    @staticmethod
    def _quote_totals(line_items: list[dict], tax_cents: int) -> tuple[int, int]:
        subtotal = 0
        for item in line_items:
            amount = item.get("amount_cents")
            if not amount:
                amount = int(item.get("quantity", 1) * item.get("unit_price_cents", 0))
                item["amount_cents"] = amount
            subtotal += amount
        return subtotal, subtotal + tax_cents

    def create_quotation(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmQuotation:
        line_items = [li if isinstance(li, dict) else li.model_dump() for li in data.get("line_items", [])]
        subtotal, total = self._quote_totals(line_items, data.get("tax_cents", 0))
        quotation = CrmQuotation(
            quote_number=self._next_number(db, CrmQuotation, "quote_number", "Q"),
            version=1,
            deal_id=data.get("deal_id"),
            company_id=data.get("company_id"),
            line_items=line_items,
            subtotal_cents=subtotal,
            tax_cents=data.get("tax_cents", 0),
            total_cents=total,
            currency=data.get("currency", "cad"),
            valid_until=data.get("valid_until"),
            notes=data.get("notes"),
            created_by=_actor(ctx),
        )
        db.add(quotation)
        db.commit()
        db.refresh(quotation)
        if quotation.deal_id:
            self.log_activity(
                db, entity_type="deal", entity_id=quotation.deal_id, activity_type="system",
                subject=f"Quotation {quotation.quote_number} created", actor_id=_actor(ctx),
            )
        return quotation

    def revise_quotation(self, db: Session, ctx: AdminContext | None, quotation_id: str, data: dict) -> CrmQuotation:
        """Create a new version of an existing quotation."""
        base = db.get(CrmQuotation, quotation_id)
        if not base:
            raise LookupError("quotation_not_found")
        line_items = [li if isinstance(li, dict) else li.model_dump() for li in data.get("line_items", base.line_items)]
        tax_cents = data.get("tax_cents", base.tax_cents)
        subtotal, total = self._quote_totals(line_items, tax_cents)
        latest = (
            db.query(func.max(CrmQuotation.version))
            .filter(CrmQuotation.quote_number == base.quote_number)
            .scalar()
            or base.version
        )
        revision = CrmQuotation(
            quote_number=base.quote_number,
            version=latest + 1,
            deal_id=base.deal_id,
            company_id=base.company_id,
            line_items=line_items,
            subtotal_cents=subtotal,
            tax_cents=tax_cents,
            total_cents=total,
            currency=base.currency,
            valid_until=data.get("valid_until", base.valid_until),
            notes=data.get("notes", base.notes),
            created_by=_actor(ctx),
        )
        db.add(revision)
        db.commit()
        db.refresh(revision)
        return revision

    def update_quotation_status(
        self, db: Session, ctx: AdminContext | None, quotation_id: str, status: str
    ) -> CrmQuotation:
        quotation = db.get(CrmQuotation, quotation_id)
        if not quotation:
            raise LookupError("quotation_not_found")
        quotation.status = status
        if status == QuotationStatus.SENT.value:
            quotation.sent_at = _now()
        if status == QuotationStatus.APPROVED.value:
            quotation.approved_by = _actor(ctx)
        db.commit()
        db.refresh(quotation)
        return quotation

    def convert_quotation_to_contract(
        self, db: Session, ctx: AdminContext | None, quotation_id: str
    ) -> CrmContract:
        quotation = db.get(CrmQuotation, quotation_id)
        if not quotation:
            raise LookupError("quotation_not_found")
        contract = self.create_contract(
            db,
            ctx,
            {
                "company_id": quotation.company_id,
                "deal_id": quotation.deal_id,
                "quotation_id": quotation.id,
                "value_cents": quotation.total_cents,
            },
        )
        quotation.status = QuotationStatus.CONVERTED.value
        db.commit()
        return contract

    # ------------------------------------------------------------------ #
    # Contracts
    # ------------------------------------------------------------------ #
    def list_contracts(
        self, db: Session, *, company_id: str | None = None, status: str | None = None, limit: int = 200
    ) -> list[CrmContract]:
        q = db.query(CrmContract)
        if company_id:
            q = q.filter(CrmContract.company_id == company_id)
        if status:
            q = q.filter(CrmContract.status == status)
        return q.order_by(CrmContract.created_at.desc()).limit(limit).all()

    def get_contract(self, db: Session, contract_id: str) -> CrmContract | None:
        return db.get(CrmContract, contract_id)

    def create_contract(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmContract:
        contract = CrmContract(
            contract_number=self._next_number(db, CrmContract, "contract_number", "C"),
            created_by=_actor(ctx),
            **data,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        if contract.company_id:
            self.log_activity(
                db, entity_type="company", entity_id=contract.company_id, activity_type="system",
                subject=f"Contract {contract.contract_number} created", actor_id=_actor(ctx),
            )
        return contract

    def update_contract(self, db: Session, contract_id: str, data: dict) -> CrmContract:
        contract = db.get(CrmContract, contract_id)
        if not contract:
            raise LookupError("contract_not_found")
        for key, value in data.items():
            setattr(contract, key, value)
        db.commit()
        db.refresh(contract)
        return contract

    # ------------------------------------------------------------------ #
    # Merchant conversion (one-click)
    # ------------------------------------------------------------------ #
    def convert_company_to_merchant(
        self, db: Session, ctx: AdminContext | None, company_id: str
    ) -> dict[str, Any]:
        company = db.get(CrmCompany, company_id)
        if not company:
            raise LookupError("company_not_found")
        if company.merchant_id:
            return {"merchant_id": company.merchant_id, "created": False, "invitation_sent": False}

        primary = (
            db.query(CrmContact)
            .filter(CrmContact.company_id == company.id, CrmContact.is_primary == True)  # noqa: E712
            .first()
        )
        email = (primary.email if primary else None) or company.email or ""
        merchant = Merchant(
            status=MerchantStatus.PENDING.value,
            company_name=company.operating_name or company.legal_name,
            legal_name=company.legal_name,
            email=email,
            phone=company.phone,
            hst_number=company.hst_number,
            business_number=company.business_number,
            billing_address=company.billing_details or company.address or {},
            preferred_vehicles=[company.preferred_vehicle] if company.preferred_vehicle else [],
            profile={
                "crm_company_id": company.id,
                "industry": company.industry,
                "service_area": company.service_area,
                "estimated_deliveries_per_month": company.estimated_deliveries_per_month,
            },
        )
        db.add(merchant)
        db.flush()

        company.merchant_id = merchant.id
        company.merchant_status = CompanyMerchantStatus.ACTIVE_MERCHANT.value
        db.commit()
        db.refresh(merchant)

        self.log_activity(
            db,
            entity_type="company",
            entity_id=company.id,
            activity_type="status_change",
            subject="Converted to Porterchain merchant",
            metadata={"merchant_id": merchant.id, "invitation_email": email},
            actor_id=_actor(ctx),
        )
        # Clerk account + invitation are dispatched asynchronously by the merchant
        # onboarding pipeline once the merchant record exists.
        return {
            "merchant_id": merchant.id,
            "created": True,
            "invitation_sent": bool(email),
            "invitation_email": email,
        }

    # ------------------------------------------------------------------ #
    # Tasks
    # ------------------------------------------------------------------ #
    def list_tasks(
        self,
        db: Session,
        *,
        status: str | None = None,
        assigned_to: str | None = None,
        entity_id: str | None = None,
        due_before: datetime | None = None,
        limit: int = 300,
    ) -> list[CrmSalesTask]:
        q = db.query(CrmSalesTask)
        if status:
            q = q.filter(CrmSalesTask.status == status)
        if assigned_to:
            q = q.filter(CrmSalesTask.assigned_to == assigned_to)
        if entity_id:
            q = q.filter(CrmSalesTask.entity_id == entity_id)
        if due_before:
            q = q.filter(CrmSalesTask.due_at <= due_before)
        return q.order_by(CrmSalesTask.due_at.asc().nullslast()).limit(limit).all()

    def get_task(self, db: Session, task_id: str) -> CrmSalesTask | None:
        return db.get(CrmSalesTask, task_id)

    def create_task(self, db: Session, ctx: AdminContext | None, data: dict) -> CrmSalesTask:
        data.setdefault("assigned_to", _actor(ctx))
        task = CrmSalesTask(created_by=_actor(ctx), **data)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def update_task(self, db: Session, task_id: str, data: dict) -> CrmSalesTask:
        task = db.get(CrmSalesTask, task_id)
        if not task:
            raise LookupError("task_not_found")
        for key, value in data.items():
            setattr(task, key, value)
        if data.get("status") == TaskStatus.DONE.value and not task.completed_at:
            task.completed_at = _now()
        db.commit()
        db.refresh(task)
        return task

    def delete_task(self, db: Session, task_id: str) -> None:
        task = db.get(CrmSalesTask, task_id)
        if not task:
            raise LookupError("task_not_found")
        db.delete(task)
        db.commit()

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #
    def dashboard(self, db: Session) -> dict[str, Any]:
        today = _today()
        start_of_day = datetime.combine(today, time.min, tzinfo=UTC)
        end_of_day = datetime.combine(today, time.max, tzinfo=UTC)
        start_of_month = datetime.combine(today.replace(day=1), time.min, tzinfo=UTC)

        new_leads = (
            db.query(func.count(CrmLead.id)).filter(CrmLead.status == LeadStatus.NEW.value).scalar() or 0
        )
        todays_follow_ups = (
            db.query(func.count(CrmSalesTask.id))
            .filter(
                CrmSalesTask.status.in_([TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value]),
                CrmSalesTask.due_at >= start_of_day,
                CrmSalesTask.due_at <= end_of_day,
            )
            .scalar()
            or 0
        )
        overdue_tasks = (
            db.query(func.count(CrmSalesTask.id))
            .filter(
                CrmSalesTask.status.in_([TaskStatus.OPEN.value, TaskStatus.IN_PROGRESS.value]),
                CrmSalesTask.due_at < start_of_day,
            )
            .scalar()
            or 0
        )
        meetings_today = (
            db.query(func.count(CrmSalesTask.id))
            .filter(
                CrmSalesTask.task_type.in_(["meeting", "demo", "merchant_visit"]),
                CrmSalesTask.due_at >= start_of_day,
                CrmSalesTask.due_at <= end_of_day,
            )
            .scalar()
            or 0
        )
        contracts_pending = (
            db.query(func.count(CrmContract.id))
            .filter(CrmContract.status.in_([ContractStatus.DRAFT.value, ContractStatus.PENDING_SIGNATURE.value]))
            .scalar()
            or 0
        )
        quotes_pending = (
            db.query(func.count(CrmQuotation.id))
            .filter(CrmQuotation.status.in_([QuotationStatus.DRAFT.value, QuotationStatus.SENT.value]))
            .scalar()
            or 0
        )
        merchant_conversions = (
            db.query(func.count(CrmCompany.id))
            .filter(
                CrmCompany.merchant_status == CompanyMerchantStatus.ACTIVE_MERCHANT.value,
                CrmCompany.updated_at >= start_of_month,
            )
            .scalar()
            or 0
        )

        open_deals_q = db.query(CrmDeal).filter(
            CrmDeal.stage.notin_([DealStage.WON.value, DealStage.LOST.value])
        )
        open_deals = open_deals_q.all()
        pipeline_value = sum(d.expected_revenue_cents for d in open_deals)
        forecast = sum(int(d.expected_revenue_cents * (d.probability / 100)) for d in open_deals)

        won_this_month = (
            db.query(func.count(CrmDeal.id))
            .filter(CrmDeal.stage == DealStage.WON.value, CrmDeal.closed_at >= start_of_month)
            .scalar()
            or 0
        )
        active_companies = (
            db.query(func.count(CrmCompany.id))
            .filter(CrmCompany.merchant_status != CompanyMerchantStatus.CHURNED.value)
            .scalar()
            or 0
        )

        recent = self.list_activities(db, limit=12)
        recent_activities = [
            {
                "id": a.id,
                "entity_type": a.entity_type,
                "entity_id": a.entity_id,
                "activity_type": a.activity_type,
                "subject": a.subject,
                "occurred_at": a.occurred_at.isoformat(),
            }
            for a in recent
        ]

        lead_sources_rows = (
            db.query(CrmLead.source, func.count(CrmLead.id)).group_by(CrmLead.source).all()
        )
        lead_sources = [{"source": s or "unknown", "count": c} for s, c in lead_sources_rows]

        reps_rows = (
            db.query(CrmDeal.owner_id, func.count(CrmDeal.id), func.sum(CrmDeal.expected_revenue_cents))
            .filter(CrmDeal.stage == DealStage.WON.value)
            .group_by(CrmDeal.owner_id)
            .all()
        )
        top_sales_reps = [
            {"owner_id": owner or "unassigned", "won_deals": count, "revenue_cents": int(rev or 0)}
            for owner, count, rev in reps_rows
        ]
        top_sales_reps.sort(key=lambda r: r["revenue_cents"], reverse=True)

        pipeline_by_stage = []
        for stage in PIPELINE_STAGES:
            rows = [d for d in open_deals if d.stage == stage]
            pipeline_by_stage.append(
                {
                    "stage": stage,
                    "count": len(rows),
                    "value_cents": sum(d.expected_revenue_cents for d in rows),
                }
            )

        return {
            "new_leads": new_leads,
            "todays_follow_ups": todays_follow_ups,
            "overdue_tasks": overdue_tasks,
            "meetings_today": meetings_today,
            "contracts_pending": contracts_pending,
            "quotes_pending": quotes_pending,
            "merchant_conversions": merchant_conversions,
            "pipeline_value_cents": pipeline_value,
            "monthly_revenue_forecast_cents": forecast,
            "open_deals": len(open_deals),
            "won_deals_this_month": won_this_month,
            "active_companies": active_companies,
            "recent_activities": recent_activities,
            "lead_sources": lead_sources,
            "top_sales_reps": top_sales_reps[:5],
            "pipeline_by_stage": pipeline_by_stage,
        }

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #
    def reports(self, db: Session) -> dict[str, Any]:
        deals = db.query(CrmDeal).all()
        won = [d for d in deals if d.stage == DealStage.WON.value]
        lost = [d for d in deals if d.stage == DealStage.LOST.value]
        open_deals = [d for d in deals if d.stage not in (DealStage.WON.value, DealStage.LOST.value)]
        closed = len(won) + len(lost)
        conversion = (len(won) / closed * 100) if closed else 0.0

        pipeline = []
        for stage in PIPELINE_STAGES:
            rows = [d for d in deals if d.stage == stage]
            pipeline.append(
                {
                    "stage": stage,
                    "count": len(rows),
                    "value_cents": sum(d.expected_revenue_cents for d in rows),
                }
            )

        forecast = sum(int(d.expected_revenue_cents * (d.probability / 100)) for d in open_deals)

        lead_rows = db.query(CrmLead.source, func.count(CrmLead.id)).group_by(CrmLead.source).all()
        lead_sources = [{"source": s or "unknown", "count": c} for s, c in lead_rows]

        reps_rows = (
            db.query(CrmDeal.owner_id, func.count(CrmDeal.id), func.sum(CrmDeal.expected_revenue_cents))
            .group_by(CrmDeal.owner_id)
            .all()
        )
        sales_performance = [
            {"owner_id": owner or "unassigned", "deals": count, "revenue_cents": int(rev or 0)}
            for owner, count, rev in reps_rows
        ]

        # Average time-to-close in days for won deals.
        durations = [
            (d.closed_at - d.created_at).days
            for d in won
            if d.closed_at and d.created_at
        ]
        avg_close = (sum(durations) / len(durations)) if durations else 0.0

        quotations = db.query(CrmQuotation).all()
        quoted = [q for q in quotations if q.status != QuotationStatus.DRAFT.value]
        won_quotes = [q for q in quotations if q.status in (QuotationStatus.APPROVED.value, QuotationStatus.CONVERTED.value)]
        quote_win = (len(won_quotes) / len(quoted) * 100) if quoted else 0.0

        # Simple CAC proxy: assume fixed sales cost per won merchant.
        cac = 75000 if won else 0  # $750 placeholder per acquisition

        return {
            "pipeline": pipeline,
            "conversion_rate_percent": round(conversion, 1),
            "revenue_forecast_cents": forecast,
            "lead_sources": lead_sources,
            "sales_performance": sales_performance,
            "merchant_acquisition_cost_cents": cac,
            "avg_time_to_close_days": round(avg_close, 1),
            "quote_win_rate_percent": round(quote_win, 1),
        }

    # ------------------------------------------------------------------ #
    # CSV import
    # ------------------------------------------------------------------ #
    def import_rows(
        self, db: Session, ctx: AdminContext | None, entity: str, rows: list[dict], dedupe: bool = True
    ) -> dict[str, Any]:
        imported = 0
        duplicates = 0
        errors: list[dict] = []

        for index, row in enumerate(rows):
            try:
                if entity == "companies":
                    name = (row.get("legal_name") or row.get("company_name") or "").strip()
                    if not name:
                        raise ValueError("legal_name is required")
                    if dedupe and self.find_company_duplicate(db, legal_name=name, email=row.get("email")):
                        duplicates += 1
                        continue
                    self.create_company(
                        db,
                        ctx,
                        {
                            "legal_name": name,
                            "operating_name": row.get("operating_name"),
                            "industry": row.get("industry"),
                            "website": row.get("website"),
                            "phone": row.get("phone"),
                            "email": row.get("email"),
                            "service_area": row.get("service_area"),
                            "estimated_deliveries_per_month": _to_int(row.get("estimated_deliveries_per_month")),
                            "merchant_status": row.get("merchant_status") or "lead",
                        },
                    )
                    imported += 1
                elif entity == "contacts":
                    first = (row.get("first_name") or "").strip()
                    if not first:
                        raise ValueError("first_name is required")
                    self.create_contact(
                        db,
                        ctx,
                        {
                            "company_id": row.get("company_id"),
                            "first_name": first,
                            "last_name": row.get("last_name"),
                            "designation": row.get("designation"),
                            "email": row.get("email"),
                            "phone": row.get("phone"),
                            "mobile": row.get("mobile"),
                        },
                    )
                    imported += 1
                elif entity == "leads":
                    company = (row.get("company_name") or "").strip()
                    if not company:
                        raise ValueError("company_name is required")
                    known = {
                        "company_name", "industry", "website", "business_type", "email", "phone",
                        "primary_contact_name", "source", "priority", "status",
                        "estimated_deliveries_per_month", "estimated_revenue_cents",
                        "preferred_vehicle", "service_area", "current_logistics_provider",
                        "street", "city", "province", "postal_code", "country", "address",
                    }
                    address = {
                        k: row[k]
                        for k in ("street", "city", "province", "postal_code", "country")
                        if row.get(k)
                    }
                    # Any column we don't explicitly model is preserved on the lead.
                    extras = {k: v for k, v in row.items() if k not in known and str(v).strip()}
                    self.create_lead(
                        db,
                        ctx,
                        {
                            "company_name": company,
                            "industry": row.get("industry"),
                            "website": row.get("website"),
                            "business_type": row.get("business_type"),
                            "email": row.get("email"),
                            "phone": row.get("phone"),
                            "primary_contact_name": row.get("primary_contact_name"),
                            "source": row.get("source") or "csv_import",
                            "priority": row.get("priority") or "medium",
                            "estimated_deliveries_per_month": _to_int(row.get("estimated_deliveries_per_month")),
                            "estimated_revenue_cents": _to_int(row.get("estimated_revenue_cents")),
                            "preferred_vehicle": row.get("preferred_vehicle"),
                            "service_area": row.get("service_area") or address.get("city"),
                            "current_logistics_provider": row.get("current_logistics_provider"),
                            "address": address,
                            "custom_fields": extras,
                        },
                    )
                    imported += 1
                elif entity == "deals":
                    name = (row.get("name") or "").strip()
                    if not name:
                        raise ValueError("name is required")
                    self.create_deal(
                        db,
                        ctx,
                        {
                            "name": name,
                            "company_id": row.get("company_id"),
                            "stage": row.get("stage") or DealStage.PROSPECTING.value,
                            "expected_revenue_cents": _to_int(row.get("expected_revenue_cents")) or 0,
                        },
                    )
                    imported += 1
                else:
                    raise ValueError(f"unsupported entity '{entity}'")
            except Exception as exc:  # noqa: BLE001 — collect per-row errors
                db.rollback()
                errors.append({"row": index + 1, "error": str(exc)})

        return {
            "entity": entity,
            "total": len(rows),
            "imported": imported,
            "duplicates": duplicates,
            "errors": errors,
        }


def _to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").replace("$", "")))
    except (ValueError, TypeError):
        return None
