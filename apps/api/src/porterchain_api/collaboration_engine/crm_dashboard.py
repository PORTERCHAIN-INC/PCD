"""CRM dashboard aggregates."""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import (
    _today,
)
from porterchain_api.crm_models import (
    CrmCompany,
    CrmContract,
    CrmDeal,
    CrmLead,
    CrmQuotation,
    CrmSalesTask,
)
from porterchain_api.domain.crm_states import (
    PIPELINE_STAGES,
    CompanyMerchantStatus,
    ContractStatus,
    DealStage,
    LeadStatus,
    QuotationStatus,
    TaskStatus,
)


class CrmDashboardMixin:
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

