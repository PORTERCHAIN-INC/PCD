#!/usr/bin/env python3
"""Wave 10 w10-1 guard — Core Web Vitals INP RUM + perf budget on matrix + /business."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
PKG = WEBSITE / "package.json"
PERF = WEBSITE / "src/lib/seo/perf-budget.ts"
REPORT = WEBSITE / "src/lib/seo/web-vitals-report.ts"
REPORTER = WEBSITE / "src/components/seo/WebVitalsReporter.tsx"
INTEGRATIONS = WEBSITE / "src/components/integrations/DeferredSiteIntegrations.tsx"
ANALYTICS = WEBSITE / "src/lib/seo/analytics.ts"
BUSINESS_SECTIONS = WEBSITE / "src/components/business/BusinessPageSections.tsx"
CITY_VIEW = WEBSITE / "src/components/seo/CityIndustryLandingView.tsx"
GLOBALS = WEBSITE / "src/app/globals.css"


def main() -> int:
    failures: list[str] = []

    pkg = PKG.read_text(encoding="utf-8")
    if '"web-vitals"' not in pkg:
        failures.append("website/package.json missing web-vitals dependency")

    perf = PERF.read_text(encoding="utf-8")
    if "PERF_BUDGET_INP_GOOD_MS" not in perf or "classifyPageRoute" not in perf:
        failures.append("perf-budget.ts missing INP budget / classifyPageRoute")
    if '"business"' not in perf or '"matrix"' not in perf:
        failures.append("perf-budget.ts missing business/matrix route classes")

    report = REPORT.read_text(encoding="utf-8")
    if "reportWebVitalMetric" not in report:
        failures.append("web-vitals-report.ts missing reportWebVitalMetric")

    reporter = REPORTER.read_text(encoding="utf-8")
    if "onINP" not in reporter:
        failures.append("WebVitalsReporter.tsx missing onINP")

    integrations = INTEGRATIONS.read_text(encoding="utf-8")
    if "WebVitalsReporter" not in integrations:
        failures.append("DeferredSiteIntegrations missing WebVitalsReporter")

    analytics = ANALYTICS.read_text(encoding="utf-8")
    if "WEB_VITAL" not in analytics:
        failures.append("analytics.ts missing WEB_VITAL event")

    business = BUSINESS_SECTIONS.read_text(encoding="utf-8")
    if "dynamic(" not in business or "perf-defer-section" not in business:
        failures.append("BusinessPageSections missing dynamic split + perf-defer-section")

    city = CITY_VIEW.read_text(encoding="utf-8")
    if "dynamic(" not in city or "PostalCoverageChecker" not in city:
        failures.append("CityIndustryLandingView missing dynamic PostalCoverageChecker")

    globals_css = GLOBALS.read_text(encoding="utf-8")
    if "perf-defer-section" not in globals_css:
        failures.append("globals.css missing perf-defer-section content-visibility")

    print("Wave 10 w10-1 guard (INP RUM + perf budget)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: INP RUM, route classification, business/matrix code-split")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
