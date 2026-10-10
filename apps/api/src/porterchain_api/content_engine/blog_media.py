"""Blog media uploads — local disk + optional S3/R2 mirror + CDN public URLs."""

from __future__ import annotations

import os
import re
import uuid
from pathlib import Path

from porterchain_api.content_engine.blog_media_s3 import put_blog_media_object

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


def blog_media_public_base() -> str:
    """CDN or site origin for media URLs. Empty → relative API path."""
    raw = os.environ.get("BLOG_MEDIA_PUBLIC_BASE_URL", "").strip()
    if not raw:
        try:
            from porterchain_api.config import get_settings

            raw = (get_settings().blog_media_public_base_url or "").strip()
        except Exception:
            raw = ""
    return raw.rstrip("/")


def public_media_path(filename: str) -> str:
    """
    Public URL for a media object.
    When CDN base is set and S3 prefix is used, prefer {cdn}/{prefix}/{filename}.
    Else {cdn}/v1/public/blog/media/{filename} or relative API path.
    """
    base = blog_media_public_base()
    prefix = os.environ.get("BLOG_MEDIA_S3_PREFIX", "").strip().strip("/")
    if not prefix:
        try:
            from porterchain_api.config import get_settings

            prefix = (get_settings().blog_media_s3_prefix or "").strip().strip("/")
        except Exception:
            prefix = ""
    if not prefix:
        prefix = "blog-media"

    # Absolute CDN object path when object storage is configured (or CDN fronts that keyspace).
    s3_on = bool(
        os.environ.get("BLOG_MEDIA_S3_ENDPOINT", "").strip()
        or os.environ.get("BLOG_MEDIA_S3_BUCKET", "").strip()
    )
    if not s3_on:
        try:
            from porterchain_api.config import get_settings

            s = get_settings()
            s3_on = bool((s.blog_media_s3_endpoint or "").strip() and (s.blog_media_s3_bucket or "").strip())
        except Exception:
            s3_on = False

    if base and s3_on:
        return f"{base}/{prefix}/{filename}"

    rel = f"/v1/public/blog/media/{filename}"
    if base:
        return f"{base}{rel}"
    return rel


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
    head = content[:12]
    magic = {".jpg": head[:3] == b"\xff\xd8\xff", ".jpeg": head[:3] == b"\xff\xd8\xff",
             ".png": head[:8] == b"\x89PNG\r\n\x1a\n", ".gif": head[:6] in (b"GIF87a", b"GIF89a"),
             ".webp": head[:4] == b"RIFF" and head[8:12] == b"WEBP"}
    if not magic.get(ext, False):  # real bytes must match the extension (no SVG/HTML)
        raise ValueError("blog_media_invalid_type")
    safe = f"{uuid.uuid4().hex}{ext}"
    if not _SAFE_NAME.match(safe):
        raise ValueError("blog_media_invalid_name")
    dest = blog_media_dir() / safe
    dest.write_bytes(content)
    ctype = content_type or f"image/{ext.lstrip('.')}"
    # Best-effort mirror to R2/S3 when credentials exist; disk remains source of truth for local.
    put_blog_media_object(filename=safe, content=content, content_type=ctype)
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
