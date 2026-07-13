#!/usr/bin/env python3
"""Marketing claim registry — banned absolute/regulatory claims in public website copy."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "website/messages"

# Paths where negation / disclaimer context is expected (still scanned; patterns must not match there).
ALLOWLIST_SUBSTRINGS = (
    "vehicle-partner-en.json",
    "vehicle-partner-fr.json",
    "legal-en.json",
    "legal-fr.json",
)

BANNED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "HIPAA absolute claim",
        re.compile(r"\bHIPAA[- ]?(compliant|certified|aware)\b", re.I),
    ),
    (
        "Uber comparison",
        re.compile(r"\bUber[- ]?like\b|\blike Uber\b", re.I),
    ),
    (
        "DoorDash comparison",
        re.compile(r"\bDoorDash\b", re.I),
    ),
    (
        "Guaranteed capacity/delivery",
        re.compile(
            r"\bguaranteed\s+(capacity|delivery|vehicle|same[- ]day|on[- ]time)\b",
            re.I,
        ),
    ),
    (
        "Native integration SKU claim",
        re.compile(r"\bNative integrations?\b", re.I),
    ),
    (
        "Dispatch software product SKU",
        re.compile(
            r"\b(our|the|a)\s+dispatch\s+(software|platform)\b|\bsell\s+dispatch\s+software\b",
            re.I,
        ),
    ),
    (
        "Logistics operating system (careers drift)",
        re.compile(r"\boperating system for commercial logistics\b", re.I),
    ),
    (
        "Platform-as-SKU niche copy",
        re.compile(
            r"\bone platform, one partner\b|\bune plateforme, un partenaire\b"
            r"|\byour logistics platform\b|\bvotre plateforme logistique\b"
            r"|\ba logistics platform\b|\bune plateforme logistique\b",
            re.I,
        ),
    ),
    (
        "Logistics technology company claim",
        re.compile(r"\bmost trusted logistics technology company\b", re.I),
    ),
)


def _walk_strings(value: object, path: str, hits: list[str]) -> None:
    if isinstance(value, str):
        for label, pattern in BANNED_PATTERNS:
            if pattern.search(value):
                hits.append(f"{path}: [{label}] {value[:100]!r}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _walk_strings(child, f"{path}.{key}" if path else key, hits)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _walk_strings(child, f"{path}[{idx}]", hits)


def main() -> int:
    failures: list[str] = []

    for path in sorted(MESSAGES.glob("*.json")):
        if any(token in path.name for token in ALLOWLIST_SUBSTRINGS):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name} invalid JSON: {exc}")
            continue
        hits: list[str] = []
        _walk_strings(data, path.name, hits)
        failures.extend(hits)

    print("Marketing claim registry guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: no banned marketing claims in website/messages/*.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
