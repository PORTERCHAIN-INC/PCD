"""CRM deals and pipeline board."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_helpers import (
    CrmActor,
    _actor,
    _now,
)
from porterchain_api.crm_models import (
    CrmCompany,
    CrmDeal,
    CrmLead,
)
from porterchain_api.db_json import json_text_lower
from porterchain_api.domain.crm_states import (
    PIPELINE_STAGES,
    STAGE_PROBABILITY,
    DealStage,
    LeadStatus,
)


class CrmDealsMixin:
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
    # Five-stage lead pipeline → board column. (The old dict listed enum aliases
    # that now share a value, so "replied" silently landed in one column and
    # "quoted" fell back to Prospecting.)
    LEAD_STATUS_TO_STAGE = {
        LeadStatus.NEW.value: DealStage.PROSPECTING.value,
        LeadStatus.REPLIED.value: DealStage.QUALIFIED.value,
        LeadStatus.QUOTED.value: DealStage.QUOTE_SENT.value,
        LeadStatus.LOST.value: DealStage.LOST.value,
    }
    # Reverse: dropping a lead into one of these columns just updates its status.
    STAGE_TO_LEAD_STATUS = {
        DealStage.PROSPECTING.value: LeadStatus.NEW.value,
        DealStage.QUALIFIED.value: LeadStatus.REPLIED.value,
        DealStage.QUOTE_SENT.value: LeadStatus.QUOTED.value,
        DealStage.LOST.value: LeadStatus.LOST.value,
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
        deal_channel: dict[str, str | None] = {}
        if include_deals:
            for row in (
                db.query(CrmLead.deal_id, CrmLead.channel)
                .filter(CrmLead.deal_id.isnot(None))
                .all()
            ):
                if row[0]:
                    deal_channel[row[0]] = row[1]

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
                    "channel": deal_channel.get(d.id),
                }
            )
            col["count"] += 1
            col["deal_count"] += 1
            col["value_cents"] += d.expected_revenue_cents

        # Leads grouped by mapped stage, capped per column (sorted by score).
        leads = []
        if include_leads:
            leads_q = db.query(CrmLead).filter(
                CrmLead.status != LeadStatus.CONVERTED.value,
                CrmLead.status != LeadStatus.ARCHIVED.value,
                # Driver applicants are not sales opportunities.
                func.coalesce(CrmLead.intent_type, "") != "driver_partner",
            )
            if min_value_cents:
                leads_q = leads_q.filter(
                    func.coalesce(CrmLead.estimated_revenue_cents, 0) >= min_value_cents
                )
            if term:
                like = f"%{term}%"
                leads_q = leads_q.filter(
                    or_(
                        func.lower(CrmLead.company_name).like(like),
                        json_text_lower(CrmLead.address, "city").like(like),
                        json_text_lower(CrmLead.address, "province").like(like),
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
                        "channel": lead.channel,
                        "has_draft": bool(lead.booking_draft_id),
                        "sla_breached": bool(
                            lead.sla_first_response_due_at
                            and lead.sla_first_response_due_at < _now()
                            and lead.status == LeadStatus.NEW.value
                        ),
                        "nurture": any("nurture" in str(t).lower() for t in (lead.tags or [])),
                    }
                )
            else:
                col["hidden"] += 1

        return [columns[stage] for stage in all_stages]

    def create_deal(self, db: Session, ctx: CrmActor | None, data: dict) -> CrmDeal:
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
