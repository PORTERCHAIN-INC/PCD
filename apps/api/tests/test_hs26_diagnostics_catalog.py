"""HS-26 — diagnostics catalog honesty: day plan is OR-Tools, not a VROOM HTTP port."""

from __future__ import annotations

import inspect
from pathlib import Path

from porterchain_api.admin_engine.diagnostics_catalog import TEST_CATALOG, TEST_IDS
from porterchain_api.admin_engine.diagnostics_dispatch_probes import (
    DiagnosticsDispatchProbesMixin,
)
from porterchain_api.admin_engine.diagnostics_service import AdminDiagnosticsService
from porterchain_api.config import Settings


def test_hs26_catalog_covers_expected_ids() -> None:
    assert "dispatch" in TEST_IDS
    assert "vroom" not in TEST_IDS
    assert "fleetbase" not in TEST_IDS
    assert len(TEST_CATALOG) == len(TEST_IDS)
    assert all(t["id"] for t in TEST_CATALOG)


def test_hs26_probe_day_plan_never_hits_vroom_http_port() -> None:
    src = inspect.getsource(DiagnosticsDispatchProbesMixin._probe_day_plan)
    assert "127.0.0.1:8030" not in src
    assert "8030/health" not in src
    assert "httpx" not in src
    assert "OR-Tools" in src or "ortools" in src


def test_hs26_probe_source_file_has_no_direct_sidecar() -> None:
    path = Path(inspect.getfile(DiagnosticsDispatchProbesMixin))
    text = path.read_text(encoding="utf-8")
    assert "http://127.0.0.1:8030" not in text


def test_hs26_dispatch_probe_reports_ortools(db, settings: Settings) -> None:
    result = AdminDiagnosticsService().run_test("dispatch", db, settings)
    assert result["status"] == "healthy"
    assert result["details"].get("engine") == "porterchain"
    assert result["details"].get("solver") == "ortools"
