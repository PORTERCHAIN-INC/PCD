"""Minimal Doppler Secrets API client (admin write-through). Never logs secret values."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from porterchain_api.config import Settings

logger = logging.getLogger(__name__)

_API = "https://api.doppler.com/v3"


class DopplerNotConfiguredError(RuntimeError):
    """DOPPLER_TOKEN missing — cannot write secrets."""


def doppler_configured(settings: Settings) -> bool:
    return bool((settings.doppler_token or "").strip())


def _headers(settings: Settings) -> dict[str, str]:
    token = (settings.doppler_token or "").strip()
    if not token:
        raise DopplerNotConfiguredError("doppler_token_missing")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def list_secret_names(settings: Settings) -> set[str]:
    """Names present in Doppler config (no values). Empty set if unconfigured/error."""
    if not doppler_configured(settings):
        return set()
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(
                f"{_API}/configs/config/secrets/names",
                headers=_headers(settings),
                params={
                    "project": settings.doppler_project,
                    "config": settings.doppler_config,
                },
            )
        if not resp.is_success:
            logger.warning("doppler_list_names_http_%s", resp.status_code)
            return set()
        data = resp.json()
        names = data.get("names") or data.get("secrets") or []
        if isinstance(names, dict):
            return {str(k) for k in names}
        return {str(n) for n in names}
    except DopplerNotConfiguredError:
        return set()
    except Exception:
        logger.exception("doppler_list_names_failed")
        return set()


def set_secrets(settings: Settings, secrets: dict[str, str]) -> dict[str, Any]:
    """
    Upsert secrets in Doppler. ``secrets`` values must be non-empty strings.
    Returns ``{ok, written, project, config}`` or raises on failure.
    """
    payload = {k: v for k, v in secrets.items() if v is not None and str(v) != ""}
    if not payload:
        return {
            "ok": True,
            "written": [],
            "project": settings.doppler_project,
            "config": settings.doppler_config,
            "skipped": "empty",
        }
    if not doppler_configured(settings):
        raise DopplerNotConfiguredError("doppler_token_missing")

    body = {
        "project": settings.doppler_project,
        "config": settings.doppler_config,
        "secrets": payload,
    }
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            f"{_API}/configs/config/secrets",
            headers=_headers(settings),
            json=body,
        )
    if not resp.is_success:
        logger.warning("doppler_set_secrets_http_%s", resp.status_code)
        raise RuntimeError(f"doppler_http_{resp.status_code}")
    logger.info(
        "doppler_secrets_written",
        extra={
            "project": settings.doppler_project,
            "config": settings.doppler_config,
            "keys": sorted(payload.keys()),
        },
    )
    return {
        "ok": True,
        "written": sorted(payload.keys()),
        "project": settings.doppler_project,
        "config": settings.doppler_config,
    }


__all__ = [
    "DopplerNotConfiguredError",
    "doppler_configured",
    "list_secret_names",
    "set_secrets",
]
