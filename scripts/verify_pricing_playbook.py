#!/usr/bin/env python3
"""Pricing page copy guard — playbook §4.4 hero, metadata, tier names."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPORATE_EN = ROOT / "website/messages/corporate-en.json"
CORPORATE_FR = ROOT / "website/messages/corporate-fr.json"

EN_META_TITLE = "B2B Delivery Pricing GTA | Quote-Based Capacity | PorterChain"
EN_META_DESC = (
    "Transparent quote-based pricing for GTA B2B delivery — same-day, urgent, recurring, "
    "and fleet overflow. Vehicle class, route, and proof requirements. Request a written quote."
)
EN_HERO_TITLE = "How delivery pricing works"
EN_HERO_SUBTITLE_MARKERS = ("transportation capacity executed", "not software seats")
EN_TIER_NAMES = ("Pay as you go", "Business account", "Dedicated program")
FACTOR_KEYS = ("label", "title", "subtitle", "colVehicle", "colSameDay", "colScheduled")


def _tier_names(data: dict) -> list[str]:
    items = data.get("pricing", {}).get("tiers", {}).get("items", {})
    return [items.get(str(i), {}).get("name", "") for i in range(3)]


def _check(locale: str, path: Path) -> list[str]:
    failures: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))

    meta = data.get("metadata", {}).get("pricing", {})
    hero = data.get("pricing", {}).get("hero", {})
    tiers_title = data.get("pricing", {}).get("tiers", {}).get("title", "")
    names = _tier_names(data)
    factors = data.get("pricing", {}).get("factors", {})

    for key in FACTOR_KEYS:
        if not factors.get(key):
            failures.append(f"{locale} pricing.factors.{key} missing")
    for i in range(3):
        row = factors.get("rows", {}).get(str(i), {})
        for field in ("vehicle", "sameDay", "scheduled"):
            if not row.get(field):
                failures.append(f"{locale} pricing.factors.rows.{i}.{field} missing")

    if locale == "en":
        if meta.get("title") != EN_META_TITLE:
            failures.append(
                f"{locale} metadata.pricing.title expected {EN_META_TITLE!r}, got {meta.get('title')!r}"
            )
        if meta.get("description") != EN_META_DESC:
            failures.append(f"{locale} metadata.pricing.description drift from playbook §4.4")
        if hero.get("title") != EN_HERO_TITLE:
            failures.append(
                f"{locale} pricing.hero.title expected {EN_HERO_TITLE!r}, got {hero.get('title')!r}"
            )
        subtitle = (hero.get("subtitle") or "").lower()
        for marker in EN_HERO_SUBTITLE_MARKERS:
            if marker not in subtitle:
                failures.append(f"{locale} pricing.hero.subtitle must mention {marker!r}")
        for expected, got in zip(EN_TIER_NAMES, names, strict=True):
            if got != expected:
                failures.append(f"{locale} pricing tier name expected {expected!r}, got {got!r}")
        if "Pay as you go" not in tiers_title:
            failures.append(f"{locale} pricing.tiers.title must list playbook tier names")
    else:
        title = meta.get("title") or ""
        if "tarification livraison b2b" not in title.lower():
            failures.append(f"{locale} metadata.pricing.title must be B2B pricing framing")
        hero_title = hero.get("title") or ""
        if "tarification" not in hero_title.lower():
            failures.append(f"{locale} pricing.hero.title must explain how pricing works")
        subtitle = (hero.get("subtitle") or "").lower()
        if "capacité" not in subtitle or "logiciel" not in subtitle:
            failures.append(f"{locale} pricing.hero.subtitle must contrast capacity vs software")
        fr_tiers = ("à l'usage", "compte entreprise", "programme dédié")
        for marker, got in zip(fr_tiers, [n.lower() for n in names], strict=True):
            if marker not in got:
                failures.append(f"{locale} pricing tier expected {marker!r}, got {got!r}")

    if hero.get("primaryCta") not in ("Get a quote", "Obtenir un devis"):
        failures.append(f"{locale} pricing.hero.primaryCta must be Get a quote")

    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_check("en", CORPORATE_EN))
    failures.extend(_check("fr", CORPORATE_FR))

    print("Pricing playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: /pricing hero, metadata, and tiers match playbook §4.4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
