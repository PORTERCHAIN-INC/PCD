"""Zoho Calendar API client (Canadian DC — accounts.zohocloud.ca)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from porterchain_shared.config.settings import PlatformSettings, get_platform_settings

logger = logging.getLogger(__name__)

_TOKEN_CACHE: dict[str, tuple[str, datetime]] = {}


@dataclass(frozen=True)
class ZohoCalendarEvent:
    uid: str
    title: str
    start: datetime
    end: datetime | None
    location: str | None = None
    description: str | None = None
    organizer: str | None = None
    raw: dict[str, Any] | None = None


class ZohoCalendarClient:
    """OAuth refresh-token client for Zoho Calendar."""

    def __init__(self, settings: PlatformSettings | None = None) -> None:
        self._settings = settings or get_platform_settings()

    @property
    def configured(self) -> bool:
        return self._settings.zoho_calendar_configured

    def integration_status(self) -> dict[str, Any]:
        return {
            "provider": "zoho_calendar",
            "configured": self.configured,
            "accounts_url": self._settings.zoho_calendar_accounts_url,
            "api_base": self._settings.zoho_calendar_api_base,
            "calendar_uid": self._settings.zoho_calendar_uid or None,
            "timezone": self._settings.zoho_calendar_timezone,
            "missing": self._missing_credentials(),
        }

    def _missing_credentials(self) -> list[str]:
        missing: list[str] = []
        if not self._settings.zoho_calendar_client_id:
            missing.append("ZOHO_CALENDAR_CLIENT_ID")
        if not self._settings.zoho_calendar_client_secret:
            missing.append("ZOHO_CALENDAR_CLIENT_SECRET")
        if not self._settings.zoho_calendar_refresh_token:
            missing.append("ZOHO_CALENDAR_REFRESH_TOKEN")
        return missing

    def _access_token(self) -> str:
        if not self.configured:
            raise ValueError("zoho_calendar_not_configured")
        cache_key = self._settings.zoho_calendar_client_id
        cached = _TOKEN_CACHE.get(cache_key)
        if cached and cached[1] > datetime.now(UTC):
            return cached[0]

        url = f"{self._settings.zoho_calendar_accounts_url.rstrip('/')}/oauth/v2/token"
        data = {
            "refresh_token": self._settings.zoho_calendar_refresh_token,
            "client_id": self._settings.zoho_calendar_client_id,
            "client_secret": self._settings.zoho_calendar_client_secret,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, data=data)
            res.raise_for_status()
            payload = res.json()
        token = payload.get("access_token")
        if not token:
            raise ValueError(f"zoho_token_error:{payload.get('error', 'unknown')}")
        expires_in = int(payload.get("expires_in", 3600))
        _TOKEN_CACHE[cache_key] = (token, datetime.now(UTC) + timedelta(seconds=max(60, expires_in - 120)))
        return token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Zoho-oauthtoken {self._access_token()}"}

    def list_calendars(self) -> list[dict[str, Any]]:
        url = f"{self._settings.zoho_calendar_api_base.rstrip('/')}/calendars"
        with httpx.Client(timeout=30.0) as client:
            res = client.get(url, headers=self._headers())
            res.raise_for_status()
            data = res.json()
        calendars = data.get("calendars") or data.get("data") or []
        if isinstance(calendars, dict):
            calendars = calendars.get("calendars", [])
        return list(calendars)

    def resolve_calendar_uid(self) -> str:
        if self._settings.zoho_calendar_uid:
            return self._settings.zoho_calendar_uid
        calendars = self.list_calendars()
        if not calendars:
            raise ValueError("zoho_calendar_not_found")
        for cal in calendars:
            if cal.get("isdefault") or cal.get("is_default"):
                uid = cal.get("uid") or cal.get("calendar_uid")
                if uid:
                    return str(uid)
        first = calendars[0]
        uid = first.get("uid") or first.get("calendar_uid")
        if not uid:
            raise ValueError("zoho_calendar_uid_missing")
        return str(uid)

    def list_events(self, *, start: datetime, end: datetime) -> list[ZohoCalendarEvent]:
        cal_uid = self.resolve_calendar_uid()
        start_key = start.strftime("%Y%m%d")
        end_key = end.strftime("%Y%m%d")
        range_json = quote(json.dumps({"start": start_key, "end": end_key}), safe="")
        url = (
            f"{self._settings.zoho_calendar_api_base.rstrip('/')}"
            f"/calendars/{cal_uid}/events?range={range_json}"
        )
        with httpx.Client(timeout=30.0) as client:
            res = client.get(url, headers=self._headers())
            res.raise_for_status()
            data = res.json()
        events = data.get("events") or data.get("data") or []
        if isinstance(events, dict):
            events = events.get("events", [])
        return [self._parse_event(row) for row in events if isinstance(row, dict)]

    def create_event(
        self,
        *,
        title: str,
        start: datetime,
        end: datetime | None = None,
        description: str | None = None,
        attendee_emails: list[str] | None = None,
        location: str | None = None,
    ) -> str:
        cal_uid = self.resolve_calendar_uid()
        end_dt = end or (start + timedelta(hours=1))
        eventdata = {
            "title": title,
            "dateandtime": {
                "timezone": self._settings.zoho_calendar_timezone,
                "start": start.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ"),
                "end": end_dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ"),
            },
        }
        if description:
            eventdata["description"] = description
        if location:
            eventdata["location"] = location
        if attendee_emails:
            eventdata["attendees"] = [{"email": e, "status": "NEEDS-ACTION"} for e in attendee_emails if e]

        url = (
            f"{self._settings.zoho_calendar_api_base.rstrip('/')}"
            f"/calendars/{cal_uid}/events?eventdata={quote(json.dumps(eventdata), safe='')}"
        )
        with httpx.Client(timeout=30.0) as client:
            res = client.post(url, headers=self._headers())
            res.raise_for_status()
            data = res.json()
        event = data.get("events") or data.get("event") or data
        if isinstance(event, list) and event:
            event = event[0]
        uid = (event or {}).get("uid") or (event or {}).get("event_uid") or data.get("uid")
        if not uid:
            raise ValueError("zoho_event_create_failed")
        return str(uid)

    def delete_event(self, event_uid: str) -> None:
        cal_uid = self.resolve_calendar_uid()
        url = f"{self._settings.zoho_calendar_api_base.rstrip('/')}/calendars/{cal_uid}/events/{event_uid}"
        with httpx.Client(timeout=30.0) as client:
            res = client.delete(url, headers=self._headers())
            if res.status_code not in (200, 204, 404):
                res.raise_for_status()

    def _parse_event(self, row: dict[str, Any]) -> ZohoCalendarEvent:
        title = str(row.get("title") or row.get("summary") or "Event")
        uid = str(row.get("uid") or row.get("event_uid") or row.get("id") or title)
        dt = row.get("dateandtime") or {}
        start_raw = dt.get("start") or row.get("start")
        end_raw = dt.get("end") or row.get("end")
        return ZohoCalendarEvent(
            uid=uid,
            title=title,
            start=self._parse_dt(start_raw),
            end=self._parse_dt(end_raw) if end_raw else None,
            location=row.get("location"),
            description=row.get("description"),
            organizer=(row.get("organizer") or {}).get("email") if isinstance(row.get("organizer"), dict) else row.get("organizer"),
            raw=row,
        )

    @staticmethod
    def _parse_dt(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if not value:
            return datetime.now(UTC)
        text = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass
        for fmt in ("%Y%m%dT%H%M%S", "%Y%m%d"):
            try:
                return datetime.strptime(str(value)[:15], fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return datetime.now(UTC)
