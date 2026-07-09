#!/usr/bin/env python3
"""Mobile design system parity guard (§6.3.7)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TOKENS = ROOT / "packages/mobile-theme/src/tokens.ts"
WEB_COLORS = ROOT / "apps/admin/src/app/globals.css"

APPS = (
    ("customer", ROOT / "apps/mobile-customer"),
    ("driver", ROOT / "apps/mobile-driver"),
)

REQUIRED_TOKENS = ("#0a1628", "#2563eb", "#f0f4f8", "touchTargetMin")


def main() -> int:
    failures: list[str] = []

    if not TOKENS.is_file():
        failures.append("missing packages/mobile-theme/src/tokens.ts")
    else:
        token_text = TOKENS.read_text(encoding="utf-8")
        for needle in REQUIRED_TOKENS:
            if needle not in token_text:
                failures.append(f"tokens.ts missing {needle!r}")

    if WEB_COLORS.is_file():
        web = WEB_COLORS.read_text(encoding="utf-8")
        for hex_val in ("#0a1628", "#2563eb", "#f0f4f8"):
            if hex_val not in web:
                failures.append(f"web globals missing {hex_val} for parity check")
            elif TOKENS.is_file() and hex_val not in TOKENS.read_text(encoding="utf-8"):
                failures.append(f"mobile tokens missing web color {hex_val}")

    for name, app_dir in APPS:
        pkg = app_dir / "package.json"
        app_tsx = app_dir / "App.tsx"
        if not pkg.is_file() or "@porterchain/mobile-theme" not in pkg.read_text(encoding="utf-8"):
            failures.append(f"{name}: missing @porterchain/mobile-theme dependency")
        if not app_tsx.is_file() or "@porterchain/mobile-theme" not in app_tsx.read_text(encoding="utf-8"):
            failures.append(f"{name}: App.tsx must import @porterchain/mobile-theme")
        if app_tsx.is_file() and "touchTargetMin" not in app_tsx.read_text(encoding="utf-8"):
            failures.append(f"{name}: App.tsx must use touchTargetMin (44pt targets)")

    print("Mobile design parity (§6.3.7)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: @porterchain/mobile-theme tokens match web + wired in both apps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
