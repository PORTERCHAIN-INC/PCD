"""Minimal Keycloak Admin REST client for staff provisioning (service account ``pc-api-admin``).

Staff never get a Porterchain-issued password or session: an invite creates the Keycloak
user with required actions (verify email, set password, configure TOTP for admin tiers)
and Keycloak emails the action link. Lost device → drop OTP credentials, force
CONFIGURE_TOTP and log every session out.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from porterchain_api.config import Settings

MFA_ROLE = "mfa_required"
MFA_TIERS = {"super_admin", "admin"}
ACTION_LIFESPAN_SECONDS = 72 * 3600


def _admin_base(settings) -> str:
    """L213: ADMIN_APP_URL when set explicitly, else ADMIN_PORTAL_URL (what every stack sets).

    The old default (localhost:3002) is not a pc-admin redirect URI on the local stack or prod, so
    Keycloak refused execute-actions-email and staff invites never arrived."""
    fields = getattr(settings, "model_fields_set", set()) or set()
    url = settings.admin_app_url if "admin_app_url" in fields else settings.admin_portal_url
    return str(url).rstrip("/")

_token_cache: dict[str, tuple[str, float]] = {}


class KeycloakAdminUnavailable(ValueError):
    """Raised when the service account is not configured or Keycloak is down."""


def _base(settings: Settings) -> str:
    base = (settings.keycloak_internal_url or settings.keycloak_url or "").strip().rstrip("/")
    if not base:
        raise KeycloakAdminUnavailable("keycloak_admin_unconfigured")
    return base


def configured(settings: Settings) -> bool:
    return bool(
        (settings.keycloak_internal_url or settings.keycloak_url)
        and settings.keycloak_admin_client_id
        and settings.keycloak_admin_client_secret
    )


class KeycloakAdmin:
    def __init__(self, settings: Settings, *, client: httpx.Client | None = None) -> None:
        if not configured(settings):
            raise KeycloakAdminUnavailable("keycloak_admin_unconfigured")
        self.settings = settings
        self.realm = settings.keycloak_realm
        self.base = _base(settings)
        self.http = client or httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0))

    # -- plumbing -------------------------------------------------------------
    def _token(self) -> str:
        key = f"{self.base}|{self.realm}|{self.settings.keycloak_admin_client_id}"
        cached = _token_cache.get(key)
        if cached and cached[1] > time.time() + 15:
            return cached[0]
        try:
            res = self.http.post(
                f"{self.base}/realms/{self.realm}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.keycloak_admin_client_id,
                    "client_secret": self.settings.keycloak_admin_client_secret,
                },
            )
        except httpx.HTTPError as exc:
            raise KeycloakAdminUnavailable("keycloak_admin_unavailable") from exc
        if res.status_code != 200:
            raise KeycloakAdminUnavailable("keycloak_admin_auth_failed")
        body = res.json()
        _token_cache[key] = (body["access_token"], time.time() + float(body.get("expires_in", 60)))
        return body["access_token"]

    def _call(self, method: str, path: str, **kw: Any) -> httpx.Response:
        url = f"{self.base}/admin/realms/{self.realm}{path}"
        try:
            res = self.http.request(method, url, headers={"Authorization": f"Bearer {self._token()}"}, **kw)
        except httpx.HTTPError as exc:
            raise KeycloakAdminUnavailable("keycloak_admin_unavailable") from exc
        if res.status_code >= 500:
            raise KeycloakAdminUnavailable("keycloak_admin_unavailable")
        return res

    # -- users ----------------------------------------------------------------
    def find_user(self, email: str) -> dict[str, Any] | None:
        res = self._call("GET", "/users", params={"email": email, "exact": "true"})
        res.raise_for_status()
        rows = [u for u in res.json() if str(u.get("email", "")).lower() == email.lower()]
        return rows[0] if rows else None

    def _realm_role(self, name: str) -> dict[str, Any] | None:
        res = self._call("GET", f"/roles/{name}")
        return res.json() if res.status_code == 200 else None

    def _sync_roles(self, user_id: str, role: str) -> None:
        from porterchain_api.auth.invitation_service import INVITABLE_ADMIN_ROLES

        want = {role} | ({MFA_ROLE} if role in MFA_TIERS else set())
        managed = set(INVITABLE_ADMIN_ROLES) | MFA_TIERS | {MFA_ROLE}
        res = self._call("GET", f"/users/{user_id}/role-mappings/realm")
        res.raise_for_status()
        have = {r["name"]: r for r in res.json()}
        drop = [have[n] for n in have if n in managed and n not in want]
        add = [r for r in (self._realm_role(n) for n in want - set(have)) if r]
        if drop:
            self._call("DELETE", f"/users/{user_id}/role-mappings/realm", json=drop).raise_for_status()
        if add:
            self._call("POST", f"/users/{user_id}/role-mappings/realm", json=add).raise_for_status()

    def ensure_staff_user(self, *, email: str, name: str | None, role: str) -> tuple[str, bool]:
        """Create or update the Keycloak user; returns (keycloak_user_id, created)."""
        first, _, last = (name or "").strip().partition(" ")
        existing = self.find_user(email)
        created = False
        if existing is None:
            actions = ["VERIFY_EMAIL", "UPDATE_PASSWORD"]
            if role in MFA_TIERS:
                actions.append("CONFIGURE_TOTP")
            res = self._call(
                "POST",
                "/users",
                json={
                    "username": email,
                    "email": email,
                    "firstName": first or None,
                    "lastName": last or None,
                    "enabled": True,
                    "emailVerified": False,
                    "requiredActions": actions,
                },
            )
            if res.status_code not in (201, 409):
                res.raise_for_status()
            existing = self.find_user(email)
            created = True
        if existing is None:
            raise KeycloakAdminUnavailable("keycloak_user_create_failed")
        if not existing.get("enabled", True):
            self._call("PUT", f"/users/{existing['id']}", json={"enabled": True}).raise_for_status()
        self._sync_roles(existing["id"], role)
        return existing["id"], created

    def send_actions_email(
        self,
        user_id: str,
        actions: list[str],
        *,
        client_id: str = "pc-admin",
        redirect_uri: str | None = None,
    ) -> bool:
        """Keycloak emails the action link (needs realm SMTP). False when mail failed."""
        try:
            res = self._call(
                "PUT",
                f"/users/{user_id}/execute-actions-email",
                params={
                    "lifespan": ACTION_LIFESPAN_SECONDS,
                    "client_id": client_id,
                    "redirect_uri": redirect_uri
                    or f"{_admin_base(self.settings)}/auth/login",
                },
                json=actions,
            )
        except KeycloakAdminUnavailable:
            return False
        return res.status_code in (200, 204)

    def pending_actions(self, user_id: str) -> list[str]:
        res = self._call("GET", f"/users/{user_id}")
        res.raise_for_status()
        return list(res.json().get("requiredActions") or [])

    def reset_mfa(self, user_id: str) -> int:
        """Remove OTP / WebAuthn credentials, require CONFIGURE_TOTP, log out every session."""
        res = self._call("GET", f"/users/{user_id}/credentials")
        res.raise_for_status()
        removed = 0
        for cred in res.json():
            if cred.get("type") in {"otp", "webauthn", "webauthn-passwordless"}:
                self._call("DELETE", f"/users/{user_id}/credentials/{cred['id']}").raise_for_status()
                removed += 1
        user = self._call("GET", f"/users/{user_id}").json()
        actions = sorted(set(user.get("requiredActions") or []) | {"CONFIGURE_TOTP"})
        self._call("PUT", f"/users/{user_id}", json={"requiredActions": actions}).raise_for_status()
        self.logout(user_id)
        return removed

    def logout(self, user_id: str) -> None:
        self._call("POST", f"/users/{user_id}/logout").raise_for_status()

    def disable(self, email: str) -> bool:
        user = self.find_user(email)
        if not user:
            return False
        self._call("PUT", f"/users/{user['id']}", json={"enabled": False}).raise_for_status()
        self.logout(user["id"])
        return True


def end_staff_sessions(settings: Settings, email: str, *, disable: bool = False) -> bool:
    """Best-effort: log a staff user out of Keycloak (and optionally disable). Never raises."""
    import logging

    if not configured(settings) or not email:
        return False
    try:
        kc = KeycloakAdmin(settings)
        if disable:
            return kc.disable(email)
        user = kc.find_user(email)
        if user:
            kc.logout(user["id"])
            return True
    except Exception:  # noqa: BLE001
        logging.getLogger("porterchain.auth.keycloak_admin").warning("keycloak_logout_failed")
    return False


def sync_staff_role(settings: Settings, *, email: str, name: str | None, role: str) -> bool:
    """Best-effort: mirror an AdminUser role change into Keycloak and force re-login."""
    import logging

    if not configured(settings) or not email:
        return False
    try:
        kc = KeycloakAdmin(settings)
        kc_id, _ = kc.ensure_staff_user(email=email, name=name, role=role)
        kc.logout(kc_id)
        return True
    except Exception:  # noqa: BLE001
        logging.getLogger("porterchain.auth.keycloak_admin").warning("keycloak_role_sync_failed")
        return False
