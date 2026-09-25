#!/usr/bin/env python3
"""EN/FR message parity — EN-only niches and service areas must be draft expansions only."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "website/messages/en.json"
FR = ROOT / "website/messages/fr.json"
DRAFT = ROOT / "website/src/lib/seo/content/draft-expansions.ts"


def _draft_map_values(const_name: str) -> set[str]:
    text = DRAFT.read_text(encoding="utf-8")
    m = re.search(rf"export const {const_name}[^=]*=\s*\{{(.*?)\n\}};", text, re.S)
    if not m:
        return set()
    return set(re.findall(r':\s*"([A-Za-z0-9_]+)"', m.group(1)))


def main() -> int:
    failures: list[str] = []
    en = json.loads(EN.read_text(encoding="utf-8"))
    fr = json.loads(FR.read_text(encoding="utf-8"))

    niche_draft = _draft_map_values("DRAFT_NICHE_MESSAGE_KEYS")
    area_draft = _draft_map_values("DRAFT_SERVICE_AREA_MESSAGE_KEYS")

    en_niches = set((en.get("nicheLanding") or {}).keys())
    fr_niches = set((fr.get("nicheLanding") or {}).keys())
    only_en_niches = en_niches - fr_niches
    unexpected_niches = only_en_niches - niche_draft
    if unexpected_niches:
        failures.append(f"EN-only niches not in draft gates: {sorted(unexpected_niches)}")
    missing_niche_draft = niche_draft - en_niches
    if missing_niche_draft:
        failures.append(f"draft niches missing from en.json: {sorted(missing_niche_draft)}")

    en_areas = set((en.get("serviceAreaLanding") or {}).keys())
    fr_areas = set((fr.get("serviceAreaLanding") or {}).keys())
    only_en_areas = en_areas - fr_areas
    unexpected_areas = only_en_areas - area_draft
    if unexpected_areas:
        failures.append(f"EN-only service areas not in draft gates: {sorted(unexpected_areas)}")
    missing_area_draft = area_draft - en_areas
    if missing_area_draft:
        failures.append(f"draft service areas missing from en.json: {sorted(missing_area_draft)}")

    if failures:
        print("Website FR message parity")
        for f in failures:
            print(f"  FAIL: {f}")
        return 1

    print(
        "Website FR message parity\n"
        f"  PASS: EN-only niches ({len(only_en_niches)}) ⊆ draft; "
        f"shared niches={len(en_niches & fr_niches)}\n"
        f"  PASS: EN-only service areas ({len(only_en_areas)}) ⊆ draft; "
        f"shared areas={len(en_areas & fr_areas)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
