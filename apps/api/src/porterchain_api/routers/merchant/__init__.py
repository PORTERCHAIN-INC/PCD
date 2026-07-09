"""Merchant API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.merchant._deps import _order_response, _profile_response, router

from porterchain_api.routers.merchant import dashboard_booking  # noqa: F401
from porterchain_api.routers.merchant import orders_tracking  # noqa: F401
from porterchain_api.routers.merchant import billing  # noqa: F401
from porterchain_api.routers.merchant import reports  # noqa: F401
from porterchain_api.routers.merchant import profile_team  # noqa: F401
from porterchain_api.routers.merchant import settings  # noqa: F401
from porterchain_api.routers.merchant import support_claims  # noqa: F401
from porterchain_api.routers.merchant import integrations  # noqa: F401
from porterchain_api.routers.merchant import standing_orders  # noqa: F401
from porterchain_api.routers.merchant import privacy  # noqa: F401

__all__ = ["router", "_order_response", "_profile_response"]
