#!/usr/bin/env python3
"""Appendix E.5 — INTEGRATIONS.md matches integrations.yaml registry."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INTEGRATIONS_MD = ROOT / "INTEGRATIONS.md"
INTEGRATIONS_YAML = ROOT / "integrations.yaml"

REQUIRED_YAML_KEYS = (
    "porterchain_api",
    "postgres",
    "redis",
    "fleetbase",
    "google_maps",
    "valhalla",
    "osrm",
    "stripe",
    "clerk",
    "merchant_api_keys",
    "merchant_webhooks",
    "oauth_third_party",
)

REQUIRED_MD_NEEDLES = (
    "integrations.yaml",
    "validate:integrations-matrix",
    "PostgreSQL 18",
    "OAuth third-party",
    "Merchant API keys",
)


def main() -> int:
    failures: list[str] = []

    if not INTEGRATIONS_MD.is_file():
        failures.append("missing INTEGRATIONS.md")
    if not INTEGRATIONS_YAML.is_file():
        failures.append("missing integrations.yaml")
        return 1

    registry = yaml.safe_load(INTEGRATIONS_YAML.read_text(encoding="utf-8")) or {}
    integrations = registry.get("integrations") or {}
    for key in REQUIRED_YAML_KEYS:
        if key not in integrations:
            failures.append(f"integrations.yaml missing {key}")

    md_text = INTEGRATIONS_MD.read_text(encoding="utf-8")
    for needle in REQUIRED_MD_NEEDLES:
        if needle not in md_text:
            failures.append(f"INTEGRATIONS.md missing {needle!r}")

    print("Integrations matrix guard (Appendix E.5)")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print(f"  PASS: {len(integrations)} integrations in yaml; INTEGRATIONS.md aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
