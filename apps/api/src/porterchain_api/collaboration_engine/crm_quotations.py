"""CRM quotations."""

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



class CrmQuotationsMixin:
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


    def create_quotation(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmQuotation:
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

    def revise_quotation(self, db: Session, ctx: CrmActor | None, quotation_id: str, data: dict) -> CrmQuotation:
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
        self, db: Session, ctx: CrmActor | None, quotation_id: str, status: str
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
        self, db: Session, ctx: CrmActor | None, quotation_id: str
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

