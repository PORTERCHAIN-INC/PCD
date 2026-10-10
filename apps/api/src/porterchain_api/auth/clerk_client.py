"""Clerk Backend API adapter — user directory CRUD (no password reads; Clerk owns credentials)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CLERK_API = "https://api.clerk.com/v1"


def _clerk_error_text(res: httpx.Response) -> str:
    try:
        body = res.json()
    except Exception:
        return ""
    errors = body.get("errors") if isinstance(body, dict) else None
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        return ""
    return str(errors[0].get("long_message") or errors[0].get("message") or "").strip()


@dataclass(frozen=True)
class ClerkInviteResult:
    action: str
    clerk_user_id: str | None = None
    clerk_invitation_id: str | None = None


@dataclass(frozen=True)
class ClerkUserSnapshot:
    clerk_user_id: str
    email: str
    first_name: str | None
    last_name: str | None
    banned: bool
    locked: bool
    email_verified: bool
    password_set: bool
    last_sign_in_at: datetime | None
    created_at: datetime | None
    public_metadata: dict[str, Any]

    @property
    def clerk_status(self) -> str:
        if self.banned:
            return "banned"
        if self.locked:
            return "locked"
        if not self.last_sign_in_at:
            return "never_signed_in"
        return "active"


class ClerkClient:
    def __init__(self, secret_key: str) -> None:
        if not secret_key.strip():
            raise ValueError("clerk_secret_key_required")
        self._secret = secret_key.strip()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._secret}", "Content-Type": "application/json"}

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        with httpx.Client(timeout=20.0) as client:
            res = client.get(
                f"{CLERK_API}/users",
                headers=self._headers(),
                params=[("email_address", email.lower().strip()), ("limit", "5")],
            )
            res.raise_for_status()
            users = res.json()
            if isinstance(users, list) and users:
                return users[0]
            if isinstance(users, dict) and users.get("data"):
                return users["data"][0] if users["data"] else None
        return None

    def get_user(self, clerk_user_id: str) -> dict[str, Any] | None:
        with httpx.Client(timeout=20.0) as client:
            res = client.get(f"{CLERK_API}/users/{clerk_user_id}", headers=self._headers())
            if res.status_code == 404:
                return None
            res.raise_for_status()
            body = res.json()
            return body if isinstance(body, dict) else None

    def list_users(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        query: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        params: list[tuple[str, str | int]] = [("limit", min(limit, 500)), ("offset", offset)]
        if query and query.strip():
            params.append(("query", query.strip()))
        with httpx.Client(timeout=30.0) as client:
            res = client.get(f"{CLERK_API}/users", headers=self._headers(), params=params)
            res.raise_for_status()
            body = res.json()
            if isinstance(body, list):
                return body, len(body)
            if isinstance(body, dict):
                data = body.get("data") or []
                total = int(body.get("total_count") or len(data))
                return data, total
        return [], 0

    def create_user(
        self,
        email: str,
        *,
        password: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        public_metadata: dict[str, Any] | None = None,
        skip_password_requirement: bool = False,
    ) -> dict[str, Any]:
        normalized = email.lower().strip()
        payload: dict[str, Any] = {
            "email_address": [normalized],
            "skip_password_requirement": skip_password_requirement or not password,
        }
        if password:
            payload["password"] = password
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if public_metadata:
            payload["public_metadata"] = public_metadata
        with httpx.Client(timeout=20.0) as client:
            res = client.post(f"{CLERK_API}/users", headers=self._headers(), json=payload)
            res.raise_for_status()
            body = res.json()
            if not isinstance(body, dict):
                raise ValueError("clerk_create_failed")
            return body

    def update_user(
        self,
        clerk_user_id: str,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        public_metadata: dict[str, Any] | None = None,
        password: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if first_name is not None:
            payload["first_name"] = first_name
        if last_name is not None:
            payload["last_name"] = last_name
        if public_metadata is not None:
            payload["public_metadata"] = public_metadata
        if password:
            payload["password"] = password
        with httpx.Client(timeout=20.0) as client:
            res = client.patch(
                f"{CLERK_API}/users/{clerk_user_id}",
                headers=self._headers(),
                json=payload,
            )
            res.raise_for_status()
            body = res.json()
            return body if isinstance(body, dict) else {}

    def delete_user(self, clerk_user_id: str) -> None:
        with httpx.Client(timeout=20.0) as client:
            res = client.delete(f"{CLERK_API}/users/{clerk_user_id}", headers=self._headers())
            if res.status_code == 404:
                return
            res.raise_for_status()

    def ban_user(self, clerk_user_id: str) -> None:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(f"{CLERK_API}/users/{clerk_user_id}/ban", headers=self._headers())
            res.raise_for_status()

    def revoke_sessions(self, clerk_user_id: str) -> int:
        """Revoke every active Clerk session for this user (signs them out everywhere)."""
        revoked = 0
        with httpx.Client(timeout=20.0) as client:
            res = client.get(f"{CLERK_API}/sessions", headers=self._headers(),
                             params={"user_id": clerk_user_id, "status": "active", "limit": 100})
            if res.status_code == 404:
                return 0
            res.raise_for_status()
            body = res.json()
            rows = body.get("data", []) if isinstance(body, dict) else body
            for s in rows or []:
                sid = s.get("id") if isinstance(s, dict) else None
                if sid:
                    client.post(f"{CLERK_API}/sessions/{sid}/revoke", headers=self._headers()).raise_for_status()
                    revoked += 1
        return revoked

    def unban_user(self, clerk_user_id: str) -> None:
        with httpx.Client(timeout=20.0) as client:
            res = client.delete(f"{CLERK_API}/users/{clerk_user_id}/ban", headers=self._headers())
            res.raise_for_status()

    @staticmethod
    def _parse_ts(value: str | int | float | None) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000 if value > 1e12 else value, tz=UTC)
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None

    @classmethod
    def snapshot(cls, user: dict[str, Any]) -> ClerkUserSnapshot | None:
        email = cls.primary_email(user)
        if not email or not user.get("id"):
            return None
        emails = user.get("email_addresses") or []
        verified = False
        for entry in emails:
            if entry.get("email_address", "").lower() == email.lower():
                verified = (entry.get("verification") or {}).get("status") == "verified"
                break
        return ClerkUserSnapshot(
            clerk_user_id=str(user["id"]),
            email=email.lower(),
            first_name=user.get("first_name"),
            last_name=user.get("last_name"),
            banned=bool(user.get("banned")),
            locked=bool(user.get("locked")),
            email_verified=verified,
            password_set=bool(user.get("password_enabled")),
            last_sign_in_at=cls._parse_ts(user.get("last_sign_in_at")),
            created_at=cls._parse_ts(user.get("created_at")),
            public_metadata=user.get("public_metadata") if isinstance(user.get("public_metadata"), dict) else {},
        )

    @staticmethod
    def primary_email(user: dict[str, Any]) -> str | None:
        emails = user.get("email_addresses") or []
        if not emails:
            return None
        primary_id = user.get("primary_email_address_id")
        for entry in emails:
            if entry.get("id") == primary_id:
                return entry.get("email_address")
        return emails[0].get("email_address")

    @staticmethod
    def primary_phone(user: dict[str, Any]) -> str | None:
        phones = user.get("phone_numbers") or []
        if not phones:
            return None
        primary_id = user.get("primary_phone_number_id")
        for entry in phones:
            if entry.get("id") == primary_id:
                return entry.get("phone_number")
        return phones[0].get("phone_number")

    def update_user_metadata(self, clerk_user_id: str, public_metadata: dict[str, Any]) -> None:
        try:
            existing = self.get_user(clerk_user_id)
            current = (existing or {}).get("public_metadata") or {}
            if not isinstance(current, dict):
                current = {}
            merged = {**current, **public_metadata}
            with httpx.Client(timeout=20.0) as client:
                res = client.patch(
                    f"{CLERK_API}/users/{clerk_user_id}",
                    headers=self._headers(),
                    json={"public_metadata": merged},
                )
                res.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "clerk_metadata_update_failed user=%s status=%s",
                clerk_user_id,
                exc.response.status_code,
            )
        except Exception:
            logger.warning("clerk_metadata_update_failed user=%s", clerk_user_id, exc_info=True)

    def invite_user(
        self,
        email: str,
        *,
        redirect_url: str,
        public_metadata: dict[str, Any],
    ) -> ClerkInviteResult:
        normalized = email.lower().strip()
        existing = self.find_user_by_email(normalized)
        if existing:
            clerk_user_id = str(existing["id"])
            self.update_user_metadata(clerk_user_id, public_metadata)
            return ClerkInviteResult(action="found", clerk_user_id=clerk_user_id)

        payload = {
            "email_address": normalized,
            "redirect_url": redirect_url,
            "public_metadata": public_metadata,
        }
        with httpx.Client(timeout=20.0) as client:
            res = client.post(f"{CLERK_API}/invitations", headers=self._headers(), json=payload)
            message = _clerk_error_text(res)
            if res.status_code >= 400 and "already" in f"{message} {res.text}".lower():
                return ClerkInviteResult(action="invite_pending")
            if res.status_code >= 400:
                logger.warning("clerk_invite_failed status=%s", res.status_code)
                raise ValueError(message or "Clerk could not send the invite.")
            body = res.json()
            invitation_id = body.get("id") if isinstance(body, dict) else None
            return ClerkInviteResult(action="invited", clerk_invitation_id=str(invitation_id) if invitation_id else None)
