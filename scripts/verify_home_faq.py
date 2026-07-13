#!/usr/bin/env python3
"""Root FAQ guard — playbook §4.2 B2B set; bans consumer-courier drift."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "website/messages"

PLAYBOOK_FAQ_QUESTIONS_EN = (
    "Do you offer same-day delivery in Toronto and the GTA?",
    "Can you handle emergency delivery when our driver is unavailable?",
    "What is intra-city logistics and do you provide it?",
    "Do you provide quick or express delivery for businesses?",
    "What areas do you serve?",
    "What vehicles are available?",
    "Is proof of delivery included?",
    "How does pricing work?",
)

BANNED_CONSUMER = (
    re.compile(r"\binstant quote tool\b", re.I),
    re.compile(r"\bfurniture delivery\b", re.I),
    re.compile(r"\bmarketplace purchases\b", re.I),
    re.compile(r"\bmobile app\b", re.I),
    re.compile(r"\bpersonal deliveries\b", re.I),
    re.compile(r"\bbooked within minutes\b", re.I),
    re.compile(r"\bmeubles\b", re.I),
    re.compile(r"\bapplication (client|mobile)\b", re.I),
    re.compile(r"\boutil de devis instantané\b", re.I),
)


def main() -> int:
    failures: list[str] = []

    for name in ("en.json", "fr.json"):
        data = json.loads((MESSAGES / name).read_text(encoding="utf-8"))
        faq = data.get("faq", {})
        items = faq.get("items", [])
        if not isinstance(items, list):
            failures.append(f"{name}: faq.items must be an array")
            continue

        if len(items) != 8:
            failures.append(f"{name}: faq.items expected 8 playbook questions, got {len(items)}")

        for item in items:
            if not isinstance(item, dict):
                continue
            text = f"{item.get('question', '')} {item.get('answer', '')}"
            for pattern in BANNED_CONSUMER:
                if pattern.search(text):
                    failures.append(f"{name}: consumer FAQ drift: {text[:80]!r}")

        if name == "en.json":
            questions = [item.get("question") for item in items if isinstance(item, dict)]
            for expected in PLAYBOOK_FAQ_QUESTIONS_EN:
                if expected not in questions:
                    failures.append(f"{name}: missing playbook FAQ question: {expected!r}")

        subtitle = faq.get("subtitle", "")
        if name == "en.json" and "businesses evaluating" not in subtitle.lower():
            failures.append(f"{name}: faq.subtitle should target B2B evaluators")

    print("Home FAQ guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: root en/fr.json FAQ is playbook B2B set (8 questions, no consumer drift)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
