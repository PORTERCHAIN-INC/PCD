"""Retired Fleetbase sync SLO — stubs only after peaceful removal."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.platform.retired_sync import (
    SLO_TARGET_PCT,
    assess_fleetbase_sync,
    build_fleetbase_sync_alerts,
)


def _bridge_settings(*, enabled: bool = True) -> Settings:
    suffix = uuid4().hex[:8]
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt",
        fleetbase_dispatch_bridge=enabled,
        fleetbase_api_key=f"key-{suffix}" if enabled else "",
        fleetbase_webhook_secret=f"secret-{suffix}" if enabled else "",
        fleetbase_default_company_uuid=f"company-{suffix}" if enabled else "",
    )


def test_assess_fleetbase_sync_always_removed(db: Session) -> None:
    for enabled in (True, False):
        result = assess_fleetbase_sync(db, _bridge_settings(enabled=enabled))
        assert result["status"] == "removed"
        assert result["ok"] is True
        assert result["bridge_enabled"] is False
        assert result.get("meets_slo", True) is True


def test_slo_threshold_retired() -> None:
    assert SLO_TARGET_PCT == 0


def test_build_fleetbase_sync_alerts_empty() -> None:
    slo = {
        "bridge_enabled": True,
        "meets_slo": False,
        "link_pct": 90.0,
        "slo_target_pct": 98.0,
        "linked_orders": 9,
        "eligible_orders": 10,
        "dead_letters": 2,
        "pending_jobs": 0,
    }
    assert build_fleetbase_sync_alerts(slo) == []
