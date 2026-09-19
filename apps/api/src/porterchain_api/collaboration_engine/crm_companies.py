"""CRM companies and invoices."""

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



class CrmCompaniesMixin:
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
            q = q.filter(json_text(CrmCompany.address, "city") == city)
        if province:
            q = q.filter(json_text(CrmCompany.address, "province") == province)
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

        city_expr = json_text(CrmCompany.address, "city")
        province_expr = json_text(CrmCompany.address, "province")
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
        province_expr = json_text(CrmCompany.address, "province")
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

    def list_invoices(self, db: Session, *, company_id: str | None = None, status: str | None = None, limit: int = 200):
        q = db.query(CrmInvoice)
        if company_id:
            q = q.filter(CrmInvoice.company_id == company_id)
        if status:
            q = q.filter(CrmInvoice.status == status)
        return q.order_by(CrmInvoice.created_at.desc()).limit(limit).all()

    def create_invoice(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmInvoice:
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

    def update_invoice(self, db: Session, ctx: CrmActor | None, invoice_id: str, data: dict) -> CrmInvoice:
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

    def create_company(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmCompany:
        data.setdefault("owner_id", _actor(ctx))
        company = CrmCompany(**data)
        db.add(company)
        db.flush()
        self._admin_audit(
            db, ctx, action="crm.company.create", resource_type="crm_company", resource_id=company.id
        )
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
        payload = dict(data)
        tax_keys = ("legal_name", "hst_number", "business_number")
        tax_patch = {key: payload.pop(key) for key in list(payload) if key in tax_keys}
        for key, value in payload.items():
            setattr(company, key, value)
        if company.merchant_id and tax_patch:
            from porterchain_api.merchant_engine.lookups import get_merchant
            from porterchain_api.merchant_engine.organization_sync import apply_tax_legal

            merchant = get_merchant(db, company.merchant_id)
            if merchant is not None:
                apply_tax_legal(merchant, actor="admin", actor_id=None, **tax_patch)
                self.project_from_merchant(db, merchant)
            else:
                for key, value in tax_patch.items():
                    setattr(company, key, value)
        else:
            for key, value in tax_patch.items():
                setattr(company, key, value)
        db.flush()
        self._admin_audit(
            db, None, action="crm.company.update", resource_type="crm_company", resource_id=company.id
        )
        db.commit()
        db.refresh(company)
        return company

    def ensure_company_for_merchant(self, db: Session, merchant: Any) -> CrmCompany:
        from porterchain_api.collaboration_engine.repositories import CrmRepository

        repo = CrmRepository()
        company = repo.get_company_by_merchant_id(db, merchant.id)
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

    def set_merchant_status(self, db: Session, merchant_id: str, status: str) -> None:
        company = db.query(CrmCompany).filter(CrmCompany.merchant_id == merchant_id).first()
        if company:
            company.merchant_status = status

    def project_from_merchant(self, db: Session, merchant: Any) -> CrmCompany:
        """Copy operational org fields onto the linked CRM company."""
        from porterchain_api.merchant_engine.coverage import profile_service_area
        from porterchain_api.merchant_engine.organization_sync import (
            branding_logo_url,
            industry_of,
            website_of,
        )

        company = self.ensure_company_for_merchant(db, merchant)
        company.operating_name = getattr(merchant, "company_name", None)
        company.legal_name = getattr(merchant, "legal_name", None) or getattr(merchant, "company_name", None)
        company.email = getattr(merchant, "email", None)
        company.phone = getattr(merchant, "phone", None)
        company.hst_number = getattr(merchant, "hst_number", None)
        company.business_number = getattr(merchant, "business_number", None)
        company.website = website_of(merchant)
        company.industry = industry_of(merchant)
        area = profile_service_area(merchant)
        if area:
            company.service_area = area
        logo = branding_logo_url(merchant)
        if logo:
            company.logo_url = logo
        billing = getattr(merchant, "billing_address", None)
        if billing:
            company.address = dict(billing)
        db.flush()
        return company

    def delete_company(self, db: Session, company_id: str) -> None:
        company = db.get(CrmCompany, company_id)
        if not company:
            raise LookupError("company_not_found")
        company_id = company.id
        db.delete(company)
        self._admin_audit(
            db, None, action="crm.company.delete", resource_type="crm_company", resource_id=company_id
        )
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

