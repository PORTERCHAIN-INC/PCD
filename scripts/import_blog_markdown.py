#!/usr/bin/env python3
"""One-time import: website/content/blog markdown → blog_posts table."""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api/src"))

from porterchain_api.content_engine.blog_service import BlogService
from porterchain_api.db import SessionLocal

BLOG_ROOT = ROOT / "website/content/blog"
_service = BlogService()
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_simple_yaml(block: str) -> dict[str, str | bool | list[str]]:
    out: dict[str, str | bool | list[str]] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        key = key.strip()
        value = raw.strip().strip('"').strip("'")
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            out[key] = [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
        elif value.lower() == "true":
            out[key] = True
        elif value.lower() == "false":
            out[key] = False
        else:
            out[key] = value
    return out


def _parse_md(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(raw)
    data: dict = {}
    body = raw
    if match:
        data = _parse_simple_yaml(match.group(1))
        body = raw[match.end() :]
    return {
        "title": str(data.get("title") or path.stem),
        "description": str(data.get("description") or ""),
        "body_md": body.strip(),
        "category": str(data.get("category") or "logistics"),
        "author_id": str(data.get("author") or "porterchain"),
        "featured": bool(data.get("featured")),
        "trending": bool(data.get("trending")),
        "case_study": bool(data.get("caseStudy")),
        "on_time_percent": data.get("onTimePercent") if isinstance(data.get("onTimePercent"), str) else None,
        "cost_delta_percent": data.get("costDeltaPercent")
        if isinstance(data.get("costDeltaPercent"), str)
        else None,
        "volume_metric": data.get("volumeMetric") if isinstance(data.get("volumeMetric"), str) else None,
        "tags": data.get("tags") if isinstance(data.get("tags"), list) else [],
        "published_at": date.fromisoformat(str(data["date"])) if data.get("date") else None,
    }


def main() -> int:
    imported = 0
    skipped = 0
    with SessionLocal() as db:
        for locale in ("en", "fr"):
            dir_path = BLOG_ROOT / locale
            if not dir_path.is_dir():
                continue
            for md in sorted(dir_path.glob("*.md")):
                slug = md.stem
                existing = _service.get_by_locale_slug(db, locale=locale, slug=slug)
                if existing:
                    skipped += 1
                    continue
                try:
                    payload = _parse_md(md)
                    _service.create_post(
                        db,
                        slug=slug,
                        locale=locale,
                        status="published",
                        created_by=None,
                        **payload,
                    )
                    imported += 1
                    print(f"  imported {locale}/{slug}")
                except ValueError as exc:
                    print(f"  skip {locale}/{slug}: {exc}")
                    skipped += 1
    print(f"Done — imported {imported}, skipped {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
