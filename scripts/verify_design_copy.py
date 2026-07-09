#!/usr/bin/env python3
"""Design copy ban-list gate (§6.1.2 · §6.1.3 · DES-G2).

Enforces docs/DESIGN_COPY_BAN_LIST.md against production marketing copy so the
platform never regresses into courier / gig-economy self-description.

Scope: website/messages/*.json (locale strings that render in prod). Legal
message files are excluded — legal-*.json may retain "commercial logistics
company" where required by counsel (per the ban-list doc).

Context-sensitive exceptions (rejected-misconception FAQ, employee careers
copy) are enumerated in REVIEWED_EXCEPTIONS with a rationale, matching the
"OK when describing customer pain" carve-outs in the ban-list doc.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "website/messages"

# Regex -> human label. Case-insensitive.
BANNED: dict[str, str] = {
    r"\blogistics company\b": 'self-description "logistics company"',
    r"\bcourier app\b": '"courier app" (consumer gig framing)',
    r"\bgig economy\b": '"gig economy"',
    r"\bside hustle\b": '"side hustle"',
    r"\bflexible hours\b": '"flexible hours" (gig framing)',
    r"\buber for\b": '"Uber for X" cliché',
    r"\b(best|cheapest) courier\b": "commodity courier comparison",
    r"\bwe deliver for you\b": '"we deliver for you" (implies we are the carrier)',
}

# (message file, term-substring, reason) — reviewed & accepted per ban-list carve-outs.
REVIEWED_EXCEPTIONS: tuple[tuple[str, str, str], ...] = (
    (
        "corporate-en.json",
        "is porterchain a courier app?",
        "Rejected-misconception FAQ — answer explicitly says 'No. Porterchain is a logistics technology platform'.",
    ),
    (
        "corporate-en.json",
        "flexible hours",
        "Employee careers benefit (Remote Friendly / Learning Budget block), not driver gig-economy framing.",
    ),
)


def _is_excepted(rel: str, line_lower: str) -> bool:
    return any(
        rel == ex_file and ex_term in line_lower for ex_file, ex_term, _ in REVIEWED_EXCEPTIONS
    )


def main() -> int:
    failures: list[str] = []
    files = sorted(p for p in MESSAGES.glob("*.json") if not p.name.startswith("legal-"))
    for path in files:
        rel = path.name
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            low = line.lower()
            for pattern, label in BANNED.items():
                if re.search(pattern, low):
                    if _is_excepted(rel, low):
                        continue
                    failures.append(f"{rel}:{lineno} — {label}: {line.strip()[:100]}")

    print("Design copy ban-list gate (§6.1.2 · DES-G2)")
    print(f"  scanned {len(files)} locale files; {len(REVIEWED_EXCEPTIONS)} reviewed exceptions")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("  PASS: zero un-reviewed ban-list terms in production copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
