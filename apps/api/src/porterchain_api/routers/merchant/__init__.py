"""Merchant API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.merchant import (
    billing,  # noqa: F401
    customer_experience,  # noqa: F401
    dashboard_booking,  # noqa: F401
    integrations,  # noqa: F401
    order_returns,  # noqa: F401
    orders_tracking,  # noqa: F401
    privacy,  # noqa: F401
    profile_team,  # noqa: F401
    referrals,  # noqa: F401
    reports,  # noqa: F401
    route_imports,  # noqa: F401
    settings,  # noqa: F401
    shopify,  # noqa: F401
    standing_orders,  # noqa: F401
    support_claims,  # noqa: F401
)
from porterchain_api.routers.merchant._deps import (
    _order_response,
    _profile_response,
    router,
)

__all__ = ["_order_response", "_profile_response", "router"]
