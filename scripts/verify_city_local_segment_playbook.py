#!/usr/bin/env python3
"""City×vehicle/intent local segment guard — bilingual templates, no EN leakage on FR."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = ROOT / "website/messages/en.json"
FR = ROOT / "website/messages/fr.json"
LOCAL_SEGMENT_TS = ROOT / "website/src/lib/seo/city-local-segment-content.ts"

_REQUIRED_TOP = (
    "vehicleLabels",
    "intentLabels",
    "cta",
    "coverage",
    "inquiry",
    "operationalFit",
    "vehicle",
    "intent",
)

_REQUIRED_BLOCK = (
    ("meta", "titlePattern"),
    ("meta", "descriptionPattern"),
    ("hero", "titlePattern"),
    ("hero", "subtitlePattern"),
    ("faq", "q4"),
    ("faq", "a4"),
)

_FR_MARKERS_IN_EN = ("Obtenir un devis", "Opérations locales", "Démarrer {")


def _get_nested(obj: object, path: tuple[str, ...]) -> object | None:
    cur: object | None = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def _check_locale_block(
    locale: str, block: dict | None, prefix: str, failures: list[str]
) -> None:
    if not isinstance(block, dict):
        failures.append(f"{locale} cityLocalSegment.{prefix} missing")
        return
    for path in _REQUIRED_BLOCK:
        if _get_nested(block, path) in (None, ""):
            failures.append(f"{locale} cityLocalSegment.{prefix} missing {'.'.join(path)}")


def main() -> int:
    failures: list[str] = []

    ts = LOCAL_SEGMENT_TS.read_text(encoding="utf-8")
    for needle in ('"Get a quote"', '"Contact us"', '"How it works"', '"Get started"'):
        if needle in ts:
            failures.append(f"city-local-segment-content.ts still hard-codes {needle}")

    en = json.loads(EN.read_text(encoding="utf-8"))
    fr = json.loads(FR.read_text(encoding="utf-8"))
    en_seg = en.get("cityLocalSegment")
    fr_seg = fr.get("cityLocalSegment")

    for key in _REQUIRED_TOP:
        if not isinstance(en_seg, dict) or key not in en_seg:
            failures.append(f"en cityLocalSegment missing {key}")
        if not isinstance(fr_seg, dict) or key not in fr_seg:
            failures.append(f"fr cityLocalSegment missing {key}")

    if isinstance(en_seg, dict):
        for marker in _FR_MARKERS_IN_EN:
            blob = json.dumps(en_seg, ensure_ascii=False)
            if marker in blob:
                failures.append(f"en cityLocalSegment contains FR marker {marker!r}")

    if isinstance(en_seg, dict):
        _check_locale_block("en", en_seg.get("vehicle"), "vehicle", failures)
        _check_locale_block("en", en_seg.get("intent"), "intent", failures)
        for field in ("titlePattern", "descriptionPattern"):
            if not en_seg.get("coverage", {}).get(field):
                failures.append(f"en cityLocalSegment.coverage missing {field}")
            if not en_seg.get("inquiry", {}).get("headingPattern"):
                failures.append("en cityLocalSegment.inquiry missing headingPattern")

    if isinstance(fr_seg, dict):
        _check_locale_block("fr", fr_seg.get("vehicle"), "vehicle", failures)
        _check_locale_block("fr", fr_seg.get("intent"), "intent", failures)
        for field in ("titlePattern", "descriptionPattern"):
            if not fr_seg.get("coverage", {}).get(field):
                failures.append(f"fr cityLocalSegment.coverage missing {field}")
            if not fr_seg.get("inquiry", {}).get("headingPattern"):
                failures.append("fr cityLocalSegment.inquiry missing headingPattern")
        if fr_seg.get("cta", {}).get("primary") == "Get a quote":
            failures.append("fr cityLocalSegment.cta.primary still English")

    print("City local segment playbook guard")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: city×vehicle/intent templates localized EN+FR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
