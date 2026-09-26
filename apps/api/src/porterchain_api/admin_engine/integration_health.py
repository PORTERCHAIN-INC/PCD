"""Integration health dashboard payload — extracted from AdminSettingsService (shrink ENG-G2)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.clerk_registry import is_clerk_configured
from porterchain_api.config import Settings
from porterchain_api.platform.health import readiness
from porterchain_api.platform.health_status import normalize_check_status
from porterchain_shared.config.settings import PlatformSettings


def build_integration_health(
    db: Session,
    settings: Settings,
    *,
    ready: dict[str, Any] | None = None,
    nvidia_nim_configured: bool,
    nvidia_model: str | None = None,
) -> dict[str, Any]:
    """Compose integration status triad for settings / diagnostics dashboards."""
    ready = ready if ready is not None else readiness(db, settings)
    platform = PlatformSettings()
    checks = ready.get("checks", {})

    def _entry(raw: str, **extra: Any) -> dict[str, Any]:
        return {"status": normalize_check_status(raw), "raw": raw, **extra}

    return {
        "api": _entry(str(ready.get("status", "unknown"))),
        "database": _entry(str(checks.get("database", "unknown"))),
        "redis": _entry(str(checks.get("redis", "unknown"))),
        "queue": _entry(str(checks.get("redis", "unknown"))),
        "stripe": _entry(
            str(checks.get("stripe", "unknown")),
            mock_mode=settings.stripe_mock,
            configured=bool(settings.stripe_secret),
        ),
        "fleetbase": _entry(
            str(checks.get("fleetbase", "unknown")),
            bridge_enabled=settings.fleetbase_dispatch_bridge,
            configured=bool(settings.fleetbase_api_key),
            api_url=settings.fleetbase_api_url,
        ),
        "google_maps": _entry(
            "configured" if platform.google_maps_api_key else "unconfigured",
            role="places_and_tiles_only",
            note="Routing uses Valhalla/OSRM — not Google",
        ),
        "firebase": _entry(
            "configured" if platform.firebase_project_id else "unconfigured",
            project_id=platform.firebase_project_id or None,
        ),
        "clerk": _entry(
            "configured"
            if is_clerk_configured(settings)
            else ("dev_bypass" if settings.clerk_dev_bypass else "unconfigured")
        ),
        "storage": _entry("local", note="File storage via API deployment volume"),
        "email": _entry(
            "configured" if platform.smtp_host else "unconfigured",
            **{"from": platform.smtp_from or None},
        ),
        "sms": _entry(
            "log_only",
            note="SMS provider not configured — Clerk handles phone verification",
        ),
        "push": _entry(
            "configured" if platform.firebase_project_id else "unconfigured",
            project_id=platform.firebase_project_id or None,
        ),
        "nvidia_nim": _entry(
            "configured" if nvidia_nim_configured else "unconfigured",
            provider="nvidia_nim",
            model=nvidia_model or "meta/llama-3.2-11b-vision-instruct",
            phase2_intelligence=bool(settings.phase2_flags.get("intelligence")),
            phase2_ai_dispatch=bool(settings.phase2_flags.get("ai_dispatch")),
            note="Read-only language assist — never on pay / Valhalla / Fleetbase write path",
        ),
        "nvidia_cuopt": _entry(
            "shadow" if bool(settings.phase2_flags.get("cuopt_shadow")) else "disabled",
            phase2_cuopt_shadow=bool(settings.phase2_flags.get("cuopt_shadow")),
            commit_sot="fleetbase_vroom",  # fleetbase-first:ok — label: Fleetbase SoT
            note="Shadow A/B only — never commits routes; Fleetbase orchestrator remains SoT",
        ),
        "routing": {
            "primary": "valhalla",
            "fallback": "osrm",
            "optimize_sot": "fleetbase_vroom",  # fleetbase-first:ok — label: Fleetbase SoT
            "merchant_route_import": "nearest_neighbor_labeled",
            "degrade_labels": {
                "valhalla_down": "osrm_fallback",
                "fleetbase_bridge_off": "optimize_unavailable",
                "cuopt_shadow_error": "vroom_only",
            },
        },
    }


__all__ = ["build_integration_health"]
