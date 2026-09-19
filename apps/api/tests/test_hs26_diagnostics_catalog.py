"""HS-26 — diagnostics catalog honesty: VROOM never probed as a PC HTTP port."""

from __future__ import annotations

import inspect
from pathlib import Path

from porterchain_api.admin_engine.diagnostics_catalog import TEST_CATALOG, TEST_IDS
from porterchain_api.admin_engine.diagnostics_fleetbase_probes import DiagnosticsFleetbaseProbesMixin
from porterchain_api.admin_engine.diagnostics_service import AdminDiagnosticsService
from porterchain_api.config import Settings


def test_hs26_catalog_covers_expected_ids() -> None:
    assert "vroom" in TEST_IDS
    assert len(TEST_CATALOG) == len(TEST_IDS)
    assert all(t["id"] for t in TEST_CATALOG)


def test_hs26_probe_vroom_never_hits_pc_http_port() -> None:
    src = inspect.getsource(DiagnosticsFleetbaseProbesMixin._probe_vroom)
    assert "127.0.0.1:8030" not in src
    assert "8030/health" not in src
    assert "httpx" not in src
    assert "fleetbase_orchestrator" in src or "RUN_PATH" in src


def test_hs26_probe_vroom_source_file_has_no_direct_sidecar() -> None:
    path = Path(inspect.getfile(DiagnosticsFleetbaseProbesMixin))
    text = path.read_text(encoding="utf-8")
    # Only the method body matters; keep the module free of PC→:8030 probes.
    assert "http://127.0.0.1:8030" not in text


def test_hs26_vroom_skipped_logs_are_honest(db, settings: Settings) -> None:
    settings = settings.model_copy(update={"fleetbase_dispatch_bridge": False})
    result = AdminDiagnosticsService().run_test("vroom", db, settings)
    assert result["status"] == "healthy"
    assert result["details"].get("skipped") is True
    assert any("skip" in (log or "").lower() or "bridge" in (log or "").lower() for log in result["logs"])
    assert not any("listed by Fleetbase" in (log or "") for log in result["logs"])
