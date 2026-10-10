"""Shared spam guard for public website forms (same rules as the calculator).

* Honeypot field (``website``) must stay empty.
* The form must have been open for at least ``min_fill_seconds``.
* Per-IP fixed-window rate limit (bucket per form family).

Spam gets the same success answer as a real submission and creates nothing.
"""

from __future__ import annotations

import logging

from fastapi import Request
from sqlalchemy.orm import Session

from porterchain_api.marketing_site.config import get_marketing_site
from porterchain_api.marketing_site.rate_limit import client_ip, enforce_public_limit

logger = logging.getLogger(__name__)


def looks_like_bot(*, honeypot: str | None, form_elapsed_ms: int | None, min_fill_seconds: int) -> bool:
    if (honeypot or "").strip():
        return True
    if form_elapsed_ms is not None and form_elapsed_ms < max(0, min_fill_seconds) * 1000:
        return True
    return False


def guard_public_form(
    request: Request,
    db: Session,
    *,
    bucket: str,
    app_env: str,
    honeypot: str | None,
    form_elapsed_ms: int | None,
) -> bool:
    """Rate-limit (raises 429) and return True when the submission is spam."""
    cfg = get_marketing_site(db)["calculator"]
    enforce_public_limit(
        request, bucket=bucket, limit=int(cfg["leads_per_minute"]), app_env=app_env
    )
    spam = looks_like_bot(
        honeypot=honeypot,
        form_elapsed_ms=form_elapsed_ms,
        min_fill_seconds=int(cfg["min_fill_seconds"]),
    )
    if spam:
        logger.info("public form dropped (spam signal) bucket=%s", bucket)
    return spam


__all__ = ["client_ip", "guard_public_form", "looks_like_bot"]
