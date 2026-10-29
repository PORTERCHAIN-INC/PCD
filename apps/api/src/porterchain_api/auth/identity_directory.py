"""User directory on Keycloak (L36) — replaces the Clerk Backend API adapter.

One realm (``porterchain``) holds every persona, so every user class resolves to the same
directory. Users are returned as a neutral dict::

    {"id", "email", "email_verified", "first_name", "last_name", "phone", "enabled",
     "created_at", "last_sign_in_at", "metadata"}

``metadata`` is stored as Keycloak user attributes (single-valued strings). Credentials
never pass through PorterChain: invites create the user with required actions and Keycloak
emails the link.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from porterchain_api.auth import keycloak_admin
from porterchain_api.auth.keycloak_admin import KeycloakAdmin, KeycloakAdminUnavailable
from porterchain_api.config import Settings

logger = logging.getLogger(__name__)

UserKind = Literal["customer", "merchant", "admin", "driver"]
ALL_USER_KINDS: tuple[UserKind, ...] = ("customer", "merchant", "admin", "driver")
_META_PREFIX = "pc_"

PORTAL_CLIENTS: dict[str, str] = {
    "customer": "pc-customer-portal",
    "merchant": "pc-merchant-portal",
    "driver": "pc-driver-portal",
    "admin": "pc-admin",
}


@dataclass(frozen=True)
class InviteResult:
    action: str  # found | invited | invite_pending
    subject: str | None = None
    invitation_id: str | None = None


@dataclass(frozen=True)
class DirectoryUserSnapshot:
    subject: str
    email: str
    first_name: str | None
    last_name: str | None
    banned: bool
    locked: bool
    email_verified: bool
    password_set: bool
    last_sign_in_at: datetime | None
    created_at: datetime | None
    metadata: dict[str, Any]

    @property
    def status(self) -> str:
        if self.banned:
            return "banned"
        if self.locked:
            return "locked"
        if not self.last_sign_in_at and not self.password_set:
            return "never_signed_in"
        return "active"


def _ts(ms: Any) -> datetime | None:
    if isinstance(ms, (int, float)) and ms:
        return datetime.fromtimestamp(ms / 1000 if ms > 1e12 else ms, tz=UTC)
    return None


def _encode_meta(meta: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for k, v in meta.items():
        if v is None:
            continue
        out[f"{_META_PREFIX}{k}"] = [v if isinstance(v, str) else json.dumps(v)]
    return out


def _decode_meta(attrs: dict[str, Any] | None) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for k, vals in (attrs or {}).items():
        if not k.startswith(_META_PREFIX) or not vals:
            continue
        raw = vals[0] if isinstance(vals, list) else vals
        try:
            meta[k[len(_META_PREFIX):]] = json.loads(raw)
        except (TypeError, ValueError):
            meta[k[len(_META_PREFIX):]] = raw
    return meta


def normalize_user(rep: dict[str, Any]) -> dict[str, Any]:
    attrs = rep.get("attributes") or {}
    phone = (attrs.get("phone_number") or attrs.get("phoneNumber") or [None])[0]
    return {
        "id": str(rep.get("id") or ""),
        "email": str(rep.get("email") or "").lower() or None,
        "email_verified": bool(rep.get("emailVerified")),
        "first_name": rep.get("firstName"),
        "last_name": rep.get("lastName"),
        "phone": phone,
        "enabled": bool(rep.get("enabled", True)),
        "created_at": rep.get("createdTimestamp"),
        "last_sign_in_at": None,
        "required_actions": list(rep.get("requiredActions") or []),
        "metadata": _decode_meta(attrs),
    }


class IdentityDirectory:
    """Keycloak-backed directory with the operations the admin/persona flows need."""

    def __init__(self, settings: Settings, *, admin: KeycloakAdmin | None = None) -> None:
        self.settings = settings
        self.kc = admin or KeycloakAdmin(settings)

    # -- reads ------------------------------------------------------------------
    def _rep(self, subject: str) -> dict[str, Any] | None:
        res = self.kc._call("GET", f"/users/{subject}")
        if res.status_code == 404:
            return None
        res.raise_for_status()
        return res.json()

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        rep = self.kc.find_user(email.lower().strip())
        return normalize_user(rep) if rep else None

    def get_user(self, subject: str) -> dict[str, Any] | None:
        rep = self._rep(subject)
        return normalize_user(rep) if rep else None

    def list_users(
        self, *, limit: int = 100, offset: int = 0, query: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        params: dict[str, Any] = {"first": offset, "max": min(limit, 500), "briefRepresentation": "false"}
        count_params: dict[str, Any] = {}
        if query and query.strip():
            params["search"] = count_params["search"] = query.strip()
        res = self.kc._call("GET", "/users", params=params)
        res.raise_for_status()
        rows = [normalize_user(u) for u in res.json() if not str(u.get("username", "")).startswith("service-account-")]
        cnt = self.kc._call("GET", "/users/count", params=count_params)
        total = int(cnt.json()) if cnt.status_code == 200 else len(rows)
        return rows, total

    # -- writes -----------------------------------------------------------------
    def create_user(
        self,
        email: str,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        metadata: dict[str, Any] | None = None,
        required_actions: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized = email.lower().strip()
        res = self.kc._call(
            "POST",
            "/users",
            json={
                "username": normalized,
                "email": normalized,
                "firstName": first_name,
                "lastName": last_name,
                "enabled": True,
                "emailVerified": False,
                "attributes": _encode_meta(metadata or {}),
                "requiredActions": required_actions or ["VERIFY_EMAIL", "UPDATE_PASSWORD"],
            },
        )
        if res.status_code not in (201, 409):
            res.raise_for_status()
        user = self.find_user_by_email(normalized)
        if not user:
            raise KeycloakAdminUnavailable("keycloak_user_create_failed")
        return user

    def update_user(
        self,
        subject: str,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rep = self._rep(subject) or {}
        body: dict[str, Any] = {}
        if first_name is not None:
            body["firstName"] = first_name
        if last_name is not None:
            body["lastName"] = last_name
        if metadata is not None:
            body["attributes"] = {**(rep.get("attributes") or {}), **_encode_meta(metadata)}
        if body:
            self.kc._call("PUT", f"/users/{subject}", json=body).raise_for_status()
        return self.get_user(subject) or {}

    def update_user_metadata(self, subject: str, metadata: dict[str, Any]) -> None:
        try:
            self.update_user(subject, metadata=metadata)
        except Exception:  # noqa: BLE001 — metadata is advisory; never fail the caller
            logger.warning("identity_metadata_update_failed user=%s", subject, exc_info=True)

    def delete_user(self, subject: str) -> None:
        res = self.kc._call("DELETE", f"/users/{subject}")
        if res.status_code not in (204, 404):
            res.raise_for_status()

    def ban_user(self, subject: str) -> None:
        self.kc._call("PUT", f"/users/{subject}", json={"enabled": False}).raise_for_status()
        self.revoke_sessions(subject)

    def unban_user(self, subject: str) -> None:
        self.kc._call("PUT", f"/users/{subject}", json={"enabled": True}).raise_for_status()

    def revoke_sessions(self, subject: str) -> int:
        res = self.kc._call("GET", f"/users/{subject}/sessions")
        if res.status_code == 404:
            return 0
        res.raise_for_status()
        n = len(res.json() or [])
        self.kc.logout(subject)
        return n

    def revoke_pending_invitations(self, email: str) -> int:
        """Keycloak has no separate invitation objects; a pending invite is a user with
        required actions that never signed in. Nothing to revoke."""
        return 0

    def invite_user(
        self,
        email: str,
        *,
        redirect_url: str,
        metadata: dict[str, Any],
        kind: UserKind = "customer",
    ) -> InviteResult:
        normalized = email.lower().strip()
        existing = self.find_user_by_email(normalized)
        if existing:
            self.update_user_metadata(existing["id"], metadata)
            return InviteResult(action="found", subject=existing["id"])
        user = self.create_user(normalized, metadata=metadata)
        sent = self.kc.send_actions_email(
            user["id"],
            user.get("required_actions") or ["UPDATE_PASSWORD"],
            client_id=PORTAL_CLIENTS.get(kind, "pc-customer-portal"),
            redirect_uri=redirect_url,
        )
        if not sent:
            logger.warning("identity_invite_email_failed kind=%s", kind)
        return InviteResult(action="invited", subject=user["id"], invitation_id=user["id"])

    # -- helpers ----------------------------------------------------------------
    @staticmethod
    def snapshot(user: dict[str, Any]) -> DirectoryUserSnapshot | None:
        if not user or not user.get("id") or not user.get("email"):
            return None
        pending = set(user.get("required_actions") or [])
        return DirectoryUserSnapshot(
            subject=str(user["id"]),
            email=str(user["email"]).lower(),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            banned=not user.get("enabled", True),
            locked=False,
            email_verified=bool(user.get("email_verified")),
            password_set="UPDATE_PASSWORD" not in pending,
            last_sign_in_at=_ts(user.get("last_sign_in_at")),
            created_at=_ts(user.get("created_at")),
            metadata=user.get("metadata") if isinstance(user.get("metadata"), dict) else {},
        )

    @staticmethod
    def primary_email(user: dict[str, Any]) -> str | None:
        return (user or {}).get("email")

    @staticmethod
    def primary_phone(user: dict[str, Any]) -> str | None:
        return (user or {}).get("phone")


def is_directory_configured(settings: Settings, kind: UserKind | None = None) -> bool:
    """True when the API can manage Keycloak users (service account configured)."""
    return keycloak_admin.configured(settings)


def directory_for_kind(settings: Settings, kind: UserKind | None = None) -> IdentityDirectory:
    """Every persona lives in the one realm; ``kind`` is kept for call-site readability."""
    return IdentityDirectory(settings)


def fetch_identity_user(settings: Settings, subject: str) -> tuple[dict | None, UserKind | None]:
    """Look a subject up in Keycloak. Kind comes from the ``user_type`` attribute when set."""
    if not subject or not is_directory_configured(settings):
        return None, None
    try:
        user = IdentityDirectory(settings).get_user(subject)
    except Exception:  # noqa: BLE001
        logger.warning("identity_lookup_failed", exc_info=True)
        return None, None
    if not user:
        return None, None
    kind = (user.get("metadata") or {}).get("user_type")
    return user, kind if kind in ALL_USER_KINDS else None


def is_identity_configured(settings: Settings) -> bool:
    """True when bearer verification can work (Keycloak issuer known)."""
    return bool((settings.keycloak_issuer or settings.keycloak_url or "").strip())


def identity_jwks_urls(settings: Settings) -> list[tuple[str, str]]:
    from porterchain_api.auth.keycloak import keycloak_jwks_url

    url = keycloak_jwks_url(settings) if is_identity_configured(settings) else ""
    return [("keycloak", url)] if url else []


def identity_health_checks(settings: Settings) -> dict[str, str]:
    return {
        "keycloak": "ok" if is_identity_configured(settings) else "not_configured",
        "directory": "ok" if is_directory_configured(settings) else "not_configured",
    }


def identity_configuration_mode(settings: Settings) -> str:
    """``keycloak`` when bearer verification is configured, else ``incomplete``."""
    return "keycloak" if is_identity_configured(settings) else "incomplete"
