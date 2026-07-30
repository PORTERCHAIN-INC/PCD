"""Fleetbase-related health probes (split from diagnostics_probes for LOC gate)."""

from __future__ import annotations

from typing import Any

from porterchain_api.admin_engine.diagnostics_helpers import HealthClass, _probe_http
from porterchain_api.config import Settings
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration


class DiagnosticsFleetbaseProbesMixin:
    def _probe_fleetbase_console(self, settings: Settings) -> dict[str, Any]:
        # When SSO/bridge are off, console is not part of the prod surface — do not fail health.
        if not settings.fleetbase_sso_enabled and not settings.fleetbase_dispatch_bridge:
            return {
                "status": "healthy",
                "details": {
                    "skipped": True,
                    "note": "Fleetbase console not provisioned (SSO/bridge disabled)",
                },
            }
        url = (settings.fleetbase_console_url or "").strip() or "http://localhost:4200"
        status, latency, err = _probe_http(url, local_optional=settings.app_env == "local")
        if settings.app_env == "local" and status == "warning":
            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {"url": url, "skipped": True, "note": "Optional locally"},
            }
        return {
            "status": status,
            "latency_ms": latency,
            "errors": [err] if err and status == "critical" else [],
            "warnings": [err] if err and status == "warning" else [],
            "details": {"url": url},
        }

    def _probe_fleetbase_adapter(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        try:
            adapter = get_fleetbase_integration(settings)
            if not adapter.is_enabled:
                # Bridge off until a Fleetbase host is provisioned (not on the API droplet).
                return {
                    "status": "healthy",
                    "details": {
                        "enabled": False,
                        "skipped": True,
                        "note": "Dispatch bridge disabled — Fleetbase host not provisioned",
                    },
                }
            status: HealthClass = "healthy"
            warnings: list[str] = []
            details = {"enabled": adapter.is_enabled}
            if live and adapter.is_enabled:
                status, latency, err = _probe_http(
                    settings.fleetbase_api_url,
                    local_optional=settings.app_env == "local",
                )
                if settings.app_env == "local" and status == "warning":
                    return {"status": "healthy", "latency_ms": latency, "details": {**details, "skipped": True}}
                if err:
                    warnings.append(err)
                return {
                    "status": status if status != "critical" else "warning",
                    "latency_ms": latency,
                    "warnings": warnings,
                    "details": details,
                }
            return {"status": status, "warnings": warnings, "details": details}
        except Exception as exc:  # noqa: BLE001
            return {"status": "critical", "errors": [str(exc)]}

    def _probe_fleetbase(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        if not settings.fleetbase_dispatch_bridge:
            return {
                "status": "healthy",
                "details": {
                    "skipped": True,
                    "note": "Dispatch bridge disabled — Fleetbase host not provisioned",
                },
            }
        status, latency, err = _probe_http(
            settings.fleetbase_api_url,
            local_optional=settings.app_env == "local",
        )
        if settings.app_env == "local" and status == "warning":
            return {
                "status": "healthy",
                "latency_ms": latency,
                "details": {"url": settings.fleetbase_api_url, "skipped": True},
            }
        warnings: list[str] = []
        if not settings.fleetbase_api_key:
            warnings.append("Fleetbase API key not configured — outbound sync may fail")
        return {
            "status": status if status != "critical" else "warning",
            "latency_ms": latency,
            "errors": [err] if err else [],
            "warnings": warnings,
            "details": {"url": settings.fleetbase_api_url, "authenticated": bool(settings.fleetbase_api_key)},
        }
