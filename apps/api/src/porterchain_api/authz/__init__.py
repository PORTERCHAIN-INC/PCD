"""SpiceDB (Zanzibar) authorization — access rules live here, not in PostgreSQL.

Do not import FastAPI deps here — that creates a circular import with
auth.dependencies → principal_resolution → authz.client → this package.
Import require_relation from porterchain_api.authz.dependencies directly.
"""

from porterchain_api.authz.client import (
    AuthzClient,
    get_authz_client,
    reset_authz_client,
)
from porterchain_api.authz.tuples import TupleWriter

__all__ = [
    "AuthzClient",
    "TupleWriter",
    "get_authz_client",
    "reset_authz_client",
]
