#!/usr/bin/env python3
"""§1 Product Vision — platform/solutions pages, retail book routing, footer links."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
APP = WEBSITE / "src/app/[locale]"

REQUIRED_PAGES = (
    "platform/page.tsx",
    "solutions/page.tsx",
    "solutions/[vertical]/page.tsx",
    "book/page.tsx",
)

HERO_FORBIDDEN = "BookingWidget"
HERO_REQUIRED = ("corporate.home.hero", "customerPortalBookUrl", "/platform")

FOOTER_NAV = WEBSITE / "src/data/footer-navigation.ts"
SITE_FOOTER_EN = WEBSITE / "messages/site-footer-en.json"
NEXT_CONFIG = WEBSITE / "next.config.ts"


def _footer_hrefs() -> list[str]:
    text = FOOTER_NAV.read_text(encoding="utf-8")
    return re.findall(r'href:\s*"([^"]+)"', text)


def _route_exists(href: str) -> bool:
    if href.startswith("__"):
        return True
    path = href.strip("/")
    if not path:
        return APP.joinpath("page.tsx").is_file()
    direct = APP / path / "page.tsx"
    if direct.is_file():
        return True
    # industry/construction-materials -> industry/[slug]/page.tsx
    parts = path.split("/")
    if len(parts) == 2 and (APP / parts[0] / "[slug]" / "page.tsx").is_file():
        return True
    if len(parts) == 2 and (APP / parts[0] / "[vertical]" / "page.tsx").is_file():
        return True
    if len(parts) == 3 and (APP / parts[0] / "[slug]" / "page.tsx").is_file():
        return True
    if len(parts) == 2 and (APP / parts[0] / "[category]" / "page.tsx").is_file():
        return True
    return False


def main() -> int:
    failures: list[str] = []

    for rel in REQUIRED_PAGES:
        if not APP.joinpath(rel).is_file():
            failures.append(f"missing page {rel}")

    hero = WEBSITE / "src/components/sections/Hero.tsx"
    if not hero.is_file():
        failures.append("missing Hero.tsx")
    else:
        hero_text = hero.read_text(encoding="utf-8")
        if HERO_FORBIDDEN in hero_text:
            failures.append("homepage Hero still embeds BookingWidget (§1.1.3)")
        for needle in HERO_REQUIRED:
            if needle not in hero_text:
                failures.append(f"Hero.tsx missing {needle}")

    book_page = APP / "book/page.tsx"
    if book_page.is_file():
        book_text = book_page.read_text(encoding="utf-8")
        if "customerPortalBookUrl" not in book_text and "portal-book-redirect" not in book_text:
            failures.append("book page does not redirect to customer portal (§1.1.4)")

    navbar = WEBSITE / "src/components/layout/SiteNavbar.tsx"
    if navbar.is_file():
        nav_text = navbar.read_text(encoding="utf-8")
        if "BookingWidget" in nav_text:
            failures.append("navbar embeds BookingWidget (PV-G2)")
        if "customerPortalBookUrl" not in nav_text:
            failures.append("navbar Book Now must link to customer portal (PV-G2)")

    home_page = APP / "page.tsx"
    if home_page.is_file():
        home_text = home_page.read_text(encoding="utf-8")
        if "BookingWidget" in home_text:
            failures.append("homepage still imports BookingWidget (PV-G2)")

    phase2_py = ROOT / "shared/python/porterchain_shared/config/phase2.py"
    if phase2_py.is_file():
        import sys

        sys.path.insert(0, str(ROOT / "shared/python"))
        from porterchain_shared.config.phase2 import Phase2Flags

        if Phase2Flags().any_enabled():
            failures.append("Phase 2 flags must default off (PV-G3)")

    next_text = NEXT_CONFIG.read_text(encoding="utf-8")
    if '"platform"' in next_text and "destination: `/${locale}/business`" in next_text:
        if re.search(r'source:\s*`/\$\{locale\}/platform`', next_text):
            failures.append("next.config still redirects /platform to /business")

    for href in _footer_hrefs():
        if not _route_exists(href):
            failures.append(f"footer link {href} has no matching page route (§1.1.7)")

    footer_labels = json.loads(SITE_FOOTER_EN.read_text(encoding="utf-8"))
    products = footer_labels.get("sections", {}).get("products", {}).get("links", {})
    for key in ("platform", "solutions", "book"):
        if key not in products:
            failures.append(f"site-footer-en.json missing products.links.{key}")

    print("Product vision pages guard (§1.1.3–1.1.7 · PV-G2/G3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: platform-first site, retail book externalized, Phase 2 default off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
