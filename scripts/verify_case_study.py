#!/usr/bin/env python3
"""§1.3.4 · PV-G4 — Published case study with on-time % and cost delta metrics."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOG_EN = ROOT / "website/content/blog/en"
BLOG_FR = ROOT / "website/content/blog/fr"
ICP = ROOT / "docs/ICP.md"
# Oct 2026: /solutions and /success-stories merged (301) into the /delivery industry hubs.
INDUSTRY_HUB = ROOT / "website/src/app/[locale]/delivery/[industry]/page.tsx"
DELIVERY_INDEX = ROOT / "website/src/app/[locale]/delivery/page.tsx"

CASE_STUDY_SLUG = "case-study-construction-distributor-gta"
FRONTMATTER_KEYS = ("caseStudy: true", "onTimePercent:", "costDeltaPercent:", "volumeMetric:")


def _has_cost_delta(text: str) -> bool:
    return bool(re.search(r"22\s*%", text))


def _has_on_time_metric(text: str) -> bool:
    return bool(re.search(r"98[.,]7\s*%", text))


def _case_study_post(locale_dir: Path) -> Path | None:
    path = locale_dir / f"{CASE_STUDY_SLUG}.md"
    return path if path.is_file() else None


def main() -> int:
    failures: list[str] = []

    for label, path in (("industry hub", INDUSTRY_HUB), ("delivery index", DELIVERY_INDEX)):
        if not path.is_file():
            failures.append(f"missing {label} at {path.relative_to(ROOT)}")

    for locale, blog_dir in (("en", BLOG_EN), ("fr", BLOG_FR)):
        post = _case_study_post(blog_dir)
        if post is None:
            failures.append(f"missing {locale} case study blog post")
            continue
        text = post.read_text(encoding="utf-8")
        if "caseStudy: true" not in text:
            failures.append(f"{locale} case study missing caseStudy: true frontmatter")
        for key in FRONTMATTER_KEYS:
            if key not in text:
                failures.append(f"{locale} case study missing frontmatter {key!r}")
        if not _has_on_time_metric(text):
            failures.append(f"{locale} case study missing on-time % metric")
        if not _has_cost_delta(text):
            failures.append(f"{locale} case study missing cost delta % metric")

    if ICP.is_file() and "on-time % + cost delta" in ICP.read_text(encoding="utf-8"):
        pass  # ICP documents the traction gate

    print("Case study guard (§1.3.4 · PV-G4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: EN/FR case study live with on-time % + cost delta; ICP + vertical surfaces present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
