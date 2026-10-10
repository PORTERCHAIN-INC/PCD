"""Admin API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.admin._deps import router

from porterchain_api.routers.admin import dashboard  # noqa: F401
from porterchain_api.routers.admin import orders  # noqa: F401
from porterchain_api.routers.admin import driver_ops  # noqa: F401
from porterchain_api.routers.admin import booking_drafts  # noqa: F401
from porterchain_api.routers.admin import claims  # noqa: F401
from porterchain_api.routers.admin import finance  # noqa: F401
from porterchain_api.routers.admin import finance_invoice_pdf  # noqa: F401
from porterchain_api.routers.admin import finance_interac  # noqa: F401
from porterchain_api.routers.admin import finance_cash  # noqa: F401
from porterchain_api.routers.admin import finance_insights  # noqa: F401
from porterchain_api.routers.admin import support  # noqa: F401
from porterchain_api.routers.admin import settings  # noqa: F401
from porterchain_api.routers.admin import settings_directory  # noqa: F401
from porterchain_api.routers.admin import impersonation  # noqa: F401
from porterchain_api.routers.admin import data_moat  # noqa: F401
from porterchain_api.routers.admin import platform_metrics  # noqa: F401
from porterchain_api.routers.admin import monopoly_metrics  # noqa: F401
from porterchain_api.routers.admin import investor_metrics  # noqa: F401
from porterchain_api.routers.admin import audit  # noqa: F401
from porterchain_api.routers.admin import marketing_leads  # noqa: F401
from porterchain_api.routers.admin import leads  # noqa: F401
from porterchain_api.routers.admin import leads_inbox  # noqa: F401 — before {lead_id}
from porterchain_api.routers.admin import leads_desk  # noqa: F401 — before {lead_id}
from porterchain_api.routers.admin import leads_outbound  # noqa: F401 — before {lead_id}
from porterchain_api.routers.admin import leads_360  # noqa: F401
from porterchain_api.routers.admin import blog  # noqa: F401
from porterchain_api.routers.admin import blog_authors  # noqa: F401
from porterchain_api.routers.admin import visitor_intelligence  # noqa: F401
from porterchain_api.routers.admin import route_templates  # noqa: F401

__all__ = ["router"]
