#!/usr/bin/env python3
"""Business page copy guard — playbook §4.2 hero + services grid keys."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUSINESS_EN = ROOT / "website/messages/business-en.json"
EXPECTED_H1_LINE1 = "Vehicle and driver capacity"
EXPECTED_H1_LINE2 = "for every delivery scenario."
EXPECTED_SOLUTION_KEYS = (
    "recurringDelivery",
    "dedicatedRoutes",
    "sameDay",
    "multiStop",
    "wholesale",
    "ltlFreight",
    "urgentEmergency",
    "quickExpress",
    "construction",
    "medical",
    "fleetOverflow",
    "lastMile",
)


def main() -> int:
    failures: list[str] = []
    data = json.loads(BUSINESS_EN.read_text(encoding="utf-8"))

    hero = data.get("hero", {})
    if hero.get("titleLine1") != EXPECTED_H1_LINE1:
        failures.append(
            f"hero.titleLine1 expected {EXPECTED_H1_LINE1!r}, got {hero.get('titleLine1')!r}"
        )
    if hero.get("titleLine2") != EXPECTED_H1_LINE2:
        failures.append(
            f"hero.titleLine2 expected {EXPECTED_H1_LINE2!r}, got {hero.get('titleLine2')!r}"
        )

    items = data.get("solutions", {}).get("items", {})
    for key in EXPECTED_SOLUTION_KEYS:
        if key not in items:
            failures.append(f"solutions.items missing playbook key: {key}")
        desc = data.get("solutions", {}).get("descriptions", {}).get(key)
        if not desc:
            failures.append(f"solutions.descriptions missing copy for: {key}")

    faq = data.get("faq", {}).get("items", {})
    for key in ("sameDay", "overflow", "intraCity", "lastMile", "gta", "vehicles", "pod", "pricing"):
        if key not in faq:
            failures.append(f"faq.items missing playbook question key: {key}")

    _PLAYBOOK_FAQ_PHRASES: dict[str, tuple[str, ...]] = {
        "sameDay": ("same-day", "cut-off"),
        "overflow": ("emergency", "fleet overflow"),
        "intraCity": ("intra-city", "GTA"),
        "pod": ("proof",),
        "pricing": ("Quote-based", "platform fees"),
    }
    for key, phrases in _PLAYBOOK_FAQ_PHRASES.items():
        item = faq.get(key, {})
        blob = f"{item.get('question', '')} {item.get('answer', '')}"
        for phrase in phrases:
            if phrase not in blob:
                failures.append(f"faq.items.{key} missing playbook phrase: {phrase!r}")

    print("Business playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: /business hero and services grid match playbook §4.2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
