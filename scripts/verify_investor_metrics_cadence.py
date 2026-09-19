#!/usr/bin/env python3
"""INV-G2 — monthly investor metrics tracking guard."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CADENCE = ROOT / "docs/investor/METRICS_CADENCE.md"
EXPORT_SCRIPT = ROOT / "apps/api/scripts/export_investor_snapshot.py"
SNAPSHOT_DIR = ROOT / "docs/investor/snapshots"
INVESTOR_SERVICE = ROOT / "apps/api/src/porterchain_api/admin_engine/investor_metrics_service.py"
DATA_ROOM = ROOT / "docs/investor/DATA_ROOM_INDEX.md"


def main() -> int:
    failures: list[str] = []

    for label, path in (
        ("export script", EXPORT_SCRIPT),
        ("investor service", INVESTOR_SERVICE),
    ):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")

    if not SNAPSHOT_DIR.is_dir():
        failures.append("missing docs/investor/snapshots/")

    if CADENCE.is_file():
        cadence = CADENCE.read_text(encoding="utf-8")
        for needle in ("Monthly", "export_investor_snapshot", "investor-metrics"):
            if needle not in cadence:
                failures.append(f"METRICS_CADENCE.md missing {needle!r}")

    export = EXPORT_SCRIPT.read_text(encoding="utf-8")
    if "investor_metrics" not in export or "snapshots" not in export:
        failures.append("export_investor_snapshot.py incomplete")

    if DATA_ROOM.is_file():
        room = DATA_ROOM.read_text(encoding="utf-8")
        if "METRICS_CADENCE" not in room:
            failures.append("DATA_ROOM_INDEX.md should link METRICS_CADENCE.md")

    print("Investor metrics cadence guard (INV-G2)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — monthly cadence doc + export script + snapshot directory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
