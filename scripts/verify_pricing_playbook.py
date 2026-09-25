#!/usr/bin/env python3
"""Pricing copy guard — playbook §4.4 lives on /business#pricing (merchants billing)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUSINESS_EN = ROOT / "website/messages/business-en.json"
BUSINESS_FR = ROOT / "website/messages/business-fr.json"
BILLING_SECTION = ROOT / "website/src/components/marketing/business/sections/BillingOptions.tsx"

EN_TITLE = "How capacity pricing works"
EN_SUBTITLE_MARKERS = ("transportation capacity executed", "not software seats")
EN_TIER_NAMES = ("Pay as you go", "Business account", "Dedicated program")
EN_FACTOR_KEYS = ("vehicle", "route", "proof")


def _check(locale: str, path: Path) -> list[str]:
    failures: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    billing = data.get("billing", {})
    plans = billing.get("plans", {})
    factors = billing.get("factors", {})

    for key in EN_FACTOR_KEYS:
        block = factors.get(key, {})
        if not block.get("title") or not block.get("body"):
            failures.append(f"{locale} billing.factors.{key} missing title/body")

    names = [
        plans.get("payAsYouGo", {}).get("name", ""),
        plans.get("creditAccount", {}).get("name", ""),
        plans.get("enterprise", {}).get("name", ""),
    ]

    if locale == "en":
        if billing.get("title") != EN_TITLE:
            failures.append(
                f"{locale} billing.title expected {EN_TITLE!r}, got {billing.get('title')!r}"
            )
        subtitle = (billing.get("subtitle") or "").lower()
        for marker in EN_SUBTITLE_MARKERS:
            if marker not in subtitle:
                failures.append(f"{locale} billing.subtitle must mention {marker!r}")
        for expected, got in zip(EN_TIER_NAMES, names, strict=True):
            if got != expected:
                failures.append(f"{locale} billing plan name expected {expected!r}, got {got!r}")
        for key in ("payAsYouGo", "creditAccount", "enterprise"):
            if not plans.get(key, {}).get("price"):
                failures.append(f"{locale} billing.plans.{key}.price missing")
        if not billing.get("footnote"):
            failures.append(f"{locale} billing.footnote missing")
    else:
        title = (billing.get("title") or "").lower()
        if "tarification" not in title:
            failures.append(f"{locale} billing.title must explain how pricing works")
        subtitle = (billing.get("subtitle") or "").lower()
        if "capacité" not in subtitle or "logiciel" not in subtitle:
            failures.append(f"{locale} billing.subtitle must contrast capacity vs software")
        fr_tiers = ("à l'utilisation", "compte d'affaires", "programme dédié")
        for marker, got in zip(fr_tiers, [n.lower() for n in names], strict=True):
            if marker not in got:
                failures.append(f"{locale} billing plan expected {marker!r}, got {got!r}")

    if billing.get("cta") not in ("Get a quote", "Obtenir un devis"):
        failures.append(f"{locale} billing.cta must be Get a quote")

    return failures


def main() -> int:
    failures: list[str] = []
    if not BILLING_SECTION.is_file():
        failures.append("missing BillingOptions.tsx (merchants #pricing section)")
    else:
        text = BILLING_SECTION.read_text(encoding="utf-8")
        if 'id="pricing"' not in text:
            failures.append("BillingOptions must expose id=pricing for /business#pricing")
        if "factors" not in text:
            failures.append("BillingOptions must render quote factor strip")

    failures.extend(_check("en", BUSINESS_EN))
    failures.extend(_check("fr", BUSINESS_FR))

    print("Pricing playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: /business#pricing billing copy matches playbook §4.4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
