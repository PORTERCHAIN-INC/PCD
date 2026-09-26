"""CRM leads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import String, and_, case, cast, func, or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.crm_lead_write import CrmLeadWriteMixin
from porterchain_api.crm_models import CrmLead
from porterchain_api.db_json import json_text
from porterchain_api.domain.crm_states import LeadPriority, LeadStatus


class CrmLeadsMixin(CrmLeadWriteMixin):
    def _leads_base_query(
        self,
        db: Session,
        *,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        source: str | None = None,
        channel: str | None = None,
        intent_type: str | None = None,
        decision_status: str | None = None,
        industry: str | None = None,
        city: str | None = None,
        province: str | None = None,
        min_score: int | None = None,
        unassigned: bool | None = None,
        converted: bool | None = None,
        merge_candidates: bool | None = None,
        sla_breached: bool | None = None,
        has_open_draft: bool | None = None,
        nurture_scheduled: bool | None = None,
        has_abandoned: bool | None = None,
        search: str | None = None,
        include_archived: bool = False,
        tag: str | None = None,
        has_phone: bool | None = None,
    ):
        q = db.query(CrmLead)
        if not include_archived and status != LeadStatus.ARCHIVED.value:
            q = q.filter(CrmLead.status != LeadStatus.ARCHIVED.value)
        if status:
            q = q.filter(CrmLead.status == status)
        if priority:
            q = q.filter(CrmLead.priority == priority)
        if assigned_to:
            q = q.filter(CrmLead.assigned_to == assigned_to)
        if source:
            q = q.filter(CrmLead.source == source)
        if channel:
            q = q.filter(CrmLead.channel == channel)
        if intent_type:
            q = q.filter(CrmLead.intent_type == intent_type)
        if decision_status:
            q = q.filter(CrmLead.decision_status == decision_status)
        if industry:
            q = q.filter(CrmLead.industry == industry)
        if city:
            q = q.filter(json_text(CrmLead.address, "city") == city)
        if province:
            q = q.filter(json_text(CrmLead.address, "province") == province)
        if min_score is not None:
            q = q.filter(CrmLead.lead_score >= min_score)
        if tag:
            q = q.filter(cast(CrmLead.tags, String).ilike(f"%{tag}%"))
        if has_phone is True:
            q = q.filter(CrmLead.phone.isnot(None), CrmLead.phone != "")
        elif has_phone is False:
            q = q.filter(or_(CrmLead.phone.is_(None), CrmLead.phone == ""))
        if unassigned:
            q = q.filter(CrmLead.assigned_to.is_(None))
        if merge_candidates:
            q = q.filter(CrmLead.merge_candidate_of.isnot(None))
        if sla_breached:
            now = datetime.now(UTC)
            q = q.filter(
                CrmLead.sla_first_response_due_at.isnot(None),
                CrmLead.sla_first_response_due_at < now,
                CrmLead.status == LeadStatus.NEW.value,
            )
        if has_open_draft:
            from porterchain_api.booking_draft_models import BookingDraft
            from porterchain_api.domain.states import BOOKING_DRAFT_TERMINAL, BookingDraftState

            terminal = {s.value for s in BOOKING_DRAFT_TERMINAL}
            open_session_ids = (
                db.query(BookingDraft.session_id)
                .filter(~BookingDraft.state.in_(terminal))
                .filter(BookingDraft.state != BookingDraftState.EXPIRED.value)
            )
            open_draft_ids = (
                db.query(BookingDraft.id)
                .filter(~BookingDraft.state.in_(terminal))
                .filter(BookingDraft.state != BookingDraftState.EXPIRED.value)
            )
            q = q.filter(
                or_(
                    CrmLead.booking_draft_id.in_(open_draft_ids),
                    and_(
                        CrmLead.visitor_session_id.isnot(None),
                        CrmLead.visitor_session_id.in_(open_session_ids),
                    ),
                )
            )
        if nurture_scheduled:
            q = q.filter(
                or_(
                    CrmLead.status == LeadStatus.NURTURING.value,
                    cast(CrmLead.tags, String).ilike("%nurture%"),
                )
            )
        if has_abandoned:
            from porterchain_api.booking_models import AbandonedCheckout

            abandoned_quotes = db.query(AbandonedCheckout.quote_id)
            q = q.filter(
                or_(
                    CrmLead.quote_id.in_(abandoned_quotes),
                    json_text(CrmLead.custom_fields, "quote_id").in_(abandoned_quotes),
                )
            )
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
        return q

    def list_leads(
        self,
        db: Session,
        *,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        source: str | None = None,
        channel: str | None = None,
        intent_type: str | None = None,
        decision_status: str | None = None,
        industry: str | None = None,
        city: str | None = None,
        province: str | None = None,
        min_score: int | None = None,
        unassigned: bool | None = None,
        converted: bool | None = None,
        merge_candidates: bool | None = None,
        sla_breached: bool | None = None,
        has_open_draft: bool | None = None,
        nurture_scheduled: bool | None = None,
        has_abandoned: bool | None = None,
        search: str | None = None,
        limit: int = 500,
        offset: int = 0,
        include_archived: bool = False,
        sort: str = "smart",
        tag: str | None = None,
        has_phone: bool | None = None,
    ) -> list[CrmLead]:
        q = self._leads_base_query(
            db,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            source=source,
            channel=channel,
            intent_type=intent_type,
            decision_status=decision_status,
            industry=industry,
            city=city,
            province=province,
            min_score=min_score,
            unassigned=unassigned,
            converted=converted,
            merge_candidates=merge_candidates,
            sla_breached=sla_breached,
            has_open_draft=has_open_draft,
            nurture_scheduled=nurture_scheduled,
            has_abandoned=has_abandoned,
            search=search,
            include_archived=include_archived,
            tag=tag,
            has_phone=has_phone,
        )
        if (sort or "smart").lower() == "smart":
            now = datetime.now(UTC)
            priority_rank = case(
                (CrmLead.priority == LeadPriority.URGENT.value, 0),
                (CrmLead.priority == LeadPriority.HIGH.value, 1),
                (CrmLead.priority == LeadPriority.MEDIUM.value, 2),
                else_=3,
            )
            sla_rank = case(
                (
                    and_(
                        CrmLead.sla_first_response_due_at.isnot(None),
                        CrmLead.sla_first_response_due_at < now,
                        CrmLead.status == LeadStatus.NEW.value,
                    ),
                    0,
                ),
                else_=1,
            )
            return (
                q.order_by(
                    sla_rank.asc(),
                    priority_rank.asc(),
                    CrmLead.lead_score.desc(),
                    CrmLead.created_at.desc(),
                )
                .offset(max(0, offset))
                .limit(limit)
                .all()
            )
        return q.order_by(CrmLead.created_at.desc()).offset(max(0, offset)).limit(limit).all()

    def count_leads(
        self,
        db: Session,
        *,
        status: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        source: str | None = None,
        channel: str | None = None,
        intent_type: str | None = None,
        decision_status: str | None = None,
        industry: str | None = None,
        city: str | None = None,
        province: str | None = None,
        min_score: int | None = None,
        unassigned: bool | None = None,
        converted: bool | None = None,
        merge_candidates: bool | None = None,
        sla_breached: bool | None = None,
        has_open_draft: bool | None = None,
        nurture_scheduled: bool | None = None,
        has_abandoned: bool | None = None,
        search: str | None = None,
        include_archived: bool = False,
        tag: str | None = None,
        has_phone: bool | None = None,
    ) -> int:
        return self._leads_base_query(
            db,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            source=source,
            channel=channel,
            intent_type=intent_type,
            decision_status=decision_status,
            industry=industry,
            city=city,
            province=province,
            min_score=min_score,
            unassigned=unassigned,
            converted=converted,
            merge_candidates=merge_candidates,
            sla_breached=sla_breached,
            has_open_draft=has_open_draft,
            nurture_scheduled=nurture_scheduled,
            has_abandoned=has_abandoned,
            search=search,
            include_archived=include_archived,
            tag=tag,
            has_phone=has_phone,
        ).count()

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

    def find_lead_by_email(self, db: Session, email: str) -> CrmLead | None:
        """Most recent lead matching email (case-insensitive)."""
        normalized = (email or "").strip().lower()
        if not normalized:
            return None
        return (
            db.query(CrmLead)
            .filter(func.lower(CrmLead.email) == normalized)
            .order_by(CrmLead.created_at.desc())
            .first()
        )
