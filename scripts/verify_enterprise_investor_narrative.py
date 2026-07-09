#!/usr/bin/env python3
"""ENT-G1 + INV-G4 — enterprise SIG Lite and investor TAM docs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SIG = ROOT / "docs/compliance/SIG_LITE.md"
TAM = ROOT / "docs/investor/TAM_VERTICAL_EXPANSION.md"
DATA_ROOM = ROOT / "docs/investor/DATA_ROOM_INDEX.md"


def main() -> int:
    failures: list[str] = []

    for label, path in (("SIG_LITE", SIG), ("TAM doc", TAM)):
        if not path.is_file():
            failures.append(f"missing {label}: {path.relative_to(ROOT)}")
        else:
            text = path.read_text(encoding="utf-8")
            if label == "SIG_LITE":
                if "20%" not in text or "Roadmap" not in text:
                    failures.append("SIG_LITE.md missing roadmap percentage attestation")
                if "RBAC_MATRIX" not in text:
                    failures.append("SIG_LITE.md missing RBAC evidence")
            else:
                for needle in ("vertical", "TAM", "orchestration"):
                    if needle not in text:
                        failures.append(f"TAM doc missing {needle!r}")

    if DATA_ROOM.is_file():
        room = DATA_ROOM.read_text(encoding="utf-8")
        if "TAM_VERTICAL" not in room and "TAM" not in room:
            failures.append("DATA_ROOM_INDEX should link TAM_VERTICAL_EXPANSION.md")
    else:
        failures.append("missing DATA_ROOM_INDEX.md")

    print("Enterprise + investor narrative guard (ENT-G1 · INV-G4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  OK — SIG Lite questionnaire + TAM vertical expansion doc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
