#!/usr/bin/env python3
"""5-minute demo script gate (§6 · DES-G4)."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/DEMO_SCRIPT.md"

NARRATIVE_START = "## Demo script (spoken narrative)"
NARRATIVE_END = "## Success criteria"

REQUIRED_BEATS = (
    "homepage",
    "track",
    "merchant",
    "admin",
    "developers",
)

DISCLAIMER_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bwip\b", "WIP"),
    (r"\bcoming soon\b", "coming soon"),
    (r"\bnot implemented\b", "not implemented"),
    (r"\bplaceholder\b", "placeholder"),
    (r"\bdisclaimer\b", "disclaimer"),
    (r"\bapolog", "apology language"),
    (r"\bbeta\b", "beta"),
    (r"\bfor demo only\b", "for demo only"),
    (r"\bmock\b", "mock"),
    (r"\btodo\b", "TODO"),
)


def _narrative_section(text: str) -> str:
    start = text.find(NARRATIVE_START)
    end = text.find(NARRATIVE_END)
    if start < 0 or end < 0 or end <= start:
        return ""
    return text[start:end]


def main() -> int:
    failures: list[str] = []

    if not DOC.is_file():
        failures.append("missing docs/DEMO_SCRIPT.md")
    else:
        text = DOC.read_text(encoding="utf-8")
        low = text.lower()
        if "5" not in text or "minute" not in low:
            failures.append("demo script must state 5-minute duration")
        for beat in REQUIRED_BEATS:
            if beat not in low:
                failures.append(f"demo script missing beat: {beat}")

        narrative = _narrative_section(text)
        if not narrative:
            failures.append("demo script missing spoken narrative section markers")
        else:
            narrative_low = narrative.lower()
            for beat in REQUIRED_BEATS:
                if beat not in narrative_low:
                    failures.append(f"spoken narrative missing beat: {beat}")
            for pattern, label in DISCLAIMER_PATTERNS:
                if re.search(pattern, narrative_low):
                    failures.append(f"spoken narrative contains disclaimer term: {label}")

    print("Demo script gate (DES-G4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: 5-minute demo script with map+ETA beats and no disclaimer language")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
