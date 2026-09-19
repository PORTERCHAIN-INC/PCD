"""Shared list pagination limits and page envelopes."""

from __future__ import annotations

from typing import Any, TypeVar

DEFAULT_LIST_LIMIT = 100
DEFAULT_PAGE_SIZE = 50
MAX_LIST_LIMIT = 500
MAX_EMBEDDED_LIST_LIMIT = 100

T = TypeVar("T")


def clamp_page(
    limit: int | None,
    offset: int | None,
    *,
    default: int = DEFAULT_PAGE_SIZE,
    max_limit: int = MAX_LIST_LIMIT,
) -> tuple[int, int]:
    size = default if limit is None else int(limit)
    size = max(1, min(size, max_limit))
    start = 0 if offset is None else max(0, int(offset))
    return size, start


def as_page(items: list[T], total: int, limit: int, offset: int) -> dict[str, Any]:
    return {"items": items, "total": int(total), "limit": limit, "offset": offset}
