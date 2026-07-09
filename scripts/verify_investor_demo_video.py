#!/usr/bin/env python3
"""§10.2.2 — 3-minute investor demo recording guide."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DOC = ROOT / "docs/investor/DEMO_VIDEO.md"
DATA_ROOM = ROOT / "docs/investor/DATA_ROOM_INDEX.md"

REQUIRED_BEATS = ("homepage", "track", "merchant", "admin", "developers")


def main() -> int:
    failures: list[str] = []

    if not DOC.is_file():
        failures.append("missing docs/investor/DEMO_VIDEO.md")
    else:
        text = DOC.read_text(encoding="utf-8")
        low = text.lower()
        if "3" not in text or "minute" not in low:
            failures.append("DEMO_VIDEO.md must state 3-minute duration")
        for beat in REQUIRED_BEATS:
            if beat not in low:
                failures.append(f"DEMO_VIDEO.md missing beat: {beat}")
        if "shot list" not in low:
            failures.append("DEMO_VIDEO.md missing shot list section")

    if DATA_ROOM.is_file():
        room = DATA_ROOM.read_text(encoding="utf-8")
        if "DEMO_VIDEO" not in room and "demo video" not in room.lower():
            failures.append("DATA_ROOM_INDEX.md should reference demo video guide")
    else:
        failures.append("missing docs/investor/DATA_ROOM_INDEX.md")

    print("Investor demo video guard (§10.2.2)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — 3-min recording guide present (manual MP4 upload still required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
