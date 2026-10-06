"""Dispatch / day-plan health probes (retired Fleetbase console probes)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from porterchain_api.config import Settings

_SEQUENCER = (
    Path(__file__).resolve().parents[1] / "dispatch_engine" / "sequencer.py"
)


class DiagnosticsFleetbaseProbesMixin:
    """Mixin name kept for import stability; probes are PorterChain day-plan only."""

    def _probe_day_plan(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        del settings, live
        if not _SEQUENCER.is_file():
            return {
                "status": "critical",
                "details": {"ok": False, "note": "dispatch_engine/sequencer.py missing"},
            }
        text = _SEQUENCER.read_text(encoding="utf-8", errors="ignore")
        ok = "ortools" in text or "pywrapcp" in text
        return {
            "status": "healthy" if ok else "critical",
            "details": {
                "ok": ok,
                "engine": "porterchain",
                "solver": "ortools" if ok else "missing",
                "note": "Day plan is OR-Tools. Valhalla is the road cost.",
            },
        }

    def _probe_fleetbase_console(self, settings: Settings) -> dict[str, Any]:
        """Retired console — report day plan instead."""
        return self._probe_day_plan(settings)

    def _probe_fleetbase_adapter(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        return self._probe_day_plan(settings, live=live)

    def _probe_fleetbase(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        return self._probe_day_plan(settings, live=live)

    def _probe_vroom(self, settings: Settings, *, live: bool = False) -> dict[str, Any]:
        """No VROOM client — same day-plan check."""
        return self._probe_day_plan(settings, live=live)
