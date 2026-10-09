"""Admin: lead attribution (source / industry / FSA / UTM) for marketing."""

from typing import Annotated

from fastapi import Query
from sqlalchemy.orm import Session

from porterchain_api.marketing_site.lead_stats import lead_attribution_summary
from porterchain_api.routers.admin._deps import (
    AdminContext,
    Depends,
    get_admin_context,
    get_db,
    require_module,
    router,
)


@router.get("/marketing/lead-attribution")
def marketing_lead_attribution(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Read-only counts of CRM leads by source, industry, FSA and UTM."""
    require_module(ctx, "crm_read")
    return lead_attribution_summary(db, days=days)
