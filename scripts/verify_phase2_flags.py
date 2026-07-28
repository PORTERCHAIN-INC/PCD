#!/usr/bin/env python3
"""§1.2.4 · DD-26 — Phase 2 feature flags default off."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "shared/python"))

PHASE2_PY = ROOT / "shared/python/porterchain_shared/config/phase2.py"
PHASE2_MJS = ROOT / "packages/config/phase2.mjs"
API_CONFIG = ROOT / "apps/api/src/porterchain_api/config.py"
ENV_EXAMPLE = ROOT / "apps/api/.env.example"
ADR_010 = ROOT / "docs/architecture/ADR-010-phase2-strategies.md"
ADR_014 = ROOT / "docs/architecture/ADR-014-phase2-feature-flags.md"

FLAG_NAMES = (
    "PORTERCHAIN_PHASE2_CRM",
    "PORTERCHAIN_PHASE2_ROUTE_CENTER",
    "PORTERCHAIN_PHASE2_AI_DISPATCH",
    "PORTERCHAIN_PHASE2_ANALYTICS",
    "PORTERCHAIN_PHASE2_INTELLIGENCE",
)


def main() -> int:
    failures: list[str] = []

    for path in (PHASE2_PY, PHASE2_MJS, API_CONFIG, ADR_010, ADR_014):
        if not path.is_file():
            failures.append(f"missing {path.relative_to(ROOT)}")

    if API_CONFIG.is_file():
        text = API_CONFIG.read_text(encoding="utf-8")
        for flag in FLAG_NAMES:
            if flag not in text:
                failures.append(f"config.py missing {flag}")
        if "phase2_flags" not in text:
            failures.append("config.py missing phase2_flags property")

    if ENV_EXAMPLE.is_file():
        env_text = ENV_EXAMPLE.read_text(encoding="utf-8")
        if "PORTERCHAIN_PHASE2_CRM=false" not in env_text:
            failures.append(".env.example missing PORTERCHAIN_PHASE2_CRM=false")

    if PHASE2_PY.is_file():
        from porterchain_shared.config.phase2 import Phase2Flags

        if Phase2Flags().any_enabled():
            failures.append("Phase2Flags defaults must all be false")

    print("Phase 2 feature flags guard (§1.2.4 · DD-26)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: PORTERCHAIN_PHASE2_* flags defined and default off")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
