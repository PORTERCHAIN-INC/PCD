"""Soft-archive inactive unconverted CrmLeads (retention policy)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.collaboration_engine.lead_privacy import PRIVACY_ERASED_TAG
from porterchain_api.crm_models import CrmLead
from porterchain_api.domain.crm_states import LeadStatus

logger = logging.getLogger(__name__)

DEFAULT_INACTIVE_DAYS = 730  # ~24 months


def soft_archive_stale_leads(
    db: Session,
    *,
    inactive_days: int = DEFAULT_INACTIVE_DAYS,
    limit: int = 100,
) -> dict[str, int]:
    """Set status=archived for unconverted leads with no touch in inactive_days."""
    cutoff = datetime.now(UTC) - timedelta(days=max(30, inactive_days))
    rows = (
        db.query(CrmLead)
        .filter(
            CrmLead.status.notin_(
                [
                    LeadStatus.CONVERTED.value,
                    LeadStatus.ARCHIVED.value,
                ]
            ),
            or_(
                CrmLead.last_touch_at < cutoff,
                (CrmLead.last_touch_at.is_(None) & (CrmLead.updated_at < cutoff)),
                (
                    CrmLead.last_touch_at.is_(None)
                    & CrmLead.updated_at.is_(None)
                    & (CrmLead.created_at < cutoff)
                ),
            ),
        )
        .order_by(CrmLead.updated_at.asc().nullsfirst())
        .limit(limit)
        .all()
    )
    archived = 0
    skipped = 0
    for lead in rows:
        tags = list(lead.tags or [])
        if PRIVACY_ERASED_TAG in tags:
            skipped += 1
            continue
        lead.status = LeadStatus.ARCHIVED.value
        if "soft_archived" not in tags:
            tags.append("soft_archived")
            lead.tags = tags
        archived += 1
    if archived:
        db.commit()
        logger.info("lead_soft_archive count=%s cutoff=%s", archived, cutoff.isoformat())
    return {"archived": archived, "skipped": skipped, "scanned": len(rows)}


__all__ = ["DEFAULT_INACTIVE_DAYS", "soft_archive_stale_leads"]
