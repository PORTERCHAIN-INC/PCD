#!/usr/bin/env python3
"""Verify website redirect registry is wired into next.config and entries are well-formed."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REDIRECTS_TS = ROOT / "website/src/lib/seo/redirects.ts"
NEXT_CONFIG = ROOT / "website/next.config.ts"


def main() -> int:
    failures: list[str] = []
    redirects_text = REDIRECTS_TS.read_text(encoding="utf-8")
    next_text = NEXT_CONFIG.read_text(encoding="utf-8")

    if "export function toNextRedirects" not in redirects_text:
        failures.append("redirects.ts: missing toNextRedirects()")
    if "toNextRedirects" not in next_text:
        failures.append("next.config.ts: must import/use toNextRedirects from redirects.ts")
    if "redirects.ts" not in next_text and "redirects" not in next_text:
        failures.append("next.config.ts: redirect registry not referenced")

    for match in re.finditer(r"source:\s*[`\"]([^`\"]+)[`\"]", redirects_text):
        source = match.group(1)
        if not source.startswith("/"):
            failures.append(f"redirect source must start with /: {source}")

    print("Website redirects guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: redirect registry present and wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
