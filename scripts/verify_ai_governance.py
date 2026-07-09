#!/usr/bin/env python3
"""§4.3.1–4.3.2 · AI-G2/G4 — AI governance docs and marketing honesty."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MASTERRULE = ROOT / "masterrule.md"
MODEL_CARDS = ROOT / "docs/ai/MODEL_CARDS.md"
INTEL_PKG = ROOT / "apps/api/src/porterchain_api/intelligence_engine/__init__.py"
ADR_016 = ROOT / "docs/architecture/ADR-016-no-llm-pricing-routing.md"
FALSE_AI_SCRIPT = ROOT / "scripts/verify_no_false_ai_marketing.py"


def main() -> int:
    failures: list[str] = []

    if not MASTERRULE.is_file():
        failures.append("missing masterrule.md")
    else:
        text = MASTERRULE.read_text(encoding="utf-8")
        if "intelligence_engine/" not in text:
            failures.append("masterrule §6 missing intelligence_engine/")
        if "ADR-016" not in text and "No LLM" not in text:
            failures.append("masterrule missing Phase 2 intelligence / LLM boundary note")

    for path in (MODEL_CARDS, INTEL_PKG, ADR_016, FALSE_AI_SCRIPT):
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")

    if MODEL_CARDS.is_file():
        cards = MODEL_CARDS.read_text(encoding="utf-8")
        for needle in ("Valhalla", "Phase 2", "ADR-016", "Pay path"):
            if needle not in cards:
                failures.append(f"MODEL_CARDS.md missing {needle!r}")

    print("AI governance guard (§4.3.1–4.3.2 · AI-G2/G4)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: intelligence_engine in masterrule, model cards, ADR-016, marketing guard present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
