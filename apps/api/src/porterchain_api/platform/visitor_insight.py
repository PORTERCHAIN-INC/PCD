"""Visitor insight for CRM leads — collaboration may read without importing booking_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.crm_models import CrmLead


def insight_for_lead(db: Session, lead: CrmLead) -> dict[str, Any] | None:
    """Compose visitor + guide signals for a CrmLead (delegates to booking intelligence)."""
    from porterchain_api.booking_engine.visitor_intelligence import VisitorIntelligenceService

    return VisitorIntelligenceService().insight_for_lead(db, lead)


__all__ = ["insight_for_lead"]
