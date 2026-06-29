"""Fleetbase SSO trust — Porterchain JWT exchange."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)


class FleetbaseSsoClient:
    """Fleetbase trusts Porterchain-signed SSO JWTs — no duplicate user passwords."""

    def __init__(
        self,
        settings: FleetbaseSettings,
        *,
        sso_jwt_secret: str = "",
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.sso_jwt_secret = sso_jwt_secret
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def exchange_sso_token(
        self,
        sso_token: str,
        *,
        email: str | None,
        clerk_user_id: str,
        fleetbase_permissions: list[str],
        fleetbase_roles: list[str],
    ) -> dict[str, Any] | None:
        """Exchange Porterchain SSO JWT for Fleetbase session (bridge endpoint)."""
        if not self.settings.is_enabled:
            return None

        body = {
            "sso_token": sso_token,
            "email": email,
            "clerk_user_id": clerk_user_id,
            "company_uuid": self.settings.company_uuid,
            "fleetbase_permissions": fleetbase_permissions,
            "fleetbase_roles": fleetbase_roles,
        }
        try:
            return self.client.post("/int/v1/porterchain/sso/exchange", json=body, retry=False)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase SSO bridge not available", level=logging.INFO)
            return None

    def sync_permissions(
        self,
        fleetbase_user_uuid: str,
        permissions: list[str],
        roles: list[str],
    ) -> bool:
        """Push permission sync to Fleetbase (bridge endpoint)."""
        if not self.settings.is_enabled:
            return False
        try:
            self.client.post(
                f"/int/v1/porterchain/sso/users/{fleetbase_user_uuid}/permissions",
                json={"permissions": permissions, "roles": roles},
                retry=False,
            )
            return True
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase permission sync failed")
            return False
