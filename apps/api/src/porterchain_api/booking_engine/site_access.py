"""Construction / jobsite dropoff access notes (§8.1.6)."""

from __future__ import annotations

SITE_ACCESS_DROP_KEY = "site_access_notes"


def enrich_dropoff(dropoff: dict, site_access_notes: str | None) -> dict:
    data = dict(dropoff)
    if site_access_notes and site_access_notes.strip():
        data[SITE_ACCESS_DROP_KEY] = site_access_notes.strip()
    return data


def extract_site_access_notes(dropoff: dict | None) -> str | None:
    if not isinstance(dropoff, dict):
        return None
    value = dropoff.get(SITE_ACCESS_DROP_KEY)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def dropoff_address_fields(dropoff: dict | None) -> dict:
    data = dict(dropoff or {})
    data.pop(SITE_ACCESS_DROP_KEY, None)
    return data
