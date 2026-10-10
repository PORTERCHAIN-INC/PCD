#!/usr/bin/env python3
"""§1 Product Vision — capacity-first website, quote CTA, retail book routing."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
APP = WEBSITE / "src/app/[locale]"

REQUIRED_PAGES = (
    "platform/page.tsx",
    # Oct 2026: /solutions merged into the /delivery industry hubs (301s in lib/seo/redirects.ts).
    "delivery/page.tsx",
    "delivery/[industry]/page.tsx",
    "book/page.tsx",
)

HOME_FORBIDDEN_IMPORTS = (
    "DeliveryTypes",
    "WhoCanUse",
    "WhyPorterchain",
    "BookingWidget",
)

HERO_FORBIDDEN = "BookingWidget"

NAV_QUOTE_HREFS = (
    'quoteHref = "/contact?intent=quote"',
    'quoteHref = "/sign-up?intent=quote',
    "customerPortalBookUrl",
)
TOP_NAV_FORBIDDEN_IDS = ('id: "platform"', 'id: "developers"')

FOOTER_NAV = WEBSITE / "src/data/footer-navigation.ts"
SITE_FOOTER_EN = WEBSITE / "messages/site-footer-en.json"
NEXT_CONFIG = WEBSITE / "next.config.ts"


def _footer_hrefs() -> list[str]:
    text = FOOTER_NAV.read_text(encoding="utf-8")
    return re.findall(r'href:\s*"([^"]+)"', text)


def _route_exists(href: str) -> bool:
    if href.startswith("__"):
        return True
    href = href.split("?", 1)[0].split("#", 1)[0]
    path = href.strip("/")
    if not path:
        return APP.joinpath("page.tsx").is_file()
    direct = APP / path / "page.tsx"
    if direct.is_file():
        return True
    # Clerk catch-alls: sign-up/[[...sign-up]]/page.tsx
    if path:
        segment_dir = APP / path
        if segment_dir.is_dir():
            for child in segment_dir.iterdir():
                if child.is_dir() and child.name.startswith("[[") and (child / "page.tsx").is_file():
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

    # Capacity-first home uses HomeChooser + MarketingHero kit (corporate HeroSection).
    home_chooser = WEBSITE / "src/components/marketing/home/HomeChooser.tsx"
    marketing_hero = WEBSITE / "src/components/marketing/MarketingHero.tsx"
    corporate_hero = WEBSITE / "src/components/marketing/corporate/sections/HeroSection.tsx"
    hero_blob = ""
    for path in (home_chooser, marketing_hero, corporate_hero):
        if path.is_file():
            hero_blob += path.read_text(encoding="utf-8")
    if not home_chooser.is_file() or not marketing_hero.is_file():
        failures.append("missing HomeChooser / MarketingHero (capacity-first home kit)")
    else:
        if HERO_FORBIDDEN in hero_blob:
            failures.append("homepage hero kit still embeds BookingWidget (§1.1.3)")
        chooser_text = home_chooser.read_text(encoding="utf-8")
        if "sign-up?intent=quote" not in chooser_text and "sign-up?intent=quote" not in hero_blob:
            failures.append("homepage capacity kit missing quote CTA (sign-up?intent=quote)")
        if "/business" not in chooser_text and "/vehicles" not in chooser_text:
            failures.append("homepage capacity kit missing business/vehicles path")

    book_page = APP / "book/page.tsx"
    if book_page.is_file():
        book_text = book_page.read_text(encoding="utf-8")
        # Customer fast-book (v2): /book hosts the guest express form only — never the
        # legacy BookingWidget / draft flow.
        if "ExpressBook" not in book_text:
            failures.append("book page must render the guest ExpressBook (no-account booking)")
        if "BookingWidget" in book_text:
            failures.append("book page must not embed the legacy BookingWidget")

    navbar = WEBSITE / "src/components/layout/SiteNavbar.tsx"
    if navbar.is_file():
        nav_text = navbar.read_text(encoding="utf-8")
        if "BookingWidget" in nav_text:
            failures.append("navbar embeds BookingWidget (PV-G2)")
        if not any(marker in nav_text for marker in NAV_QUOTE_HREFS):
            failures.append('navbar primary CTA must link to /contact?intent=quote (not demo or customer portal book)')

    nav_data = WEBSITE / "src/data/navbar-navigation.ts"
    if nav_data.is_file():
        nav_items = nav_data.read_text(encoding="utf-8").split("export const navbarNavigation", 1)[-1]
        top_level_region = nav_items.split("children:", 1)[0]
        for marker in TOP_NAV_FORBIDDEN_IDS:
            if marker in top_level_region:
                failures.append(f"top-level nav must not expose {marker} before capacity services")

    home_page = APP / "page.tsx"
    if home_page.is_file():
        home_text = home_page.read_text(encoding="utf-8")
        for forbidden in HOME_FORBIDDEN_IMPORTS:
            if forbidden in home_text:
                failures.append(f"homepage still imports consumer section {forbidden} (PV-G2)")
        if "HomeChooser" not in home_text:
            failures.append("homepage must render HomeChooser (welcome capacity guide)")
        if "LaneASoftwareSchema" in home_text:
            failures.append("homepage must not emit SoftwareApplication schema during Phase 1 capacity positioning")
        if "HomeDeliverySchema" not in home_text:
            failures.append("homepage must emit delivery/local business schema")

    for rel in (
        "components/seo/IndustryLandingView.tsx",
        "components/seo/ContentClusterView.tsx",
        "components/seo/CityIndustryLandingView.tsx",
    ):
        path = WEBSITE / "src" / rel
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            if "PlatformBridgeSection" not in text:
                failures.append(f"{rel} missing PlatformBridgeSection (Lane B bridge)")

    next_text = NEXT_CONFIG.read_text(encoding="utf-8")
    redirects_ts = (WEBSITE / "src/lib/seo/redirects.ts").read_text(encoding="utf-8")
    if '"platform"' in next_text and "destination: `/${locale}/business`" in next_text:
        if re.search(r'source:\s*`/\$\{locale\}/platform`', next_text):
            failures.append("next.config still redirects /platform to /business")

    for old_hub in ("onboarding-education", "integrations-education"):
        if old_hub not in redirects_ts or "/faq" not in redirects_ts:
            failures.append(f"redirects.ts missing {old_hub} index redirect to /faq")
        hub_index = APP / old_hub / "page.tsx"
        if hub_index.is_file():
            failures.append(f"remove stub hub page {old_hub}/page.tsx (redirect-only)")

    dev_docs = APP / "developers/docs/page.tsx"
    if not dev_docs.is_file():
        failures.append("missing hosted developer docs hub at /developers/docs")

    for trust_exhibit in ("dpa", "msa"):
        if not (APP / "trust" / trust_exhibit / "page.tsx").is_file():
            failures.append(f"missing trust exhibit page /trust/{trust_exhibit} (P1.14)")

    corporate_en = WEBSITE / "messages/corporate-en.json"
    if corporate_en.is_file():
        corporate_blob = corporate_en.read_text(encoding="utf-8")
        if "99.2%" in corporate_blob:
            failures.append("corporate-en.json must not contain unsourced 99.2% SLA stat")
        corporate = json.loads(corporate_blob)
        home_blob = json.dumps(
            {
                "metadata": corporate.get("metadata", {}).get("home", {}),
                "home": corporate.get("home", {}),
            },
            ensure_ascii=False,
        ).lower()
        pricing_blob = json.dumps(corporate.get("pricing", {}), ensure_ascii=False).lower()
        business_en = WEBSITE / "messages/business-en.json"
        home_chooser_en = WEBSITE / "messages/en.json"
        if business_en.is_file():
            business = json.loads(business_en.read_text(encoding="utf-8"))
            pricing_blob += "\n" + json.dumps(business.get("billing", {}), ensure_ascii=False).lower()
        if home_chooser_en.is_file():
            home_msg = json.loads(home_chooser_en.read_text(encoding="utf-8"))
            home_blob += "\n" + json.dumps(home_msg.get("homeChooser", {}), ensure_ascii=False).lower()
        for forbidden in (
            "dispatch os",
            "dispatch operating system",
            "software-led pricing",
            "platform subscription",
            "$24k",
            "24k+ acv",
        ):
            if forbidden in home_blob or forbidden in pricing_blob:
                failures.append(f"capacity-first home/pricing copy must not contain '{forbidden}'")
        for required in ("transportation capacity", "vehicle", "driver", "get a quote"):
            if required not in home_blob and required not in pricing_blob:
                failures.append(f"capacity-first home/pricing copy must mention '{required}'")
        attribution_py = (WEBSITE / "src/lib/seo/attribution.ts").read_text(encoding="utf-8")
        if "from?:" not in attribution_py or "resolveLeadSource" not in attribution_py:
            failures.append("attribution.ts must capture from= for CRM tagging (P2.6)")
        if "pushAttributionToZoho" not in (
            WEBSITE / "src/lib/seo/zoho-attribution.ts"
        ).read_text(encoding="utf-8"):
            failures.append("missing Zoho attribution push (P2.6)")

    if corporate_en.is_file():
        corporate = json.loads(corporate_en.read_text(encoding="utf-8"))
        developers = corporate.get("developers", {})
        developer_blob = json.dumps(developers, ensure_ascii=False).lower()
        if "phase 1" in developer_blob:
            failures.append("corporate developers copy must not expose 'Phase 1' public API label")
        if "api v1" not in developer_blob or "rate limits" not in developer_blob:
            failures.append("corporate developers copy must include API v1 versioning and rate limits")

    phase2_py = ROOT / "shared/python/porterchain_shared/config/phase2.py"
    if phase2_py.is_file():
        phase2_text = phase2_py.read_text(encoding="utf-8")
        for field in ("crm", "route_center", "ai_dispatch", "analytics", "intelligence"):
            if not re.search(rf"^\s*{field}:\s*bool\s*=\s*False", phase2_text, re.MULTILINE):
                failures.append(f"Phase2Flags.{field} must default off (PV-G3)")

    for href in _footer_hrefs():
        if not _route_exists(href):
            failures.append(f"footer link {href} has no matching page route (§1.1.7)")

    footer_labels = json.loads(SITE_FOOTER_EN.read_text(encoding="utf-8"))
    sections = footer_labels.get("sections", {})
    # Oct 2026 footer IA: services / industries / company / support / legal.
    products = {**sections.get("products", {}).get("links", {}), **sections.get("services", {}).get("links", {})}
    resources_links = {**sections.get("resources", {}).get("links", {}), **sections.get("support", {}).get("links", {})}
    company_links = {**sections.get("company", {}).get("links", {}), **sections.get("support", {}).get("links", {})}
    # Website Phase 1 IA (Oct 2026): five navbar links (Price, Industries, Track, Shopify app,
    # Sign in); Merchants (/business) moved to the footer crawl map. Either surface satisfies this.
    navbar_data = WEBSITE / "src/data/navbar-navigation.ts"
    navbar_text = navbar_data.read_text(encoding="utf-8") if navbar_data.is_file() else ""
    footer_nav_text = FOOTER_NAV.read_text(encoding="utf-8") if FOOTER_NAV.is_file() else ""
    if 'href: "/business"' not in navbar_text and 'href: "/business"' not in footer_nav_text:
        failures.append("merchants /business capacity link missing from navbar and footer navigation")
    if "getQuote" not in products and "price" not in products and "contact" not in company_links:
        failures.append("site-footer-en.json missing quote path (products.getQuote or company.contact)")
    if "trust" not in company_links and "trust" not in sections.get("solutions", {}).get("links", {}):
        failures.append("site-footer-en.json missing trust link (company.links.trust)")
    if (
        "platform" not in resources_links
        and "platform" not in products
        and "howItWorks" not in products
        and "howPorterchainWorks" not in resources_links
    ):
        failures.append(
            "site-footer-en.json missing platform/how-it-works link (resources.links.platform or howPorterchainWorks)"
        )

    print("Product vision pages guard (§1.1.3–1.1.7 · PV-G2/G3)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: capacity-first site, quote CTA on-site, Phase 2 default off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
