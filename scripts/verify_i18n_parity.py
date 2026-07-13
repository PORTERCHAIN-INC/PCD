#!/usr/bin/env python3
"""§6.1.5 — FR/EN locale message parity on marketing site."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MESSAGES = ROOT / "website/messages"

_PAIRS: tuple[tuple[str, str], ...] = (
    ("corporate-en.json", "corporate-fr.json"),
    ("site-footer-en.json", "site-footer-fr.json"),
    ("business-en.json", "business-fr.json"),
    ("blog-en.json", "blog-fr.json"),
    ("vehicle-partner-en.json", "vehicle-partner-fr.json"),
)

# Root marketing namespaces checked separately until full fr.json parity ships.
_ROOT_NAMESPACE_PAIRS: tuple[tuple[str, str], ...] = (
    ("cityLocalSegment", "cityLocalSegment"),
    ("cityIndustryDelivery.industryLabels", "cityIndustryDelivery.industryLabels"),
    ("cityIndustryDelivery.areaLabels", "cityIndustryDelivery.areaLabels"),
)

# Common FR leakage markers in en.json landing namespaces (regression guard).
_EN_LANDING_NAMESPACES = ("nicheLanding", "campaignLanding")
_FR_LEAK_MARKERS = (
    "livraison",
    "matériaux",
    "chantier",
    "prêt pour",
    "nous joindre",
    "contactez-nous",
    "décrivez vos",
    "partagez vos",
)


def _check_en_root_landing_locale_purity() -> list[str]:
    en_path = MESSAGES / "en.json"
    if not en_path.is_file():
        return ["§6.1.5 missing en.json for landing locale purity check"]
    en = json.loads(en_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for namespace in _EN_LANDING_NAMESPACES:
        bucket = en.get(namespace)
        if not isinstance(bucket, dict):
            continue
        for message_key, content in bucket.items():
            if not isinstance(content, dict):
                continue
            blob = json.dumps(content, ensure_ascii=False).lower()
            for marker in _FR_LEAK_MARKERS:
                if marker in blob:
                    failures.append(
                        f"§6.1.5 en.json {namespace}.{message_key} contains French marker {marker!r}"
                    )
                    break
    return failures


def _flatten_keys(obj: object, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            keys.add(path)
            keys.update(_flatten_keys(value, path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            keys.update(_flatten_keys(item, f"{prefix}[{idx}]"))
    return keys


def _get_nested(obj: object, dotted_path: str) -> object | None:
    current: object | None = obj
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _check_full_root_parity() -> list[str]:
    en_path = MESSAGES / "en.json"
    fr_path = MESSAGES / "fr.json"
    if not en_path.is_file() or not fr_path.is_file():
        return ["§6.1.5 missing en.json / fr.json for full root parity"]
    en = json.loads(en_path.read_text(encoding="utf-8"))
    fr = json.loads(fr_path.read_text(encoding="utf-8"))
    en_keys = _flatten_keys(en)
    fr_keys = _flatten_keys(fr)
    failures: list[str] = []
    missing_fr = sorted(en_keys - fr_keys)
    if missing_fr:
        failures.append(
            f"§6.1.5 fr.json missing {len(missing_fr)} root keys (e.g. {missing_fr[:3]})"
        )
    return failures


def _check_root_namespace_parity() -> list[str]:
    en_path = MESSAGES / "en.json"
    fr_path = MESSAGES / "fr.json"
    if not en_path.is_file() or not fr_path.is_file():
        return ["§6.1.5 missing en.json / fr.json for root namespace parity"]
    en = json.loads(en_path.read_text(encoding="utf-8"))
    fr = json.loads(fr_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for en_path_key, fr_path_key in _ROOT_NAMESPACE_PAIRS:
        en_obj = _get_nested(en, en_path_key)
        fr_obj = _get_nested(fr, fr_path_key)
        if en_obj is None:
            continue
        if fr_obj is None:
            failures.append(f"§6.1.5 fr.json missing root namespace {fr_path_key}")
            continue
        en_keys = _flatten_keys(en_obj)
        fr_keys = _flatten_keys(fr_obj)
        missing_fr = sorted(en_keys - fr_keys)
        if missing_fr:
            failures.append(
                f"§6.1.5 fr.json {fr_path_key} missing {len(missing_fr)} keys (e.g. {missing_fr[:3]})"
            )
    return failures


_EXPECTED_PROGRAMMATIC_SLUGS: dict[str, tuple[str, ...]] = {
    "compare": (
        "in-house-delivery",
        "ad-hoc-courier",
        "unmanaged-same-day",
        "spreadsheet-dispatch",
    ),
    "faq": (
        "construction-delivery",
        "electrical-distributor-delivery",
        "plumbing-supply-delivery",
        "delivery-pricing",
        "onboarding",
        "csv-uploads",
        "api-integrations",
        "local-service-areas",
        "pharmacy-delivery",
        "coffee-roaster-delivery",
        "cosmetics-delivery",
        "same-day-delivery",
        "how-much-does-local-delivery-cost-toronto",
        "how-to-set-up-recurring-deliveries-coffee-roaster",
        "how-pharmacy-courier-delivery-works-gta",
        "how-to-onboard-merchant-csv-upload",
        "what-vehicle-right-for-parcel-volume",
        "same-day-retail-distribution",
        "fleet-overflow-wholesale-delivery",
    ),
    "guides": (
        "delivery-operations-model",
        "merchant-onboarding-guide",
        "route-and-tracking-overview",
        "support-and-issue-handling",
    ),
    "successStories": (
        "construction-distributor-jobsite-delivery",
        "coffee-roaster-wholesale-delivery",
        "pharmacy-patient-delivery",
        "beauty-brand-d2c-fulfillment",
    ),
}


def _check_programmatic_fr_slug_parity() -> list[str]:
    path = MESSAGES / "seo-programmatic-fr.json"
    if not path.is_file():
        return ["§6.1.5 missing website/messages/seo-programmatic-fr.json"]
    data = json.loads(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for hub in ("compare", "faq", "guides", "successStories"):
        if hub not in data.get("hubs", {}):
            failures.append(f"§6.1.5 seo-programmatic-fr.json missing hubs.{hub}")
    for namespace, expected in _EXPECTED_PROGRAMMATIC_SLUGS.items():
        bucket = data.get(namespace)
        if not isinstance(bucket, dict):
            failures.append(f"§6.1.5 seo-programmatic-fr.json missing namespace {namespace}")
            continue
        got = set(bucket.keys())
        want = set(expected)
        missing = sorted(want - got)
        extra = sorted(got - want)
        if missing:
            failures.append(
                f"§6.1.5 seo-programmatic-fr {namespace} missing slugs: {missing[:5]}"
                + (f" (+{len(missing) - 5} more)" if len(missing) > 5 else "")
            )
        if extra:
            failures.append(f"§6.1.5 seo-programmatic-fr {namespace} unexpected slugs: {extra[:5]}")
    return failures


def main() -> int:
    failures: list[str] = []

    for en_name, fr_name in _PAIRS:
        en_path = MESSAGES / en_name
        fr_path = MESSAGES / fr_name
        if not en_path.is_file() or not fr_path.is_file():
            failures.append(f"§6.1.5 missing locale pair {en_name} / {fr_name}")
            continue
        en_keys = _flatten_keys(json.loads(en_path.read_text(encoding="utf-8")))
        fr_keys = _flatten_keys(json.loads(fr_path.read_text(encoding="utf-8")))
        missing_fr = sorted(en_keys - fr_keys)
        missing_en = sorted(fr_keys - en_keys)
        if missing_fr:
            failures.append(f"§6.1.5 {fr_name} missing {len(missing_fr)} keys (e.g. {missing_fr[:3]})")
        if missing_en:
            failures.append(f"§6.1.5 {en_name} missing {len(missing_en)} keys (e.g. {missing_en[:3]})")

    failures.extend(_check_full_root_parity())
    failures.extend(_check_root_namespace_parity())
    failures.extend(_check_en_root_landing_locale_purity())
    failures.extend(_check_programmatic_fr_slug_parity())

    if failures:
        print("i18n parity guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        f"i18n parity guard passed (§6.1.5 — {len(_PAIRS)} EN/FR locale pairs + full en/fr.json root parity)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
