#!/usr/bin/env python3
"""Homepage copy guard — playbook §4.1 hero + trust line."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPORATE_EN = ROOT / "website/messages/corporate-en.json"
CORPORATE_FR = ROOT / "website/messages/corporate-fr.json"

EXPECTED = {
    "title": "When your fleet can't cover it,",
    "titleHighlight": "PorterChain can.",
    "primaryCta": "Get a quote",
    "secondaryCta": "See vehicles",
    "trustLine": "Response within one business day · Quote-based, no platform fees",
}


def _check(locale: str, path: Path, hero_key: str, primary_fr: str, trust_fr: str) -> list[str]:
    failures: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    hero = data.get("home", {}).get("hero", {})

    if locale == "en":
        for key, expected in EXPECTED.items():
            if hero.get(key) != expected:
                failures.append(f"{locale} home.hero.{key} expected {expected!r}, got {hero.get(key)!r}")
    else:
        if hero.get("primaryCta") != primary_fr:
            failures.append(f"{locale} home.hero.primaryCta expected {primary_fr!r}")
        if "devis" not in (hero.get("trustLine") or "").lower() and "quote" not in (
            hero.get("trustLine") or ""
        ).lower():
            failures.append(f"{locale} home.hero.trustLine must mention quote-based pricing")
        if hero.get("trustLine") != trust_fr:
            failures.append(f"{locale} home.hero.trustLine expected {trust_fr!r}")

    for dead in ("bookDeliveryCta", "trackCta"):
        if dead in hero:
            failures.append(f"{locale} home.hero still has deprecated key: {dead}")

    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_check("en", CORPORATE_EN, "en", "Obtenir un devis", ""))
    failures.extend(
        _check(
            "fr",
            CORPORATE_FR,
            "fr",
            "Obtenir un devis",
            "Réponse en un jour ouvrable · Sur devis, sans frais plateforme",
        )
    )

    print("Home playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: homepage hero matches playbook §4.1 (price trust line + quote CTA)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
