#!/usr/bin/env python3
"""Wave 10 w10-6 guard — merchant portal system dark-mode tokens only.

Marketing website stays light-only permanently (no prefers-color-scheme dark).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORTAL_GLOBALS = ROOT / "apps/merchant-portal/src/app/globals.css"
PORTAL_LAYOUT = ROOT / "apps/merchant-portal/src/app/layout.tsx"
WEB_GLOBALS = ROOT / "website/src/app/globals.css"
WEB_LAYOUT = ROOT / "website/src/app/[locale]/layout.tsx"


def main() -> int:
    failures: list[str] = []

    portal_css = PORTAL_GLOBALS.read_text(encoding="utf-8")
    if "prefers-color-scheme: dark" not in portal_css:
        failures.append("merchant-portal globals.css missing dark media query")
    if "portal-surface" not in portal_css:
        failures.append("merchant-portal globals.css missing portal-surface utility")

    portal_layout = PORTAL_LAYOUT.read_text(encoding="utf-8")
    if "colorScheme" not in portal_layout:
        failures.append("merchant-portal layout missing color-scheme meta/style")

    web_css = WEB_GLOBALS.read_text(encoding="utf-8")
    if "prefers-color-scheme: dark" in web_css:
        failures.append("website globals.css must stay light-only (no dark media query)")

    web_layout = WEB_LAYOUT.read_text(encoding="utf-8")
    if 'colorScheme: "light dark"' in web_layout or "colorScheme: 'light dark'" in web_layout:
        failures.append("website locale layout must not use light dark colorScheme")
    if 'colorScheme: "dark"' in web_layout:
        failures.append("website locale layout must not force dark colorScheme")

    print("Wave 10 w10-6 guard (portal dark mode; marketing light-only)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: system dark on merchant portal; marketing website light-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
