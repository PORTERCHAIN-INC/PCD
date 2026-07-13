#!/usr/bin/env python3
"""Wave 10 w10-6 guard — entire web surface is light-mode only.

No prefers-color-scheme dark on website or portals; html colorScheme stays light.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TARGETS: tuple[tuple[Path, Path], ...] = (
    (ROOT / "apps/merchant-portal/src/app/globals.css", ROOT / "apps/merchant-portal/src/app/layout.tsx"),
    (ROOT / "apps/admin/src/app/globals.css", ROOT / "apps/admin/src/app/layout.tsx"),
    (ROOT / "apps/customer/src/app/globals.css", ROOT / "apps/customer/src/app/layout.tsx"),
    (ROOT / "apps/driver-portal/src/app/globals.css", ROOT / "apps/driver-portal/src/app/layout.tsx"),
    (ROOT / "website/src/app/globals.css", ROOT / "website/src/app/layout.tsx"),
)


def main() -> int:
    failures: list[str] = []

    for css_path, layout_path in TARGETS:
        label = css_path.relative_to(ROOT).parts[0] if "website" not in str(css_path) else "website"
        if "website" in str(css_path):
            label = "website"
        elif "merchant" in str(css_path):
            label = "merchant-portal"
        elif "admin" in str(css_path):
            label = "admin"
        elif "customer" in str(css_path):
            label = "customer"
        else:
            label = "driver-portal"

        if css_path.is_file():
            css = css_path.read_text(encoding="utf-8")
            if "prefers-color-scheme: dark" in css:
                failures.append(f"{label} globals.css must stay light-only (no dark media query)")
        else:
            failures.append(f"missing {css_path.relative_to(ROOT)}")

        if layout_path.is_file():
            layout = layout_path.read_text(encoding="utf-8")
            if 'colorScheme: "light dark"' in layout or "colorScheme: 'light dark'" in layout:
                failures.append(f"{label} layout must not use light dark colorScheme")
            if 'colorScheme: "dark"' in layout or "colorScheme: 'dark'" in layout:
                failures.append(f"{label} layout must not force dark colorScheme")
            if 'colorScheme: "light"' not in layout and "colorScheme: 'light'" not in layout:
                failures.append(f"{label} layout must force colorScheme light")
        else:
            failures.append(f"missing {layout_path.relative_to(ROOT)}")

    portal_css = (ROOT / "apps/merchant-portal/src/app/globals.css").read_text(encoding="utf-8")
    if "portal-surface" not in portal_css:
        failures.append("merchant-portal globals.css missing portal-surface utility")

    web_locale = ROOT / "website/src/app/[locale]/layout.tsx"
    if web_locale.is_file():
        text = web_locale.read_text(encoding="utf-8")
        if 'colorScheme: "light dark"' in text or 'colorScheme: "dark"' in text:
            failures.append("website locale layout must stay light-only")

    print("Wave 10 w10-6 guard (light-mode only across website + portals)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: light-only color scheme on website, admin, merchant, customer, driver")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
