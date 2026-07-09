#!/usr/bin/env python3
"""§9.1.1–9.1.4 — Category name and narrative consistency."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CATEGORY = ROOT / "docs/CATEGORY.md"
COMPETITIVE = ROOT / "docs/COMPETITIVE_MEMO.md"
ICP = ROOT / "docs/ICP.md"
MASTERRULE = ROOT / "masterrule.md"
CORPORATE_EN = ROOT / "website/messages/corporate-en.json"

CATEGORY_NEEDLES = ("B2B last-mile orchestration", "orchestration")
ANTI_NEEDLES = ("cheapest courier", "gig marketplace", "uber for packages")


def main() -> int:
    failures: list[str] = []

    for path in (CATEGORY, COMPETITIVE, ICP, MASTERRULE):
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")

    if CATEGORY.is_file():
        cat = CATEGORY.read_text(encoding="utf-8")
        for needle in CATEGORY_NEEDLES:
            if needle.lower() not in cat.lower():
                failures.append(f"CATEGORY.md missing {needle!r}")

    combined = ""
    for path in (MASTERRULE, ICP, CATEGORY, CORPORATE_EN):
        if path.is_file():
            combined += path.read_text(encoding="utf-8").lower()

    if not any(n in combined for n in ("orchestration", "operating system")):
        failures.append("narrative missing orchestration / OS positioning (§9.1.2)")

    if CORPORATE_EN.is_file():
        hero = json.loads(CORPORATE_EN.read_text(encoding="utf-8")).get("home", {}).get("hero", {})
        subtitle = str(hero.get("subtitle", "")).lower()
        if "courier" in subtitle and "not" not in subtitle:
            failures.append("homepage hero subtitle uses courier framing (§9.1.3)")

    for anti in ANTI_NEEDLES:
        idx = combined.find(anti)
        while idx != -1:
            window = combined[max(0, idx - 24) : idx]
            if "not " not in window and "no " not in window and "never " not in window:
                failures.append(f"anti-positioning phrase found: {anti!r}")
                break
            idx = combined.find(anti, idx + 1)

    if COMPETITIVE.is_file():
        comp = COMPETITIVE.read_text(encoding="utf-8")
        for threat in ("Uber", "Amazon", "Onfleet", "Fleetbase"):
            if threat not in comp:
                failures.append(f"COMPETITIVE_MEMO.md missing {threat} section")

    print("Category positioning guard (§9.1.1–9.1.4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: owned category + consistent orchestration narrative")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
