#!/usr/bin/env python3
"""Website SEO metadata guard — canonical/hreflang helpers on indexable pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "website/src/app/[locale]"
HELPERS = ROOT / "website/src/lib/seo/page-helpers.ts"
HREFLANG = ROOT / "website/src/lib/seo/hreflang.ts"

INDEX_PAGES = (
    "page.tsx",
    "company/page.tsx",
    "platform/page.tsx",
    "business/page.tsx",
    "contact/page.tsx",
    "developers/page.tsx",
    "developers/docs/page.tsx",
    "delivery/page.tsx",
    "enterprise/page.tsx",
    "faq/page.tsx",
    "trust/page.tsx",
    "blog/page.tsx",
    "careers/page.tsx",
    "privacy/page.tsx",
    "terms/page.tsx",
    "cookies/page.tsx",
)

SLUG_PAGES_REQUIRING_HELPER = (
    APP / "delivery/[industry]/page.tsx",
    APP / "developers/docs/[slug]/page.tsx",
    APP / "onboarding-education/[slug]/page.tsx",
)

BARE_METADATA_PATTERN = re.compile(
    r"openGraph:\s*\{\s*title:\s*t\(",
    re.MULTILINE,
)


def check_page(path: Path, failures: list[str]) -> None:
    if not path.is_file():
        failures.append(f"{path.relative_to(ROOT)}: missing indexable page")
        return
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(ROOT)
    if "generateMetadata" not in text:
        return
    if "buildPageMetadata" not in text and "buildProgrammaticPageMetadata" not in text:
        failures.append(f"{rel}: must use page metadata helper for canonical/hreflang")
    if BARE_METADATA_PATTERN.search(text):
        failures.append(f"{rel}: generateMetadata must not return bare openGraph object")


def main() -> int:
    failures: list[str] = []

    for rel in INDEX_PAGES:
        check_page(APP / rel, failures)

    for path in SLUG_PAGES_REQUIRING_HELPER:
        if not path.is_file():
            continue
        check_page(path, failures)

    hreflang = HREFLANG.read_text(encoding="utf-8")
    if "defaultOpenGraphImages" not in hreflang:
        failures.append("hreflang.ts: missing defaultOpenGraphImages for OG/Twitter images")
    if "twitter:" not in hreflang:
        failures.append("hreflang.ts: missing twitter card metadata")

    og_image = ROOT / "website/src/app/opengraph-image.tsx"
    if not og_image.exists():
        failures.append("website/src/app/opengraph-image.tsx missing")

    for path in [*SLUG_PAGES_REQUIRING_HELPER, HELPERS]:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "buildEnglishOnlyPageMetadata" in text and path != HELPERS:
            failures.append(f"{path.relative_to(ROOT)}: deprecated buildEnglishOnlyPageMetadata usage")

    print("Website SEO metadata guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: index and slug pages use metadata helpers with OG images")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
