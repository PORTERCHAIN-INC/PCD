"""Jeff Dean health triad + phase_1 contract locks."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.admin_engine.e2e_validation_catalog import SYSTEM_CHAIN
from porterchain_api.admin_engine.e2e_validation_service import E2EValidationService
from porterchain_api.config import Settings
from porterchain_api.platform.health_status import normalize_check_status
from porterchain_api.schemas_health import HealthDashboardResponse, IntegrationHealthResponse


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("ok", "healthy"),
        ("healthy", "healthy"),
        ("configured", "healthy"),
        ("bridge_enabled", "healthy"),
        ("local", "healthy"),
        ("legacy_ok", "healthy"),
        ("degraded", "warning"),
        ("mock", "warning"),
        ("mock_or_unconfigured", "warning"),
        ("dev_bypass", "warning"),
        ("bridge_disabled", "warning"),
        ("unconfigured", "warning"),
        ("unavailable", "warning"),
        ("dry_run", "warning"),
        ("below_slo:90%", "warning"),
        ("error: boom", "critical"),
        ("unreachable: timeout", "critical"),
        ("unbonded:auth", "critical"),
        ("", "warning"),
        (None, "warning"),
    ],
)
def test_normalize_check_status(raw: str | None, expected: str) -> None:
    assert normalize_check_status(raw) == expected


def test_health_to_validation_jeff_dean_triad() -> None:
    svc = E2EValidationService()
    assert svc._health_to_validation("healthy") == "PASS"
    assert svc._health_to_validation("ok") == "PASS"
    assert svc._health_to_validation("pass") == "PASS"
    assert svc._health_to_validation("warning") == "WARNING"
    assert svc._health_to_validation("degraded") == "WARNING"
    assert svc._health_to_validation("mock") == "WARNING"
    assert svc._health_to_validation("critical") == "BLOCKER"
    # Unknown tokens fail-closed (Jeff Dean else → FAIL)
    assert svc._health_to_validation("mystery") == "FAIL"


def test_integration_health_emits_triad_and_validates_schema() -> None:
    from porterchain_api.admin_engine.settings_service import AdminSettingsService

    db = MagicMock()
    db.execute.return_value = None
    settings = Settings(app_env="local")
    with patch("porterchain_api.platform.health.ping_redis", return_value=True):
        with patch("porterchain_api.platform.health._routing_health", return_value="ok"):
            with patch(
                "porterchain_api.auth.clerk_registry.clerk_health_checks",
                return_value={"customer": "ok", "merchant": "ok", "admin": "ok", "driver": "ok"},
            ):
                with patch(
                    "porterchain_api.auth.clerk_registry.clerk_configuration_mode",
                    return_value="enterprise",
                ):
                    with patch(
                        "porterchain_api.auth.clerk_registry.is_clerk_configured",
                        return_value=True,
                    ):
                        health = AdminSettingsService().integration_health(db, settings)

    for key in ("api", "database", "redis", "stripe", "fleetbase"):
        assert health[key]["status"] in ("healthy", "warning", "critical")
        assert "raw" in health[key]

    IntegrationHealthResponse.model_validate(health)


def test_health_dashboard_statuses_are_triad_and_system_chain_ids() -> None:
    db = MagicMock()
    settings = Settings(app_env="local")

    fake_components = [
        {
            "id": node["id"],
            "name": node["label"],
            "category": "infrastructure",
            "status": "healthy",
            "latency_ms": None,
            "last_sync": None,
            "version": None,
            "errors": [],
            "warnings": [],
            "recovery_status": "none",
            "details": {},
        }
        for node in SYSTEM_CHAIN
        if node["id"]
        not in {
            "booking_portal",
            "customer_portal",
        }  # intentional PASS exceptions in phase_1
    ]
    # Ensure porterchain_api present (Jeff Dean SYSTEM_CHAIN id)
    if not any(c["id"] == "porterchain_api" for c in fake_components):
        fake_components.append(
            {
                "id": "porterchain_api",
                "name": "Porterchain API",
                "category": "infrastructure",
                "status": "healthy",
                "latency_ms": None,
                "last_sync": None,
                "version": "test",
                "errors": [],
                "warnings": [],
                "recovery_status": "none",
                "details": {},
            }
        )

    payload = {
        "overall": "healthy",
        "checked_at": "2026-01-01T00:00:00+00:00",
        "version": "test",
        "environment": "local",
        "cached": False,
        "summary": {"healthy": len(fake_components), "warning": 0, "critical": 0},
        "components": fake_components,
        "groups": {},
        "masterrule_compliance": {"overall": "healthy", "checks": []},
    }
    HealthDashboardResponse.model_validate(payload)

    for c in payload["components"]:
        assert c["status"] in ("healthy", "warning", "critical")

    svc = E2EValidationService()
    with patch.object(svc._diagnostics, "architecture_validation", return_value={"missing_apis": []}):
        with patch.object(svc._diagnostics, "health_dashboard", return_value=payload):
            with patch.object(svc._diagnostics, "fleetbase_sync_monitor", return_value={}):
                result = svc.phase_1_system_layer(db, settings)

    assert result["phase"] == 1
    assert result["overall"] in ("PASS", "WARNING", "FAIL", "BLOCKER")
    by_id = {c["id"]: c for c in result["connections"]}
    assert by_id["porterchain_api"]["status"] == "PASS"
    # booking/customer portals intentionally PASS without a component
    assert by_id["booking_portal"]["status"] == "PASS"
    assert by_id["customer_portal"]["status"] == "PASS"


def test_diagnostics_helpers_classify_uses_ssot() -> None:
    from porterchain_api.admin_engine.diagnostics_helpers import _classify

    assert _classify("ok") == "healthy"
    assert _classify("degraded") == "warning"
    assert _classify("error: x") == "critical"
