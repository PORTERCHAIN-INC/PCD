"""Zapier template catalog loader (§7.2.4)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
TEMPLATES_PATH = ROOT / "integrations" / "zapier" / "templates.json"


@lru_cache(maxsize=1)
def load_zapier_templates() -> dict[str, Any]:
    if not TEMPLATES_PATH.is_file():
        return {"version": "1.0.0", "templates": []}
    return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))


def zapier_catalog() -> dict[str, Any]:
    data = load_zapier_templates()
    return {
        "publisher": data.get("publisher", "porterchain"),
        "version": data.get("version", "1.0.0"),
        "templates": data.get("templates") or [],
        "template_count": len(data.get("templates") or []),
        "docs_path": "integrations/zapier/README.md",
    }
