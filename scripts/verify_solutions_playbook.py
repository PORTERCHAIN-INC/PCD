#!/usr/bin/env python3
"""Solutions hub copy guard — playbook §4.3 hero, metadata, pricing FAQ."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPORATE_EN = ROOT / "website/messages/corporate-en.json"
CORPORATE_FR = ROOT / "website/messages/corporate-fr.json"

EN_META_TITLE = "B2B Delivery Solutions GTA | Construction, Wholesale, Medical | Porterchain"
EN_HERO_TITLE = "Transportation capacity for GTA businesses"
EN_PRICING_FAQ_MARKERS = ("quote-based", "platform fees")


def _check(locale: str, path: Path) -> list[str]:
    failures: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))

    meta = data.get("metadata", {}).get("solutions", {})
    hero = data.get("solutions", {}).get("hero", {})
    faq_pricing = data.get("solutions", {}).get("faq", {}).get("items", {}).get("3", {})

    if locale == "en":
        if meta.get("title") != EN_META_TITLE:
            failures.append(
                f"{locale} metadata.solutions.title expected {EN_META_TITLE!r}, got {meta.get('title')!r}"
            )
        if hero.get("title") != EN_HERO_TITLE:
            failures.append(
                f"{locale} solutions.hero.title expected {EN_HERO_TITLE!r}, got {hero.get('title')!r}"
            )
        answer = (faq_pricing.get("a") or "").lower()
        for marker in EN_PRICING_FAQ_MARKERS:
            if marker not in answer:
                failures.append(f"{locale} solutions.faq.items.3.a must mention {marker!r}")
    else:
        title = meta.get("title") or ""
        if "solutions livraison b2b" not in title.lower():
            failures.append(f"{locale} metadata.solutions.title must be B2B solutions framing")
        hero_title = hero.get("title") or ""
        if "capacité" not in hero_title.lower() or "rgt" not in hero_title.lower():
            failures.append(f"{locale} solutions.hero.title must lead with GTA capacity framing")
        answer = (faq_pricing.get("a") or "").lower()
        if "devis" not in answer:
            failures.append(f"{locale} solutions.faq.items.3.a must mention quote-based (devis)")
        if "plateforme" not in answer and "licence" not in answer:
            failures.append(f"{locale} solutions.faq.items.3.a must deny platform/software fees")

    if hero.get("primaryCta") not in ("Get a quote", "Obtenir un devis"):
        failures.append(f"{locale} solutions.hero.primaryCta must be Get a quote")

    return failures


def main() -> int:
    failures: list[str] = []
    failures.extend(_check("en", CORPORATE_EN))
    failures.extend(_check("fr", CORPORATE_FR))

    print("Solutions playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: /solutions hero, metadata, and pricing FAQ match playbook §4.3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
