#!/usr/bin/env python3
"""§4.1.5 · AI-G2 — No false AI claims in public marketing copy."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "website/messages"

BANNED_PATTERNS = (
    re.compile(r"AI-powered", re.I),
    re.compile(r"artificial intelligence", re.I),
    re.compile(r"machine learning", re.I),
    re.compile(r"ML-powered", re.I),
    re.compile(r"GPT[- ]powered", re.I),
    re.compile(r"LLM[- ]powered", re.I),
    re.compile(r"optimisé par IA", re.I),
    re.compile(r"alimenté par l'IA", re.I),
)


def _walk_strings(value: object, path: str, hits: list[str]) -> None:
    if isinstance(value, str):
        for pattern in BANNED_PATTERNS:
            if pattern.search(value):
                hits.append(f"{path}: {value[:80]!r}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _walk_strings(child, f"{path}.{key}" if path else key, hits)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            _walk_strings(child, f"{path}[{idx}]", hits)


def main() -> int:
    failures: list[str] = []

    for path in sorted(MESSAGES.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append(f"{path.name} invalid JSON: {exc}")
            continue
        hits: list[str] = []
        _walk_strings(data, path.name, hits)
        failures.extend(hits)

    print("No false AI marketing guard (§4.1.5 · AI-G2)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: website messages free of banned AI marketing claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
