#!/usr/bin/env python3
"""Fail when website GTA±150 FSA set drifts from porterchain_pricing.gta150_fsa_codes()."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / "website" / "src" / "lib" / "seo" / "gta150FsaCodes.ts"
sys.path.insert(0, str(ROOT / "services" / "pricing-engine"))

from porterchain_pricing.gta150_fsa import gta150_fsa_codes  # noqa: E402


def _codes_from_ts(text: str) -> set[str]:
    block = re.search(r"GTA150_FSA_CODES\s*=\s*new Set<string>\(\[(.*?)\]\)", text, re.S)
    if not block:
        raise SystemExit("website gta150FsaCodes.ts missing GTA150_FSA_CODES set")
    return set(re.findall(r'"([A-Z]\d[A-Z])"', block.group(1)))


def main() -> int:
    if not TS.is_file():
        print(f"FAIL: missing {TS.relative_to(ROOT)}")
        return 1
    text = TS.read_text(encoding="utf-8")
    if "Generated from porterchain_pricing.gta150_fsa_codes()" not in text:
        print("FAIL: website FSA file missing generated header (do not hand-edit)")
        return 1
    if "Auto-synced" in text:
        print("FAIL: stale 'Auto-synced' header — regenerate with sync_website_gta150_fsa.py")
        return 1
    if "export function isOntarioFsa" not in text:
        print("FAIL: website FSA module must export isOntarioFsa (no hand-copy in components)")
        return 1
    expected = set(gta150_fsa_codes())
    got = _codes_from_ts(text)
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        print(f"FAIL: website FSA drift (website={len(got)} engine={len(expected)})")
        if missing[:10]:
            print(f"  missing on website: {missing[:10]}")
        if extra[:10]:
            print(f"  extra on website: {extra[:10]}")
        print("  fix: python scripts/sync_website_gta150_fsa.py")
        return 1
    # Published coverage count (facts, llms.txt, copy) must equal the engine set size.
    facts = (ROOT / "website/src/lib/seo/delivery-programmatic.ts").read_text(encoding="utf-8")
    m = re.search(r"export const COVERAGE_FSA_COUNT = (\d+);", facts)
    if not m or int(m.group(1)) != len(expected):
        print(f"FAIL: COVERAGE_FSA_COUNT must be {len(expected)} (delivery-programmatic.ts)")
        return 1
    llms = (ROOT / "website/public/llms.txt").read_text(encoding="utf-8")
    claims = [int(n) for n in re.findall(r"\b(\d{3}) postal areas", llms)]
    if not claims or any(n != len(expected) for n in claims):
        print(f"FAIL: llms.txt postal-area count {claims} != {len(expected)}")
        return 1
    print(f"OK — website GTA±150 FSA set matches engine ({len(expected)} codes)")
    print(f"OK — published coverage count is {len(expected)} (facts constant + llms.txt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
