"""Blog media uploads — local disk store served via the public blog media route."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")
_FALLBACK_EXT = frozenset({".jpg", ".jpeg", ".png", ".webp", ".gif"})
_FALLBACK_MAX_BYTES = 5 * 1024 * 1024


def blog_media_dir() -> Path:
    raw = os.environ.get("BLOG_MEDIA_DIR", "").strip()
    if raw:
        path = Path(raw)
    else:
        # apps/api/data/blog-media. This package sits at the same depth as the old location.
        path = Path(__file__).resolve().parents[3] / "data" / "blog-media"
    path.mkdir(parents=True, exist_ok=True)
    return path


def public_media_path(filename: str) -> str:
    return f"/v1/public/blog/media/{filename}"


def save_blog_image(
    *,
    filename: str,
    content: bytes,
    content_type: str | None,
    max_bytes: int | None = None,
    allowed_ext: frozenset[str] | None = None,
) -> str:
    limit = _FALLBACK_MAX_BYTES if max_bytes is None else max_bytes
    exts = _FALLBACK_EXT if allowed_ext is None else allowed_ext
    if len(content) > limit:
        raise ValueError("blog_media_too_large")
    ext = Path(filename).suffix.lower()
    if ext not in exts:
        raise ValueError("blog_media_invalid_type")
    if content_type and not content_type.startswith("image/"):
        raise ValueError("blog_media_invalid_type")
    safe = f"{uuid.uuid4().hex}{ext}"
    if not _SAFE_NAME.match(safe):
        raise ValueError("blog_media_invalid_name")
    dest = blog_media_dir() / safe
    dest.write_bytes(content)
    return public_media_path(safe)


def resolve_media_file(filename: str) -> Path | None:
    if not _SAFE_NAME.match(filename):
        return None
    path = blog_media_dir() / filename
    if not path.is_file():
        return None
    try:
        path.resolve().relative_to(blog_media_dir().resolve())
    except ValueError:
        return None
    return path
