"""The day solver is OR-Tools. A VROOM sidecar is not the Optimize path."""

from __future__ import annotations

from pathlib import Path


def test_day_solver_is_ortools_in_dispatch_engine() -> None:
    root = Path(__file__).resolve().parents[3]
    sequencer = root / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"
    text = sequencer.read_text()
    assert "ortools" in text
    assert "PATH_CHEAPEST_ARC" in text
    assert "8030" not in text
