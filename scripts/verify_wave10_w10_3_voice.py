#!/usr/bin/env python3
"""Wave 10 w10-3 guard — conversational voice longtail FAQ on intent hubs."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAQ = ROOT / "website/src/lib/seo/content/faq-clusters.ts"
FR = ROOT / "website/messages/seo-programmatic-fr.json"

VOICE_PHRASES_EN = (
    "right now near me",
    "50kg pallet",
)


def main() -> int:
    failures: list[str] = []
    faq = FAQ.read_text(encoding="utf-8")

    for phrase in VOICE_PHRASES_EN:
        if phrase not in faq:
            failures.append(f"faq-clusters.ts missing conversational phrase: {phrase}")

    fr = json.loads(FR.read_text(encoding="utf-8"))
    for slug, phrase in (
        ("same-day-retail-distribution", "tout de suite près de moi"),
        ("fleet-overflow-wholesale-delivery", "50 kg"),
    ):
        cluster = fr.get("faq", {}).get(slug, {})
        items = cluster.get("items", [])
        if not items:
            failures.append(f"seo-programmatic-fr.json missing FAQ items: {slug}")
            continue
        first_q = items[0].get("question", "").lower()
        if "?" not in first_q:
            failures.append(f"{slug} FR first FAQ should be conversational question")
        if phrase not in json.dumps(cluster, ensure_ascii=False).lower():
            failures.append(f"{slug} FR missing voice phrase: {phrase}")

    print("Wave 10 w10-3 guard (voice longtail FAQ)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: conversational voice FAQ on intent hubs EN+FR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
