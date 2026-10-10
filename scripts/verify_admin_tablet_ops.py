#!/usr/bin/env python3
"""Admin ops tablet responsiveness guard (§6.3.4)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Dispatch owns the ops surface. Routes only mount DispatchShell; the speed
# metrics grid and the horizontally scrollable section tabs live in the shell.
REQUIRED = (
    (ROOT / "apps/admin/src/app/globals.css", ("ops-table-scroll", "ops-touch-target", "768px")),
    (ROOT / "apps/admin/src/components/AdminShell.tsx", ("ops-main",)),
    (ROOT / "apps/admin/src/components/dispatch/MetricsBar.tsx", ("grid-cols-2", "lg:grid-cols-6")),
    (
        ROOT / "apps/admin/src/components/dispatch/DispatchShell.tsx",
        ("overflow-x-auto", "MetricsBar", "min-h-11"),
    ),
    (ROOT / "apps/admin/src/app/(ops)/dispatch/[view]/page.tsx", ("DispatchShell",)),
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
    print("  PASS: ops tablet scroll, touch targets, dispatch layout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
