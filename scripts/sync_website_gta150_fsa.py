#!/usr/bin/env python3
"""Write website/src/lib/seo/gta150FsaCodes.ts from porterchain_pricing.gta150_fsa_codes().

SoT is services/pricing-engine/porterchain_pricing/data/gta150_fsa_registry.json
plus the downtown hub overrides in gta150_fsa.py. Do not hand-edit the TS file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "website" / "src" / "lib" / "seo" / "gta150FsaCodes.ts"
sys.path.insert(0, str(ROOT / "services" / "pricing-engine"))

from porterchain_pricing.components.fsa import ONTARIO_FSA_PREFIXES  # noqa: E402
from porterchain_pricing.gta150_fsa import gta150_fsa_codes, gta150_registry_meta  # noqa: E402


def main() -> int:
    codes = sorted(gta150_fsa_codes())
    meta = gta150_registry_meta()
    hubs = ", ".join(meta.get("hub_overrides") or [])
    ontario = sorted(ONTARIO_FSA_PREFIXES)
    out = [
        "/**",
        " * Generated from porterchain_pricing.gta150_fsa_codes() — do not hand-edit.",
        f" * Registry version={meta.get('version')} count={len(codes)}"
        + (f" hub_overrides={hubs}" if hubs else "")
        + ".",
        " * Regenerate: python scripts/sync_website_gta150_fsa.py",
        " * CI: python scripts/verify_gta150_fsa_sync.py",
        " */",
        "export const GTA150_FSA_CODES = new Set<string>([",
        *[f'  "{code}",' for code in codes],
        "]);",
        "",
        "export function isGta150Fsa(fsa: string): boolean {",
        "  return GTA150_FSA_CODES.has(fsa.trim().toUpperCase().slice(0, 3));",
        "}",
        "",
        "export const ONTARIO_FSA_PREFIXES = new Set<string>(["
        + ", ".join(f'"{c}"' for c in ontario)
        + "]);",
        "",
        "export function isOntarioFsa(fsa: string): boolean {",
        "  const first = fsa.trim().toUpperCase().charAt(0);",
        "  return ONTARIO_FSA_PREFIXES.has(first);",
        "}",
        "",
    ]
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} count={len(codes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
