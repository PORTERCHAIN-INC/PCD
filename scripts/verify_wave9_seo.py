#!/usr/bin/env python3
"""Wave 9 SEO guard — hyperlocal schema, intent hubs, SLA, engagement hooks."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
SCHEMA = WEBSITE / "src/lib/seo/schema.ts"
GEO = WEBSITE / "src/lib/seo/hyperlocal-geo.ts"
FAQ = WEBSITE / "src/lib/seo/content/faq-clusters.ts"
LINKING = WEBSITE / "src/lib/seo/internal-linking.ts"
FR = WEBSITE / "messages/seo-programmatic-fr.json"
CONTACT = WEBSITE / "src/app/[locale]/contact/page.tsx"
HERO_COPY = WEBSITE / "src/components/sections/HeroCopy.tsx"
CITY_VIEW = WEBSITE / "src/components/seo/CityIndustryLandingView.tsx"
BUSINESS = WEBSITE / "src/app/[locale]/business/page.tsx"
GUIDES = WEBSITE / "src/app/[locale]/guides/[slug]/page.tsx"
ACCORDION = WEBSITE / "src/components/ui/Accordion.tsx"

INTENT_SLUGS = ("same-day-retail-distribution", "fleet-overflow-wholesale-delivery")


def main() -> int:
    failures: list[str] = []

    schema = SCHEMA.read_text(encoding="utf-8")
    if "geoSlug" not in schema or "GeoCoordinates" not in schema:
        failures.append("schema.ts missing hyperlocal geoSlug / GeoCoordinates")
    if "knowsAbout" not in schema:
        failures.append("schema.ts Organization missing knowsAbout (E-E-A-T)")
    if "buildSpeakableWebPageSchema" not in schema:
        failures.append("schema.ts missing buildSpeakableWebPageSchema")
    if "authorPerson" not in schema:
        failures.append("schema.ts buildArticleSchema missing authorPerson (guides E-E-A-T)")

    geo = GEO.read_text(encoding="utf-8")
    if "SERVICE_AREA_GEO" not in geo or "toronto" not in geo:
        failures.append("hyperlocal-geo.ts missing SERVICE_AREA_GEO")

    linking = LINKING.read_text(encoding="utf-8")
    if "buildIntentHubLinks" not in linking:
        failures.append("internal-linking.ts missing buildIntentHubLinks")
    for slug in INTENT_SLUGS:
        if slug not in linking:
            failures.append(f"internal-linking.ts missing intent hub slug: {slug}")

    faq = FAQ.read_text(encoding="utf-8")
    for slug in INTENT_SLUGS:
        if f'slug: "{slug}"' not in faq:
            failures.append(f"faq-clusters missing intent hub: {slug}")

    fr = json.loads(FR.read_text(encoding="utf-8"))
    for slug in INTENT_SLUGS:
        if slug not in fr.get("faq", {}):
            failures.append(f"seo-programmatic-fr.json missing FAQ: {slug}")

    contact = CONTACT.read_text(encoding="utf-8")
    if "SlaResponseCountdown" not in contact:
        failures.append("contact page missing SlaResponseCountdown")

    hero = HERO_COPY.read_text(encoding="utf-8")
    if "SlaResponseCountdown" not in hero:
        failures.append("home HeroCopy missing SlaResponseCountdown")

    city_view = CITY_VIEW.read_text(encoding="utf-8")
    if "PostalCoverageChecker" not in city_view:
        failures.append("CityIndustryLandingView missing PostalCoverageChecker")
    if "geoSlug: serviceAreaSlug" not in city_view:
        failures.append("CityIndustryLandingView missing hyperlocal geoSlug schema")
    if "buildIntentHubLinks" not in city_view:
        failures.append("CityIndustryLandingView missing intent hub internal links")

    business = BUSINESS.read_text(encoding="utf-8")
    if "buildSpeakableWebPageSchema" not in business:
        failures.append("business page missing speakable WebPage schema")
    if "buildFAQPageSchema" not in business:
        failures.append("business page missing FAQPage schema")

    guides = GUIDES.read_text(encoding="utf-8")
    if "buildArticleSchema" not in guides or "authorPerson" not in guides:
        failures.append("guides page missing Article schema with authorPerson")

    accordion = ACCORDION.read_text(encoding="utf-8")
    if "speakable-faq-q" not in accordion or "speakable-faq-a" not in accordion:
        failures.append("Accordion missing speakable FAQ CSS classes")

    cluster = WEBSITE / "src/components/seo/ContentClusterView.tsx"
    cluster_text = cluster.read_text(encoding="utf-8")
    before_compare = cluster_text.split("data.comparisonRows &&")[0]
    if "FaqSection" not in before_compare or "faqItems.length" not in before_compare:
        failures.append("ContentClusterView FAQ should render before comparison (AI-first)")

    print("Wave 9 SEO guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: hyperlocal schema, intent hubs, SLA, speakable, engagement hooks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
