"""CRM reports."""

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



class CrmReportsMixin:
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

