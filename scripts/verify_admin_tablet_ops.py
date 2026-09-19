#!/usr/bin/env python3
"""Admin ops tablet responsiveness guard (§6.3.4)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    (ROOT / "apps/admin/src/app/globals.css", ("ops-table-scroll", "ops-touch-target", "768px")),
    (ROOT / "apps/admin/src/components/AdminShell.tsx", ("ops-main",)),
    (ROOT / "apps/admin/src/components/operations/KpiStrip.tsx", ("ops-stat-grid",)),
    (ROOT / "apps/admin/src/app/(ops)/operations/page.tsx", ("ops-table-scroll", "KpiStrip")),
)


def main() -> int:
    failures: list[str] = []
    for path, needles in REQUIRED:
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                failures.append(f"{path.relative_to(ROOT)} missing {needle!r}")

    print("Admin tablet ops (§6.3.4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: ops tablet scroll, touch targets, control tower layout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
