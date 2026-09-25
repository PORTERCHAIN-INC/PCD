"""Notify the website to revalidate blog pages after admin mutations."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from porterchain_api.config import Settings

logger = logging.getLogger(__name__)


def notify_blog_revalidate(
    settings: Settings,
    *,
    locale: str | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    """POST website /api/revalidate/blog. No-op when secret unset."""
    secret = (settings.website_revalidate_secret or "").strip()
    if not secret:
        return {"ok": False, "skipped": "revalidate_secret_unset"}

    base = (settings.website_url or "").rstrip("/")
    if not base:
        return {"ok": False, "skipped": "website_url_unset"}

    payload: dict[str, str] = {}
    if locale:
        payload["locale"] = locale.strip().lower()
    if slug:
        payload["slug"] = slug.strip().lower()

    url = f"{base}/api/revalidate/blog"
    try:
        with httpx.Client(timeout=8.0) as client:
            res = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {secret}",
                    "Content-Type": "application/json",
                },
            )
        if res.status_code >= 400:
            logger.warning(
                "blog_revalidate_failed status=%s body=%s",
                res.status_code,
                res.text[:300],
            )
            return {"ok": False, "status": res.status_code}
        data = res.json() if res.content else {}
        return {"ok": True, "status": res.status_code, "response": data}
    except httpx.HTTPError as exc:
        logger.warning("blog_revalidate_error: %s", exc)
        return {"ok": False, "error": str(exc)}
