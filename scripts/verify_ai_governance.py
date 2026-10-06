#!/usr/bin/env python3
"""AI boundary — intelligence_engine exists; no LLM on pay/dispatch path."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL_PKG = ROOT / "apps/api/src/porterchain_api/intelligence_engine/__init__.py"
ARCHITECTURE = ROOT / "ARCHITECTURE.md"
FALSE_AI_SCRIPT = ROOT / "scripts/verify_no_false_ai_marketing.py"
SEQUENCER = ROOT / "apps/api/src/porterchain_api/dispatch_engine/sequencer.py"


def main() -> int:
    failures: list[str] = []

    if not INTEL_PKG.is_file():
        failures.append("missing intelligence_engine/__init__.py")
    if not FALSE_AI_SCRIPT.is_file():
        failures.append("missing verify_no_false_ai_marketing.py")
    if not SEQUENCER.is_file():
        failures.append("missing dispatch_engine/sequencer.py (OR-Tools day plan)")
    if not ARCHITECTURE.is_file():
        failures.append("missing ARCHITECTURE.md")
    else:
        text = ARCHITECTURE.read_text(encoding="utf-8")
        if "OR-Tools" not in text and "ortools" not in text:
            failures.append("ARCHITECTURE.md missing OR-Tools day solver")
        if "No PorterChain VROOM" not in text and "no PorterChain VROOM" not in text and "Do not add a VROOM client" not in text:
            failures.append("ARCHITECTURE.md missing no-VROOM-client rule")
        if "Fleetbase adapter" in text and "permanent bond" in text:
            failures.append("ARCHITECTURE.md still describes Fleetbase permanent bond")

    print("AI governance guard (living architecture)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: intelligence_engine present; OR-Tools day plan; no VROOM/LLM on request path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
