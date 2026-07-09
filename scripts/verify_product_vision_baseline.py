#!/usr/bin/env python3
"""§1 Product Vision — automatable dev-layer baseline (positioning docs + glossary)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS: tuple[tuple[str, str, str], ...] = (
    ("1.1.1", "masterrule.md", "orchestration platform"),
    ("1.1.8", "BUSINESS_GLOSSARY.md", "post-payment the **Order** is the fulfillment aggregate"),
    ("1.1.9", "docs/ICP.md", "B2B last-mile orchestration software"),
    ("1.3.1", "docs/ICP.md", "Ideal Customer Profile"),
)


def main() -> int:
    failures: list[str] = []
    for item_id, rel, needle in CHECKS:
        path = ROOT / rel
        if not path.is_file():
            failures.append(f"§{item_id} missing {rel}")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            failures.append(f"§{item_id} {rel} missing {needle!r}")

    print("Product vision baseline guard (§1.1.1 · §1.1.8 · §1.1.9 · §1.3.1)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: canonical positioning + ICP + booking/order glossary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
