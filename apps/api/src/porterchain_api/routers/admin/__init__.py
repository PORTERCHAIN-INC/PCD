"""Admin API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.admin import (
    audit,  # noqa: F401
    blog,  # noqa: F401
    blog_authors,  # noqa: F401
    booking_drafts,  # noqa: F401
    claims,  # noqa: F401
    dashboard,  # noqa: F401
    data_moat,  # noqa: F401
    dispatch,  # noqa: F401
    dispatch_plan,  # noqa: F401
    driver_ops,  # noqa: F401
    finance,  # noqa: F401
    finance_invoice_pdf,  # noqa: F401
    impersonation,  # noqa: F401
    investor_metrics,  # noqa: F401
    leads,  # noqa: F401
    leads_360,  # noqa: F401
    leads_outbound,  # noqa: F401 — before {lead_id}
    marketing_leads,  # noqa: F401
    monopoly_metrics,  # noqa: F401
    orders,  # noqa: F401
    platform_metrics,  # noqa: F401
    route_templates,  # noqa: F401
    settings,  # noqa: F401
    settings_directory,  # noqa: F401
    support,  # noqa: F401
    visitor_intelligence,  # noqa: F401
)
from porterchain_api.routers.admin._deps import router

__all__ = ["router"]
