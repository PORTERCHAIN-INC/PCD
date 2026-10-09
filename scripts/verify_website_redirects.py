#!/usr/bin/env python3
"""Verify the website redirect registry is applied in ONE hop by middleware.

Contract (GSC clean-up, Oct 2026): redirects.ts is the registry; src/lib/seo/url-policy.ts
compiles it and middleware answers every legacy URL with a single 301 (or 410). next.config
must NOT also emit the registry (its redirects run before middleware and create chains), and
Next's own trailing-slash redirect is disabled for the same reason. Chain/loop freedom is
asserted by `pnpm --dir website test:seo`.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REDIRECTS_TS = ROOT / "website/src/lib/seo/redirects.ts"
NEXT_CONFIG = ROOT / "website/next.config.ts"
URL_POLICY = ROOT / "website/src/lib/seo/url-policy.ts"
MIDDLEWARE = ROOT / "website/src/middleware.ts"
POLICY_TEST = ROOT / "website/src/lib/seo/url-policy.test.mts"


def main() -> int:
    failures: list[str] = []
    redirects_text = REDIRECTS_TS.read_text(encoding="utf-8")
    next_text = NEXT_CONFIG.read_text(encoding="utf-8")

    if "export function toNextRedirects" not in redirects_text:
        failures.append("redirects.ts: missing toNextRedirects()")
    policy_text = URL_POLICY.read_text(encoding="utf-8") if URL_POLICY.is_file() else ""
    mw_text = MIDDLEWARE.read_text(encoding="utf-8")
    if "WEBSITE_REDIRECTS" not in policy_text:
        failures.append("url-policy.ts: must compile WEBSITE_REDIRECTS from redirects.ts")
    if "resolveUrlPolicy" not in mw_text:
        failures.append("middleware.ts: must apply resolveUrlPolicy (single-hop redirects)")
    if "skipTrailingSlashRedirect: true" not in next_text:
        failures.append("next.config.ts: skipTrailingSlashRedirect must be true (policy normalises)")
    if re.search(r"redirects\(\)[^}]*return\s+toNextRedirects\(\)\s*;", next_text, re.S):
        failures.append("next.config.ts: must not emit the registry (chains before middleware)")
    if not POLICY_TEST.is_file():
        failures.append("missing url-policy.test.mts (no-chain / no-loop contract)")

    for match in re.finditer(r"source:\s*[`\"]([^`\"]+)[`\"]", redirects_text):
        source = match.group(1)
        if not source.startswith("/"):
            failures.append(f"redirect source must start with /: {source}")

    print("Website redirects guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: registry applied by middleware url-policy in one hop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
