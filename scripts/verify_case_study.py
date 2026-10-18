#!/usr/bin/env python3
"""§1.3.4 · PV-G4 — No unverified case studies.

Oct 2026: the construction-distributor case study (98.7% on-time, 22% cost
delta) was not a real, verifiable customer result and was retired. This guard
now keeps it (and any other unverified ``caseStudy: true`` post) from coming
back until a real, customer-approved case study exists.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOG_DIRS = (ROOT / "website/content/blog/en", ROOT / "website/content/blog/fr")
INDUSTRY_HUB = ROOT / "website/src/app/[locale]/delivery/[industry]/page.tsx"
DELIVERY_INDEX = ROOT / "website/src/app/[locale]/delivery/page.tsx"
RETIRED_SLUG = "case-study-construction-distributor-gta"


def main() -> int:
    failures: list[str] = []
    for label, path in (
        ("industry hub", INDUSTRY_HUB),
        ("delivery index", DELIVERY_INDEX),
    ):
        if not path.is_file():
            failures.append(f"missing {label} at {path.relative_to(ROOT)}")
    for blog_dir in BLOG_DIRS:
        if (blog_dir / f"{RETIRED_SLUG}.md").is_file():
            failures.append(
                f"retired case study is back: {blog_dir.name}/{RETIRED_SLUG}.md"
            )
        for post in sorted(blog_dir.glob("*.md")):
            if "caseStudy: true" in post.read_text(encoding="utf-8"):
                failures.append(
                    f"{blog_dir.name}/{post.name}: caseStudy posts need a real, customer-approved result"
                )

    print("Case study guard (§1.3.4 · PV-G4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: no unverified case studies; industry surfaces present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
