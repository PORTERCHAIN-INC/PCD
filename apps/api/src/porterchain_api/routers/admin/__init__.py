"""Admin API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.admin._deps import router

from porterchain_api.routers.admin import dashboard  # noqa: F401
from porterchain_api.routers.admin import orders  # noqa: F401
from porterchain_api.routers.admin import booking_drafts  # noqa: F401
from porterchain_api.routers.admin import claims  # noqa: F401
from porterchain_api.routers.admin import pricing  # noqa: F401
from porterchain_api.routers.admin import finance  # noqa: F401
from porterchain_api.routers.admin import support  # noqa: F401
from porterchain_api.routers.admin import settings  # noqa: F401

__all__ = ["router"]
