"""Export the FastAPI OpenAPI schema to docs/api/openapi.json.

Keeps the partner-facing OpenAPI snapshot in sync with the live route surface.
Live truth remains `/openapi.json` + `/docs`; this file is a committed snapshot
for Postman import and offline diligence review.

Run: `pnpm docs:openapi`
"""

from __future__ import annotations

import json
from pathlib import Path

from porterchain_api.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT = REPO_ROOT / "docs" / "api" / "openapi.json"


def main() -> None:
    spec = app.openapi()
    OUT.write_text(json.dumps(spec, indent=2, sort_keys=False) + "\n")
    print(f"Wrote {OUT.relative_to(REPO_ROOT)} — {len(spec.get('paths', {}))} paths")


if __name__ == "__main__":
    main()
