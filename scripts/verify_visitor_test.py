#!/usr/bin/env python3
"""PV-G1 — 10-second visitor test: homepage communicates what + for whom."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CORPORATE_EN = ROOT / "website/messages/corporate-en.json"
CORPORATE_FR = ROOT / "website/messages/corporate-fr.json"
PLATFORM_PAGE = ROOT / "website/src/app/[locale]/platform/page.tsx"
ICP = ROOT / "docs/ICP.md"

WHAT_NEEDLES = (
    "operating system",
    "orchestration",
    "logistics",
    "système d'exploitation",
    "logistique",
    "orchestration",
)
WHOM_NEEDLES = ("business", "merchant", "operations", "entreprise", "équipes", "entreprises")


def _hero_text(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    hero = data.get("home", {}).get("hero", {})
    title = str(hero.get("title", "")).lower()
    subtitle = str(hero.get("subtitle", "")).lower()
    return title, subtitle


def main() -> int:
    failures: list[str] = []

    if not PLATFORM_PAGE.is_file():
        failures.append("missing /platform page")
    if not ICP.is_file():
        failures.append("missing docs/ICP.md")

    for label, path in (("corporate-en", CORPORATE_EN), ("corporate-fr", CORPORATE_FR)):
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")
            continue
        title, subtitle = _hero_text(path)
        combined = f"{title} {subtitle}"
        if not any(needle in combined for needle in WHAT_NEEDLES):
            failures.append(f"{label} hero missing clear WHAT (platform/orchestration)")
        if not any(needle in combined for needle in WHOM_NEEDLES):
            failures.append(f"{label} hero missing clear FOR WHOM (business/operations)")

    if PLATFORM_PAGE.is_file():
        platform_text = PLATFORM_PAGE.read_text(encoding="utf-8").lower()
        if "corporate.platform" not in platform_text and "platform" not in platform_text:
            failures.append("platform page missing platform copy hook")

    print("Visitor test guard (PV-G1)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: homepage hero states what (orchestration OS) + for whom (business ops)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
