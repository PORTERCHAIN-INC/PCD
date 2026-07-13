#!/usr/bin/env python3
"""Programmatic EN body guard — top compare/FAQ slugs meet B2B depth + playbook phrases."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "website/src/lib/seo/content"

_TOP_COMPARE = (
    "in-house-delivery",
    "ad-hoc-courier",
    "unmanaged-same-day",
    "spreadsheet-dispatch",
)
_TOP_FAQ = (
    "construction-delivery",
    "electrical-distributor-delivery",
    "plumbing-supply-delivery",
    "delivery-pricing",
    "onboarding",
    "csv-uploads",
    "api-integrations",
    "local-service-areas",
)

_MIN_COMPARE_INTRO = 280
_MIN_FAQ_INTRO = 180
_MIN_FAQ_ANSWER = 80
_FORBIDDEN = ("cargo bike", "cargo bikes")

_REQUIRED_PHRASES: dict[str, tuple[str, ...]] = {
    "delivery-pricing": ("Quote-based", "platform fee"),
    "construction-delivery": ("job",),  # jobsite / job site
    "onboarding": ("days",),
    "api-integrations": ("API",),
}


def _extract_slug_blocks(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    blocks: dict[str, str] = {}
    parts = re.split(r'slug:\s*"([^"]+)"', text)
    for i in range(1, len(parts), 2):
        blocks[parts[i]] = parts[i + 1]
    return blocks


def _field(block: str, name: str) -> str:
    m = re.search(rf'{name}:\s*\n?\s*"((?:[^"\\]|\\.)*)"', block, re.S)
    return m.group(1).replace("\\n", "\n") if m else ""


def _faq_answers(block: str) -> list[str]:
    return re.findall(r'answer:\s*\n?\s*"((?:[^"\\]|\\.)*)"', block, re.S)


def _comparison_rows(block: str) -> int:
    return len(re.findall(r"dimension:\s*\"", block))


def main() -> int:
    failures: list[str] = []

    compare_path = CONTENT / "comparison-pages.ts"
    faq_path = CONTENT / "faq-clusters.ts"

    for path in (compare_path, faq_path):
        blob = path.read_text(encoding="utf-8").lower()
        for term in _FORBIDDEN:
            if term in blob:
                failures.append(f"{path.name} contains forbidden consumer term {term!r}")

    compare_blocks = _extract_slug_blocks(compare_path)
    faq_blocks = _extract_slug_blocks(faq_path)

    for slug in _TOP_COMPARE:
        block = compare_blocks.get(slug)
        if not block:
            failures.append(f"compare missing slug: {slug}")
            continue
        intro = _field(block, "intro")
        rows = _comparison_rows(block)
        if len(intro) < _MIN_COMPARE_INTRO:
            failures.append(f"compare/{slug} intro too short ({len(intro)} < {_MIN_COMPARE_INTRO})")
        if rows < 4:
            failures.append(f"compare/{slug} needs 4 comparison rows, got {rows}")

    for slug in _TOP_FAQ:
        block = faq_blocks.get(slug)
        if not block:
            failures.append(f"faq missing slug: {slug}")
            continue
        intro = _field(block, "intro")
        answers = _faq_answers(block)
        if len(intro) < _MIN_FAQ_INTRO:
            failures.append(f"faq/{slug} intro too short ({len(intro)} < {_MIN_FAQ_INTRO})")
        if len(answers) < 4:
            failures.append(f"faq/{slug} needs 4 FAQ answers, got {len(answers)}")
        for idx, ans in enumerate(answers):
            if len(ans) < _MIN_FAQ_ANSWER:
                failures.append(
                    f"faq/{slug} answer[{idx}] too short ({len(ans)} < {_MIN_FAQ_ANSWER})"
                )
        blob = f"{intro} {' '.join(answers)}"
        for phrase in _REQUIRED_PHRASES.get(slug, ()):
            if phrase.lower() not in blob.lower():
                failures.append(f"faq/{slug} missing playbook phrase: {phrase!r}")

    print("Programmatic EN playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print(f"  PASS: {_TOP_COMPARE.__len__()} compare + {_TOP_FAQ.__len__()} FAQ slugs meet B2B depth bar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
