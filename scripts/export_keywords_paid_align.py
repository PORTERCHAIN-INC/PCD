#!/usr/bin/env python3
"""Export KEYWORDS map → docs/ops/KEYWORDS_PAID_ALIGN.md for Ads/LinkedIn align."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "website/src/lib/seo/seo-content/industries.ts"
OUT = ROOT / "docs/ops/KEYWORDS_PAID_ALIGN.md"


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    m = re.search(r"const KEYWORDS:.*?=\s*\{(.*?)\n\};", text, re.S)
    if not m:
        raise SystemExit("KEYWORDS map not found in industries.ts")
    body = m.group(1)
    entries = re.findall(r'["\']?([\w-]+)["\']?\s*:\s*\[(.*?)\]', body, re.S)
    rows: list[tuple[str, str, str]] = []
    for niche, arr in entries:
        kws = re.findall(r'"([^"]+)"', arr)
        if not kws:
            continue
        primary, *rest = kws
        rows.append((niche, primary, " · ".join(rest)))
    rows.sort()
    lines = [
        "# KEYWORDS paid-align checklist",
        "",
        "SSOT: `website/src/lib/seo/seo-content/industries.ts` (`KEYWORDS`).",
        "Google Ads / LinkedIn: bid only on these primaries; remove campaign terms not in this table.",
        "",
        "Regenerate: `python3 scripts/export_keywords_paid_align.py`",
        "",
        "| Niche | Primary (must keep) | Secondary |",
        "| --- | --- | --- |",
    ]
    for niche, primary, rest in rows:
        lines.append(f"| `{niche}` | {primary} | {rest or '—'} |")
    lines += ["", f"_Rows: {len(rows)}_ · Update Ads after regenerating this file.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(rows)} niches)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
