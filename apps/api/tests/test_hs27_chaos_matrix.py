"""HS-27 — chaos matrix: degrade-closed, no stack dumps, offline ≠ live probe fail."""

from __future__ import annotations

import json

from porterchain_api.admin_engine.diagnostics_chaos import (
    CANONICAL_CHAOS_SCENARIOS,
    resolve_chaos_scenario,
)
from porterchain_api.admin_engine.diagnostics_service import AdminDiagnosticsService
from porterchain_api.config import Settings


def test_hs27_admin_chaos_list_matches_api() -> None:
    from pathlib import Path
    import re

    admin = Path(__file__).resolve().parents[2] / "admin/src/lib/diagnostics.ts"
    text = admin.read_text(encoding="utf-8")
    match = re.search(r"CHAOS_SCENARIOS = \[([\s\S]*?)\] as const", text)
    assert match
    admin_ids = re.findall(r'"([^"]+)"', match.group(1))
    assert tuple(admin_ids) == CANONICAL_CHAOS_SCENARIOS


def test_hs27_chaos_matrix_degrade_closed(db, settings: Settings) -> None:
    svc = AdminDiagnosticsService()
    for scenario in CANONICAL_CHAOS_SCENARIOS:
        result = svc.chaos_test(scenario, db, settings)
        blob = json.dumps(result, default=str)
        assert "Traceback" not in blob
        assert 'File "' not in blob
        assert result["status"] in {"healthy", "warning", "critical"}
        assert result["scenario"] == scenario
        assert resolve_chaos_scenario(scenario) == result.get("canonical_scenario", scenario)


def test_hs27_stripe_offline_not_live_probe(db, settings: Settings) -> None:
    """stripe_offline must pass when webhook+keys wired even if Stripe API is down."""
    settings = settings.model_copy(
        update={"stripe_mock": True, "stripe_webhook_secret": "whsec_test_hs27", "stripe_secret": ""}
    )
    result = AdminDiagnosticsService().chaos_test("stripe_offline", db, settings)
    assert result["status"] == "healthy"
    assert any("idempotency" in (log or "").lower() for log in result["logs"])


def test_hs27_ui_uses_status_tone_not_json_dump() -> None:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "admin/src/components/diagnostics/DiagnosticsTestCenter.tsx"
    text = path.read_text(encoding="utf-8")
    # Chaos panel must render statusTone — not a raw JSON dump of the payload.
    assert "statusTone" in text
    assert "JSON.stringify(chaosResult" not in text
