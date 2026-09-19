"""Admin Lead Ingest settings — status (no secret values) + Doppler write-through."""

from __future__ import annotations

import json
import logging
import os
import secrets
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.config import Settings, get_settings
from porterchain_api.integrations.doppler_secrets import (
    DopplerNotConfiguredError,
    doppler_configured,
    list_secret_names,
    set_secrets,
)

logger = logging.getLogger(__name__)

# Write-only secrets (never returned to UI).
SECRET_FIELDS: tuple[str, ...] = (
    "PUBLIC_INGEST_API_KEY",
    "GOOGLE_LEAD_WEBHOOK_SECRET",
    "SOCIAL_LEAD_WEBHOOK_SECRET",
    "META_APP_SECRET",
    "META_WEBHOOK_VERIFY_TOKEN",
    "META_CAPI_ACCESS_TOKEN",
    "LINKEDIN_CAPI_TOKEN",
)

# Visible ops config (safe to show / edit in clear).
VISIBLE_FIELDS: tuple[str, ...] = (
    "META_PIXEL_ID",
    "LINKEDIN_CONVERSION_URN",
    "LEAD_TERRITORY_MAP_JSON",
    "LEAD_ROUND_ROBIN_JSON",
    "LEAD_SLA_MINUTES_JSON",
    "REFERRAL_CREDIT_CENTS",
)

_SETTINGS_ATTR: dict[str, str] = {
    "PUBLIC_INGEST_API_KEY": "public_ingest_api_key",
    "GOOGLE_LEAD_WEBHOOK_SECRET": "google_lead_webhook_secret",
    "SOCIAL_LEAD_WEBHOOK_SECRET": "social_lead_webhook_secret",
    "META_APP_SECRET": "meta_app_secret",
    "META_WEBHOOK_VERIFY_TOKEN": "meta_webhook_verify_token",
    "META_CAPI_ACCESS_TOKEN": "meta_capi_access_token",
    "META_PIXEL_ID": "meta_pixel_id",
    "LINKEDIN_CAPI_TOKEN": "linkedin_capi_token",
    "LINKEDIN_CONVERSION_URN": "linkedin_conversion_urn",
    "LEAD_TERRITORY_MAP_JSON": "lead_territory_map_json",
    "LEAD_ROUND_ROBIN_JSON": "lead_round_robin_json",
    "LEAD_SLA_MINUTES_JSON": "lead_sla_minutes_json",
    "REFERRAL_CREDIT_CENTS": "referral_credit_cents",
}


def _runtime_value(settings: Settings, env_key: str) -> str:
    attr = _SETTINGS_ATTR[env_key]
    raw = getattr(settings, attr, None)
    if raw is None:
        return ""
    return str(raw).strip()


def _configured(settings: Settings, env_key: str, *, doppler_names: set[str]) -> bool:
    if env_key == "REFERRAL_CREDIT_CENTS":
        return True
    if _runtime_value(settings, env_key):
        return True
    return env_key in doppler_names


def lead_ingest_settings_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    names = list_secret_names(settings) if doppler_configured(settings) else set()
    secrets_status = {
        key: {
            "configured": _configured(settings, key, doppler_names=names),
            "in_runtime": bool(_runtime_value(settings, key)),
            "in_doppler": key in names,
        }
        for key in SECRET_FIELDS
    }
    visible = {
        "META_PIXEL_ID": _runtime_value(settings, "META_PIXEL_ID"),
        "LINKEDIN_CONVERSION_URN": _runtime_value(settings, "LINKEDIN_CONVERSION_URN"),
        "LEAD_TERRITORY_MAP_JSON": _runtime_value(settings, "LEAD_TERRITORY_MAP_JSON"),
        "LEAD_ROUND_ROBIN_JSON": _runtime_value(settings, "LEAD_ROUND_ROBIN_JSON"),
        "LEAD_SLA_MINUTES_JSON": _runtime_value(settings, "LEAD_SLA_MINUTES_JSON"),
        "REFERRAL_CREDIT_CENTS": int(settings.referral_credit_cents or 0),
    }
    return {
        "doppler": {
            "configured": doppler_configured(settings),
            "project": settings.doppler_project,
            "config": settings.doppler_config,
        },
        "secrets": secrets_status,
        "visible": visible,
        "note": (
            "Secret values are never shown. Saving writes to Doppler and updates this API process; "
            "other replicas need sync-secrets + recreate to pick up changes."
        ),
    }


def _apply_runtime(env_key: str, value: str) -> None:
    """Best-effort: update process env + Settings cache for this worker."""
    os.environ[env_key] = value
    attr = _SETTINGS_ATTR.get(env_key)
    if not attr:
        return
    try:
        get_settings.cache_clear()
    except Exception:
        pass


def update_lead_ingest_settings(
    db: Session,
    ctx: AdminContext,
    body: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Apply visible fields + optional secret writes.

    Secret keys: omit or empty = leave unchanged; non-empty = set.
    Special: ``generate`` list may include GOOGLE_LEAD_WEBHOOK_SECRET /
    SOCIAL_LEAD_WEBHOOK_SECRET / META_WEBHOOK_VERIFY_TOKEN / PUBLIC_INGEST_API_KEY.
    """
    settings = settings or get_settings()
    to_write: dict[str, str] = {}

    generate = body.get("generate") or []
    if isinstance(generate, list):
        for key in generate:
            if key not in (
                "GOOGLE_LEAD_WEBHOOK_SECRET",
                "SOCIAL_LEAD_WEBHOOK_SECRET",
                "META_WEBHOOK_VERIFY_TOKEN",
                "PUBLIC_INGEST_API_KEY",
            ):
                raise ValueError(f"cannot_generate:{key}")
            to_write[key] = secrets.token_hex(32)

    secrets_in = body.get("secrets") if isinstance(body.get("secrets"), dict) else {}
    for key in SECRET_FIELDS:
        if key in to_write:
            continue
        if key not in secrets_in:
            continue
        val = secrets_in.get(key)
        if val is None:
            continue
        text = str(val).strip()
        if not text:
            continue  # leave unchanged
        if len(text) > 8000:
            raise ValueError(f"secret_too_long:{key}")
        to_write[key] = text

    visible_in = body.get("visible") if isinstance(body.get("visible"), dict) else {}
    if "META_PIXEL_ID" in visible_in:
        to_write["META_PIXEL_ID"] = str(visible_in.get("META_PIXEL_ID") or "").strip()
    if "LINKEDIN_CONVERSION_URN" in visible_in:
        to_write["LINKEDIN_CONVERSION_URN"] = str(
            visible_in.get("LINKEDIN_CONVERSION_URN") or ""
        ).strip()
    if "LEAD_TERRITORY_MAP_JSON" in visible_in:
        raw = str(visible_in.get("LEAD_TERRITORY_MAP_JSON") or "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("lead_territory_map_json_invalid") from exc
            if not isinstance(parsed, dict):
                raise ValueError("lead_territory_map_json_must_be_object")
        to_write["LEAD_TERRITORY_MAP_JSON"] = raw
    if "LEAD_ROUND_ROBIN_JSON" in visible_in:
        raw = str(visible_in.get("LEAD_ROUND_ROBIN_JSON") or "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("lead_round_robin_json_invalid") from exc
            if not isinstance(parsed, list):
                raise ValueError("lead_round_robin_json_must_be_array")
            if not all(isinstance(x, (str, int)) and str(x).strip() for x in parsed):
                raise ValueError("lead_round_robin_json_entries_must_be_ids")
        to_write["LEAD_ROUND_ROBIN_JSON"] = raw
    if "LEAD_SLA_MINUTES_JSON" in visible_in:
        raw = str(visible_in.get("LEAD_SLA_MINUTES_JSON") or "").strip()
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("lead_sla_minutes_json_invalid") from exc
            if not isinstance(parsed, dict):
                raise ValueError("lead_sla_minutes_json_must_be_object")
            for k, v in parsed.items():
                try:
                    int(v)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"lead_sla_minutes_invalid:{k}") from exc
        to_write["LEAD_SLA_MINUTES_JSON"] = raw
    if "REFERRAL_CREDIT_CENTS" in visible_in:
        try:
            cents = int(visible_in.get("REFERRAL_CREDIT_CENTS"))
        except (TypeError, ValueError) as exc:
            raise ValueError("referral_credit_cents_invalid") from exc
        if cents < 0 or cents > 10_000_000:
            raise ValueError("referral_credit_cents_out_of_range")
        to_write["REFERRAL_CREDIT_CENTS"] = str(cents)

    # Empty visible clears are allowed (PIXEL / URN / TERRITORY); secrets never clear via empty.
    doppler_result: dict[str, Any]
    if to_write:
        try:
            doppler_result = set_secrets(settings, to_write)
        except DopplerNotConfiguredError as exc:
            raise ValueError("doppler_token_missing") from exc
        except RuntimeError as exc:
            raise ValueError(str(exc)) from exc
        for key, value in to_write.items():
            _apply_runtime(key, value)
    else:
        doppler_result = {"ok": True, "written": [], "skipped": "noop"}

    try:
        log_admin_audit(
            db,
            ctx,
            action="settings.lead_ingest.update",
            resource_type="lead_ingest",
            resource_id="doppler",
            payload={"keys": sorted(to_write.keys()), "doppler_ok": bool(doppler_result.get("ok"))},
        )
        db.commit()
    except Exception:
        logger.exception("lead_ingest_audit_failed")
        db.rollback()

    status = lead_ingest_settings_status(get_settings())
    status["save"] = doppler_result
    return status


__all__ = [
    "SECRET_FIELDS",
    "VISIBLE_FIELDS",
    "lead_ingest_settings_status",
    "update_lead_ingest_settings",
]
