"""Driver API package — thin sub-routers on shared `router`."""

from porterchain_api.routers.driver._deps import router

from porterchain_api.routers.driver import profile  # noqa: F401
from porterchain_api.routers.driver import dashboard  # noqa: F401
from porterchain_api.routers.driver import shift  # noqa: F401
from porterchain_api.routers.driver import support  # noqa: F401
from porterchain_api.routers.driver import communications  # noqa: F401
from porterchain_api.routers.driver import jobs  # noqa: F401
from porterchain_api.routers.driver import navigation_pod  # noqa: F401
from porterchain_api.routers.driver import auth_dev  # noqa: F401
from porterchain_api.routers.driver import verification  # noqa: F401

__all__ = ["router"]
