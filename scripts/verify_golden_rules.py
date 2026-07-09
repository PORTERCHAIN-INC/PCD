#!/usr/bin/env python3
"""FND-G4 — masterrule §20 golden rules (§0.3) enforced in CI where automatable."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github/workflows/ci.yml"
PACKAGE = ROOT / "package.json"
MASTER = ROOT / "masterrule.md"
CONTRIBUTING = ROOT / "CONTRIBUTING_GUIDE.md"
CHANGELOG = ROOT / "docs/api/CHANGELOG.md"
CHECKLIST = ROOT / "docs/SILICON_VALLEY_READINESS_CHECKLIST.md"

# §0.3 ID → (description, CI script or file evidence)
_GOLDEN_RULE_CI: tuple[tuple[str, str, str], ...] = (
    ("0.3.2", "No Fleetbase bypass (UI)", "validate:architecture"),
    ("0.3.3", "Business logic in services", "validate:router-audit"),
    ("0.3.6", "Engine modularity LOC", "validate:d2"),
    ("0.3.8", "One customer surface", "validate:d2"),
    ("0.3.9", "Thin routers", "validate:router-audit"),
    ("0.3.10", "No upward engine imports", "validate:d2"),
    ("0.3.4", "Fleetbase upstream-clean", "apps/fleetbase absent or vendor-only"),
    ("0.3.5", "Refactor over rewrite", "CONTRIBUTING_GUIDE.md"),
    ("0.3.7", "API changelog", "docs/api/CHANGELOG.md"),
    ("0.3.11", "Docs follow code", "Appendix C"),
    ("0.3.12", "Essential complexity", "FORBIDDEN_PATHS"),
)

_DOC_RULES: tuple[tuple[str, str], ...] = (
    ("0.3.1", "Locked topology"),
    ("0.3.4", "Fleetbase upstream-clean"),
)


def _ci_text() -> str:
    parts = []
    if CI.is_file():
        parts.append(CI.read_text(encoding="utf-8", errors="ignore"))
    if PACKAGE.is_file():
        parts.append(PACKAGE.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def main() -> int:
    failures: list[str] = []
    ci_text = _ci_text()

    for rule_id, _desc, script in _GOLDEN_RULE_CI:
        if script.startswith("validate:"):
            if script not in ci_text:
                failures.append(f"§{rule_id} {script} not in CI/package.json")
        elif script == "CONTRIBUTING_GUIDE.md":
            if not CONTRIBUTING.is_file():
                failures.append("§0.3.5 missing CONTRIBUTING_GUIDE.md")
            elif "Refactor over rewrite" not in CONTRIBUTING.read_text(encoding="utf-8", errors="ignore"):
                failures.append("§0.3.5 CONTRIBUTING_GUIDE missing refactor policy")
        elif script == "docs/api/CHANGELOG.md":
            if not CHANGELOG.is_file():
                failures.append("§0.3.7 missing docs/api/CHANGELOG.md")
        elif script == "Appendix C":
            if not CHECKLIST.is_file() or "## Appendix C" not in CHECKLIST.read_text(encoding="utf-8", errors="ignore"):
                failures.append("§0.3.11 checklist missing Appendix C")
        elif script == "FORBIDDEN_PATHS":
            if "validate:d2" not in ci_text:
                failures.append("§0.3.12 validate:d2 not in CI")
        elif "apps/fleetbase" in script:
            fleetbase = ROOT / "apps/fleetbase"
            if fleetbase.is_dir():
                for py in fleetbase.rglob("*.py"):
                    text = py.read_text(encoding="utf-8", errors="ignore")
                    if "porterchain_api" in text or "booking_engine" in text:
                        rel = py.relative_to(ROOT)
                        failures.append(f"§0.3.4 Porterchain logic in vendor tree: {rel}")
                        break

    if not MASTER.is_file():
        failures.append("§0.3.1 missing masterrule.md")
    elif "## 20. Golden rules" not in MASTER.read_text(encoding="utf-8", errors="ignore"):
        failures.append("§0.3.1 masterrule.md missing §20 golden rules")

    d2_script = ROOT / "apps/api/scripts/verify_d2_contracts.py"
    if d2_script.is_file():
        d2 = d2_script.read_text(encoding="utf-8", errors="ignore")
        if "FORBIDDEN_PATHS" not in d2:
            failures.append("§0.3.12 verify_d2_contracts missing FORBIDDEN_PATHS")
    else:
        failures.append("§0.3.12 missing verify_d2_contracts.py")

    if "validate:golden-rules" not in ci_text:
        failures.append("FND-G4 validate:golden-rules not wired in CI")

    if failures:
        print("Golden rules CI guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"Golden rules CI guard passed (FND-G4 — {len(_GOLDEN_RULE_CI)} automatable §0.3 rules in CI).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
