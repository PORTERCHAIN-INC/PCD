"""Fleetbase-related health probes (split from diagnostics_probes for LOC gate)."""

from __future__ import annotations

import time
from typing import Any

from porterchain_api.admin_engine.diagnostics_helpers import HealthClass, _probe_http
from porterchain_api.config import Settings
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration


class DiagnosticsFleetbaseProbesMixin:
    def _probe_fleetbase_console(self, settings: Settings) -> dict[str, Any]:
        # Ember console is not a PorterChain surface. The bond is the Fleetbase API.
        return {
            "status": "healthy",
            "details": {
                "skipped": True,
                "api_url": settings.fleetbase_api_url,
                "note": "Console is not used. Fleetbase is reached only through the API adapter.",
            },
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
                # Permanent bond: authenticated GET /v1/orders, not bare host ping.
                bond = adapter.verify_bond(reset_circuit=True)
                details = {
                    **details,
                    "bonded": bool(bond.get("bonded")),
                    "company_uuid_configured": bool(bond.get("company_uuid_configured")),
                    "api_key_configured": bool(bond.get("api_key_configured")),
                }
                if bond.get("bonded"):
                    return {
                        "status": "healthy",
                        "latency_ms": bond.get("latency_ms"),
                        "warnings": warnings,
                        "details": details,
                    }
                err = str(bond.get("error") or "bond_failed")
                if settings.app_env == "local":
                    # Local stack may be mid-heal; surface warning, not critical.
                    return {
                        "status": "warning",
                        "latency_ms": bond.get("latency_ms"),
                        "warnings": [err],
                        "details": details,
                    }
                return {
                    "status": "warning",
                    "latency_ms": bond.get("latency_ms"),
                    "warnings": [err],
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

    def _probe_vroom(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:  # fleetbase-first:ok
        """VROOM is Fleetbase's TSP engine — probe orchestrator only, never a PC HTTP port."""  # fleetbase-first:ok
        if not settings.fleetbase_dispatch_bridge:
            return {
                "status": "healthy",
                "details": {"skipped": True, "note": "VROOM lives in Fleetbase; bridge off"},  # fleetbase-first:ok
            }
        try:
            adapter = get_fleetbase_integration(settings)
            if not adapter.is_enabled:
                return {
                    "status": "healthy",
                    "details": {
                        "skipped": True,
                        "enabled": False,
                        "note": "Fleetbase adapter disabled; VROOM not probed",  # fleetbase-first:ok
                    },
                }
            from porterchain_fleetbase_adapter.exceptions import FleetbaseApiError
            from porterchain_fleetbase_adapter.orchestrator import RUN_PATH

            start = time.monotonic()
            try:
                raw = adapter.client.post(
                    RUN_PATH,
                    json={
                        "mode": "allocate",
                        "order_ids": [],
                        "orders": [],
                        "options": {"engine": "vroom"},  # fleetbase-first:ok
                    },
                )
                latency = (time.monotonic() - start) * 1000
                return {
                    "status": "healthy",
                    "latency_ms": latency,
                    "details": {
                        "path": RUN_PATH,
                        "via": "fleetbase_orchestrator",
                        "keys": list(raw)[:12] if isinstance(raw, dict) else type(raw).__name__,
                    },
                }
            except FleetbaseApiError as exc:
                latency = (time.monotonic() - start) * 1000
                body = exc.body or str(exc)
                saas = "Invalid API Key" in body or "verso-optim" in body
                # Empty allocate often 400/422 once VROOM answered inside Fleetbase.
                engine_answered = "VROOM returned" in body or exc.status_code in {400, 422}  # fleetbase-first:ok
                if saas:
                    return {
                        "status": "warning",
                        "latency_ms": latency,
                        "warnings": [
                            "Fleetbase VROOM still on Verso SaaS (no local binary key). "  # fleetbase-first:ok
                            "Fix Fleetbase VROOM_ENDPOINT_MODE=binary — do not probe :8030 from PorterChain."
                        ],
                        "details": {"path": RUN_PATH, "via": "fleetbase_orchestrator", "http": exc.status_code},
                    }
                if engine_answered:
                    return {
                        "status": "healthy",
                        "latency_ms": latency,
                        "details": {
                            "path": RUN_PATH,
                            "via": "fleetbase_orchestrator",
                            "note": "Orchestrator reached VROOM; empty allocate is not a production plan",  # fleetbase-first:ok
                            "http": exc.status_code,
                        },
                    }
                return {
                    "status": "warning",
                    "latency_ms": latency,
                    "errors": [str(exc)],
                    "details": {"path": RUN_PATH, "via": "fleetbase_orchestrator", "http": exc.status_code},
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "warning",
                "errors": [str(exc)],
                "details": {"note": "VROOM is Fleetbase-owned; orchestrator run failed"},  # fleetbase-first:ok
            }
