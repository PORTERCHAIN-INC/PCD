#!/usr/bin/env python3
"""Website SEO metadata guard — canonical/hreflang helpers on slug pages."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "website/src/app"
HELPERS = ROOT / "website/src/lib/seo/page-helpers.ts"

SLUG_PAGES_REQUIRING_HELPER = (
    APP / "[locale]/solutions/[vertical]/page.tsx",
    APP / "[locale]/developers/docs/[slug]/page.tsx",
    APP / "[locale]/integrations-education/[slug]/page.tsx",
    APP / "[locale]/onboarding-education/[slug]/page.tsx",
    APP / "[locale]/how-porterchain-works/page.tsx",
)


def main() -> int:
    failures: list[str] = []

    for path in SLUG_PAGES_REQUIRING_HELPER:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if "buildPageMetadata" not in text and "buildProgrammaticPageMetadata" not in text:
            failures.append(f"{rel}: must use page metadata helper for canonical/hreflang")
        if "return {" in text.partition("generateMetadata")[2].partition("}")[0]:
            failures.append(f"{rel}: generateMetadata should not return bare metadata object")

    for path in [*SLUG_PAGES_REQUIRING_HELPER, HELPERS]:
        text = path.read_text(encoding="utf-8")
        if "buildEnglishOnlyPageMetadata" in text and path != HELPERS:
            failures.append(f"{path.relative_to(ROOT)}: deprecated buildEnglishOnlyPageMetadata usage")

    print("Website SEO metadata guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: slug pages use metadata helpers with canonical/hreflang")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
