"""Integration health dashboard payload — extracted from AdminSettingsService (shrink ENG-G2)."""

from __future__ import annotations

from typing import Any

from porterchain_shared.config.settings import PlatformSettings
from sqlalchemy.orm import Session

from porterchain_api.auth.identity_directory import is_identity_configured
from porterchain_api.config import Settings
from porterchain_api.platform.health import readiness
from porterchain_api.platform.health_status import normalize_check_status


def build_integration_health(
    db: Session,
    settings: Settings,
    *,
    ready: dict[str, Any] | None = None,
    llm_configured: bool = False,
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
        "dispatch": _entry(str(checks.get("dispatch", "porterchain"))),
        "maps": _entry(
            "configured",
            role="maplibre_tiles_and_photon_search",
            note=(
                "MapLibre + self-hosted PMTiles, Photon search (Nominatim fallback), "
                "Valhalla/OSRM routing. No third-party map or places API."
            ),
        ),
        "firebase": _entry(
            "configured" if platform.firebase_project_id else "unconfigured",
            project_id=platform.firebase_project_id or None,
        ),
        "keycloak": _entry(
            "configured"
            if is_identity_configured(settings)
            else ("dev_bypass" if settings.auth_dev_bypass else "unconfigured")
        ),
        "storage": _entry("local", note="File storage via API deployment volume"),
        "email": _entry(
            "configured" if platform.smtp_host else "unconfigured",
            **{"from": platform.smtp_from or None},
        ),
        "sms": _entry(
            "log_only",
            note="SMS provider not configured — Keycloak handles phone verification",
        ),
        "push": _entry(
            "configured" if platform.firebase_project_id else "unconfigured",
            project_id=platform.firebase_project_id or None,
        ),
        "llm": _entry(
            "configured" if llm_configured else "disabled",
            provider="none",
            feature_ai=False,
            phase2_intelligence=bool(settings.phase2_flags.get("intelligence")),
            phase2_ai_dispatch=bool(settings.phase2_flags.get("ai_dispatch")),
            note="FEATURE_AI=false (doc 60 R2): no LLM client ships; heuristics only.",
        ),
        "routing": {
            "primary": "valhalla",
            "fallback": "osrm",
            "optimize_sot": "porterchain_ortools",
            "merchant_route_import": "day_plan",
            "degrade_labels": {
                "valhalla_down": "osrm_fallback",
                "day_plan_unavailable": "optimize_unavailable",
            },
        },
    }


__all__ = ["build_integration_health"]
