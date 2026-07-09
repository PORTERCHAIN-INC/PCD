"""Enterprise System Validation & Diagnostics — composes existing health probes and services."""

from __future__ import annotations

from porterchain_api.admin_engine.diagnostics_catalog import TEST_CATALOG, TEST_IDS
from porterchain_api.admin_engine.diagnostics_chaos import DiagnosticsChaosMixin
from porterchain_api.admin_engine.diagnostics_health import DiagnosticsHealthMixin
from porterchain_api.admin_engine.diagnostics_helpers import (
    EVENT_CONSUMERS,
    EVENT_PUBLISHERS,
    HealthClass,
    _classify,
    _component,
    _now_iso,
    _openapi_paths,
    _portal_component,
    _probe_http,
    _run_probe_batch,
    _test_result,
)
from porterchain_api.admin_engine.diagnostics_probes import DiagnosticsProbesMixin
from porterchain_api.admin_engine.diagnostics_reports import DiagnosticsReportsMixin
from porterchain_api.admin_engine.diagnostics_timeline import ControlTowerTimeline
from porterchain_api.admin_engine.diagnostics_validation import DiagnosticsValidationMixin
from porterchain_api.admin_engine.diagnostics_workflows import DiagnosticsWorkflowsMixin
from porterchain_api.admin_engine.settings_service import AdminSettingsService


class AdminDiagnosticsService(
    DiagnosticsHealthMixin,
    DiagnosticsValidationMixin,
    DiagnosticsWorkflowsMixin,
    DiagnosticsChaosMixin,
    DiagnosticsProbesMixin,
    DiagnosticsReportsMixin,
):
    """Validation & diagnostics — reuses settings health, fleetbase sync, event bus, and probes."""

    def __init__(self) -> None:
        self._settings_svc = AdminSettingsService()


__all__ = [
    "AdminDiagnosticsService",
    "ControlTowerTimeline",
    "EVENT_CONSUMERS",
    "EVENT_PUBLISHERS",
    "HealthClass",
    "TEST_CATALOG",
    "TEST_IDS",
    "_classify",
    "_component",
    "_now_iso",
    "_openapi_paths",
    "_portal_component",
    "_probe_http",
    "_run_probe_batch",
    "_test_result",
]
