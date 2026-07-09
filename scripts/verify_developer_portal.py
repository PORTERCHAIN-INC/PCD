#!/usr/bin/env python3
"""Developer portal guard — §7.1.6 website route + footer link."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEVELOPERS_PAGE = ROOT / "website/src/app/[locale]/developers/page.tsx"
FOOTER_NAV = ROOT / "website/src/data/footer-navigation.ts"
SITE_FOOTER_EN = ROOT / "website/messages/site-footer-en.json"
CORPORATE_EN = ROOT / "website/messages/corporate-en.json"
CORPORATE_FR = ROOT / "website/messages/corporate-fr.json"
PARTNER_GUIDE = ROOT / "docs/api/PARTNER_GUIDE.md"
POSTMAN = ROOT / "docs/api/porterchain.postman.json"
CHANGELOG = ROOT / "docs/api/CHANGELOG.md"
OPENAPI = ROOT / "docs/api/openapi.json"


def main() -> int:
    failures: list[str] = []

    if not DEVELOPERS_PAGE.is_file():
        failures.append("missing website/src/app/[locale]/developers/page.tsx")

    footer_text = FOOTER_NAV.read_text(encoding="utf-8")
    if 'id: "developers"' not in footer_text or 'href: "/developers"' not in footer_text:
        failures.append("footer-navigation.ts missing /developers link")

    site_footer = SITE_FOOTER_EN.read_text(encoding="utf-8")
    if '"developers"' not in site_footer:
        failures.append("site-footer-en.json missing developers label")

    for name, path in (("corporate-en.json", CORPORATE_EN), ("corporate-fr.json", CORPORATE_FR)):
        if not path.is_file():
            failures.append(f"missing {name}")
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if "sandbox" not in lowered:
            failures.append(f"{name} missing sandbox keys copy (§7.1.8)")
        has_key_guidance = (
            "pk_sandbox" in text
            or "sandbox api keys" in lowered
            or "clés sandbox" in lowered
            or "sandbox keys" in lowered
        )
        if not has_key_guidance:
            failures.append(f"{name} missing sandbox key guidance")

    for label, path in (
        ("PARTNER_GUIDE", PARTNER_GUIDE),
        ("postman collection", POSTMAN),
        ("API CHANGELOG", CHANGELOG),
        ("openapi.json", OPENAPI),
    ):
        if not path.is_file():
            failures.append(f"missing {label} ({path.relative_to(ROOT)})")

    if DEVELOPERS_PAGE.is_file():
        dev_text = DEVELOPERS_PAGE.read_text(encoding="utf-8")
        for needle in ("OpenAPI", "Postman", "webhook"):
            if needle.lower() not in dev_text.lower():
                failures.append(f"developers page missing {needle} reference")

    if failures:
        print("Developer portal guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("Developer portal guard passed (§7.1 · PLT-G2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
