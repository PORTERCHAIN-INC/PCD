"""Admin Lead Ingest settings: status (no secret values) and validated change requests.

Secrets live in SOPS + age (``secrets/<host>.enc.yaml``, doc 37). The API cannot decrypt or
write that file, so a save validates the input and returns the key names an operator must set
with ``sops`` before the next deploy. Values are never echoed back.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.config import Settings, get_settings

logger = logging.getLogger(__name__)

SECRETS_FILE = "secrets/droplet.enc.yaml"

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


def _configured(settings: Settings, env_key: str) -> bool:
    if env_key == "REFERRAL_CREDIT_CENTS":
        return True
    return bool(_runtime_value(settings, env_key))


def lead_ingest_settings_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    secrets_status = {
        key: {
            "configured": _configured(settings, key),
            "in_runtime": bool(_runtime_value(settings, key)),
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
        "secrets_store": {"kind": "sops", "file": SECRETS_FILE, "writable": False},
        "secrets": secrets_status,
        "visible": visible,
        "note": (
            "Secret values are never shown. These keys live in the SOPS file; a save checks "
            f"the values and lists the keys to set with `sops {SECRETS_FILE}`, then redeploy."
        ),
    }


def update_lead_ingest_settings(
    db: Session,
    ctx: AdminContext,
    body: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Validate visible fields and secret inputs; return the keys to set in SOPS.

    Secret keys: omit or empty = leave unchanged. Nothing is written by the API.
    """
    settings = settings or get_settings()
    to_write: dict[str, str] = {}

    if body.get("generate"):
        raise ValueError("generate_unsupported_use_sops")

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

    keys = sorted(to_write.keys())
    save: dict[str, Any] = {
        "ok": True,
        "applied": False,
        "keys": keys,
        "how": (
            f"Run `sops {SECRETS_FILE}` on the ops machine, set these keys, then redeploy."
            if keys
            else "noop"
        ),
    }
    try:
        log_admin_audit(
            db,
            ctx,
            action="settings.lead_ingest.change_requested",
            resource_type="lead_ingest",
            resource_id="sops",
            payload={"keys": keys},
        )
        db.commit()
    except Exception:
        logger.exception("lead_ingest_audit_failed")
        db.rollback()

    status = lead_ingest_settings_status(settings)
    status["save"] = save
    return status


__all__ = [
    "SECRET_FIELDS",
    "VISIBLE_FIELDS",
    "lead_ingest_settings_status",
    "update_lead_ingest_settings",
]
