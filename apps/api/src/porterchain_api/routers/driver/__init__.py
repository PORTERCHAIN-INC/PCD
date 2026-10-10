"""Driver API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.driver import (
    assignment,  # noqa: F401
    auth_dev,  # noqa: F401
    communications,  # noqa: F401
    dashboard,  # noqa: F401
    dispatch_route,  # noqa: F401
    jobs,  # noqa: F401
    navigation_pod,  # noqa: F401
    profile,  # noqa: F401
    shift,  # noqa: F401
    support,  # noqa: F401
    verification,  # noqa: F401
)
from porterchain_api.routers.driver._deps import router

__all__ = ["router"]
