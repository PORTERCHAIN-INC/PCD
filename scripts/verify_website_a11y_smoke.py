#!/usr/bin/env python3
"""Accessibility smoke checks — main landmark and custom 404."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "website/src/components/layout/SiteShell.tsx"
NOT_FOUND = ROOT / "website/src/app/[locale]/not-found.tsx"


def main() -> int:
    failures: list[str] = []

    if not SHELL.exists():
        failures.append("SiteShell.tsx missing")
    else:
        shell = SHELL.read_text(encoding="utf-8")
        if 'id="main-content"' not in shell and "id='main-content'" not in shell:
            failures.append("SiteShell: main landmark id=main-content required")

    if not NOT_FOUND.exists():
        failures.append("[locale]/not-found.tsx missing — custom 404 required")

    print("Website a11y smoke guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: main landmark, custom 404 present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
