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

    failures.extend(_check_en_root_landing_locale_purity())

    if failures:
        print("i18n parity guard failed:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(f"i18n parity guard passed (§6.1.5 — {len(_PAIRS)} EN/FR locale pairs).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
