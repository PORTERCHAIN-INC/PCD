#!/usr/bin/env python3
"""Charter + architecture identity — Transportation Capacity Network."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str, str], ...] = (
    ("charter", "docs/PORTERCHAIN_CHARTER.md", "Transportation Capacity Network"),
    ("architecture", "ARCHITECTURE.md", "Transportation Capacity Network"),
    ("charter-gate", "ARCHITECTURE.md", "10-customer"),
)


def main() -> int:
    failures: list[str] = []
    for item_id, rel, needle in CHECKS:
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"{item_id} missing {rel}")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            failures.append(f"{item_id} {rel} missing {needle!r}")

    print("Product vision baseline guard (charter + ARCHITECTURE.md)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: living identity docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
