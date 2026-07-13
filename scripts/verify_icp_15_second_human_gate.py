#!/usr/bin/env python3
"""ICP 15-second human gate — automated copy audit for 3 personas × 3 URLs × 6 dims."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "docs/ICP_15_SECOND_TEST_LOG.md"

PERSONAS = (
    {
        "id": "construction",
        "label": "Construction ops manager (building supply / GC)",
        "niche_key": "constructionMaterials",
        "industry_slug": "construction-materials",
    },
    {
        "id": "pharmacy",
        "label": "Pharmacy ops lead (independent / regional chain)",
        "niche_key": "pharmacyMedical",
        "industry_slug": "pharmacy-medical",
    },
    {
        "id": "electrical",
        "label": "Electrical wholesale ops (counter + jobsite lanes)",
        "niche_key": "electricalDistribution",
        "industry_slug": "electrical-distribution",
    },
)

DIMENSIONS = ("what", "when", "where", "trust", "next", "price")

MARKERS: dict[str, tuple[str, ...]] = {
    "what": (
        r"vehicle",
        r"driver",
        r"capacity",
        r"courier",
        r"delivery",
        r"transportation",
        r"capacité",
        r"chauffeur",
        r"livraison",
    ),
    "when": (
        r"fleet",
        r"overflow",
        r"urgent",
        r"emergency",
        r"same-day",
        r"same day",
        r"can't cover",
        r"cannot cover",
        r"driver",
        r"backup",
        r"flotte",
        r"urgence",
        r"jour même",
    ),
    "where": (
        r"gta",
        r"greater toronto",
        r"ontario",
        r"toronto",
        r"peel",
        r"york",
        r"durham",
        r"rgt",
        r"ontario",
    ),
    "trust": (
        r"proof",
        r"tracking",
        r"chain-of-custody",
        r"chain of custody",
        r"photo",
        r"signature",
        r"preuve",
        r"suivi",
    ),
    "next": (r"get a quote", r"obtenir un devis", r"request a quote", r"quote"),
    "price": (
        r"quote-based",
        r"written quote",
        r"no platform fees",
        r"sur devis",
        r"sans frais",
        r"quote by",
    ),
}


@dataclass
class PageCopy:
    route: str
    above_fold: str
    primary_cta: str


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _join(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def _hero_block(corporate: dict, business: dict, niche: dict | None, route: str) -> PageCopy:
    if route == "/":
        hero = corporate["home"]["hero"]
        above = _join(
            hero.get("badge"),
            hero.get("title"),
            hero.get("titleHighlight"),
            hero.get("subtitle"),
            hero.get("trustLine"),
            hero.get("trustProof"),
            hero.get("trustAreas"),
        )
        return PageCopy(route, above, hero.get("primaryCta", ""))
    if route == "/business":
        hero = business["hero"]
        above = _join(
            hero.get("badge"),
            hero.get("titleLine1"),
            hero.get("titleLine2"),
            hero.get("subtitle"),
        )
        return PageCopy(route, above, hero.get("ctaPrimary", ""))
    if niche:
        hero = niche.get("hero", {})
        cta = niche.get("cta", {})
        above = _join(hero.get("title"), hero.get("subtitle"))
        return PageCopy(route, above, cta.get("primary", ""))
    raise ValueError(f"unknown route {route}")


def _score_dimension(text: str, dimension: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in MARKERS[dimension])


def _score_page(page: PageCopy) -> dict[str, bool]:
    blob = f"{page.above_fold} {page.primary_cta}"
    return {dim: _score_dimension(blob, dim) for dim in DIMENSIONS}


def _format_log(results: list[dict]) -> str:
    today = date.today().isoformat()
    lines = [
        "# ICP 15-second test log",
        "",
        f"**Date:** {today}  ",
        "**Gate:** Wave 8 A+ · `docs/ICP.md` §15-second test  ",
        "**Method:** Automated above-fold copy audit (`verify_icp_15_second_human_gate.py`) + founder visual sign-off",
        "",
        "## Rubric (6 dimensions ≥4/5 equivalent — all must pass)",
        "",
        "| Dimension | Pass bar |",
        "| --------- | -------- |",
        "| What | Vehicle + driver capacity (not software SKU) |",
        "| When | Fleet overflow / urgent / can't cover shipment |",
        "| Where | GTA or Ontario metros named |",
        "| Trust | Proof or tracking language (no fake metrics) |",
        "| Next | Get a quote primary CTA |",
        "| Price | Quote-based / no platform fees |",
        "",
        "## Persona results (3 URLs each)",
        "",
    ]

    persona_pass = 0
    for persona in results:
        all_pass = all(cell["pass"] for cell in persona["cells"])
        if all_pass:
            persona_pass += 1
        lines.append(f"### {persona['label']} — **{'PASS' if all_pass else 'FAIL'}**")
        lines.append("")
        lines.append("| URL | What | When | Where | Trust | Next | Price | Result |")
        lines.append("| --- | ---- | ---- | ----- | ----- | ---- | ----- | ------ |")
        for cell in persona["cells"]:
            dims = cell["dims"]
            row_pass = all(dims.values())
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{cell['route']}`",
                        "✓" if dims["what"] else "✗",
                        "✓" if dims["when"] else "✗",
                        "✓" if dims["where"] else "✗",
                        "✓" if dims["trust"] else "✗",
                        "✓" if dims["next"] else "✗",
                        "✓" if dims["price"] else "✗",
                        "PASS" if row_pass else "FAIL",
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(
        [
            "## Summary",
            "",
            f"- **Automated persona pass:** {persona_pass}/3",
            f"- **Exit gate (ICP.md):** {'PASS' if persona_pass == 3 else 'FAIL'} — construction + pharmacy + electrical ops buyers",
            "",
            "## Human sign-off",
            "",
            "- [ ] Founder / ops visual check on live localhost or staging (15s timer, no scrolling on home)",
            "- [ ] Record tester name + date below after live check",
            "",
            "**Live tester:** _pending_  ",
            "**Live date:** _pending_  ",
            "",
            "---",
            "",
            "_Generated by `scripts/verify_icp_15_second_human_gate.py`. Re-run after hero or niche copy changes._",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    corporate = _load_json(ROOT / "website/messages/corporate-en.json")
    business = _load_json(ROOT / "website/messages/business-en.json")
    root = _load_json(ROOT / "website/messages/en.json")
    niches = root.get("nicheLanding", {})

    failures: list[str] = []
    results: list[dict] = []

    for persona in PERSONAS:
        niche = niches.get(persona["niche_key"])
        if not niche:
            failures.append(f"missing nicheLanding.{persona['niche_key']}")
            continue

        cells = []
        for route in ("/", "/business", f"/industry/{persona['industry_slug']}"):
            page = _hero_block(
                corporate,
                business,
                niche if route.startswith("/industry/") else None,
                route if not route.startswith("/industry/") else "/industry/[slug]",
            )
            if route.startswith("/industry/"):
                page = PageCopy(route, page.above_fold, page.primary_cta)
            dims = _score_page(page)
            cell_pass = all(dims.values())
            if not cell_pass:
                missing = [dim for dim, ok in dims.items() if not ok]
                failures.append(
                    f"{persona['id']} {route}: missing dimensions {', '.join(missing)}"
                )
            cells.append({"route": route, "dims": dims, "pass": cell_pass})
        results.append({"label": persona["label"], "cells": cells})

    LOG_PATH.write_text(_format_log(results), encoding="utf-8")

    print("ICP 15-second human gate")
    persona_pass = sum(1 for p in results if all(c["pass"] for c in p["cells"]))
    print(f"  Automated persona pass: {persona_pass}/3")
    print(f"  Log written: {LOG_PATH.relative_to(ROOT)}")
    if failures:
        for item in failures:
            print(f"  FAIL: {item}")
        return 1
    print("  PASS: all 3 ICP personas pass automated 15-second copy audit")
    print("  HUMAN: complete live visual sign-off in docs/ICP_15_SECOND_TEST_LOG.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
