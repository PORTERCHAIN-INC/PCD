#!/usr/bin/env python3
"""Fail if high-visibility FR keys still match EN (leakage)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMESPACES = ("serviceAreasIndex", "nicheLanding", "campaignLanding")
MUST_DIFF = [
    ("serviceAreasIndex", "faq", "items", "0", "q"),
    ("nicheLanding", "electricalDistribution", "painPoints", "item1"),
    ("nicheLanding", "plumbingSupply", "painPoints", "item1"),
    ("campaignLanding", "electricalDistribution", "painPoints", "item1"),
    ("campaignLanding", "plumbingSupply", "painPoints", "item1"),
]


def _get(d: dict, path: tuple[str, ...]):
    cur: object = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def _identical_long(en_ns: object, fr_ns: object) -> list[str]:
    hits: list[str] = []

    def walk(e, f, path: str) -> None:
        if type(e) != type(f):
            return
        if isinstance(e, dict):
            for k in e:
                if k in f:
                    walk(e[k], f[k], f"{path}.{k}" if path else k)
        elif isinstance(e, list):
            for i, (a, b) in enumerate(zip(e, f)):
                walk(a, b, f"{path}[{i}]")
        elif isinstance(e, str) and e == f and len(e) > 40:
            hits.append(path)

    walk(en_ns, fr_ns, "")
    return hits


def main() -> int:
    en = json.loads((ROOT / "website/messages/en.json").read_text(encoding="utf-8"))
    fr = json.loads((ROOT / "website/messages/fr.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    for path in MUST_DIFF:
        ev, fv = _get(en, path), _get(fr, path)
        if ev is None or fv is None:
            failures.append(f"missing path {'.'.join(path)}")
        elif ev == fv:
            failures.append(f"FR still equals EN: {'.'.join(path)}")

    identical: list[str] = []
    for ns in NAMESPACES:
        if ns in en and ns in fr:
            identical.extend(f"{ns}{p}" if p.startswith(".") or p.startswith("[") else f"{ns}.{p}" if p else ns for p in _identical_long(en[ns], fr[ns]))

    print("FR←EN leakage guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    if identical:
        for item in identical[:20]:
            print(f"  FAIL: identical long string {item}")
        if len(identical) > 20:
            print(f"  FAIL: … and {len(identical) - 20} more")
        return 1
    print("  PASS: critical FR paths + niche/campaign/service-areas long strings translated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
