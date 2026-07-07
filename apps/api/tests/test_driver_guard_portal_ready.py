"""Regression: driver `guard_portal_ready` must delegate to the mapper, not recurse.

A previous version redefined ``guard_portal_ready`` in ``routers/driver/_deps.py``
so it called itself, causing ``RecursionError`` on every driver dashboard/jobs
request. These tests pin the wrapper to the mapper implementation and its
PermissionError -> HTTP 403 translation.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from porterchain_api.routers.driver import _deps


def test_guard_portal_ready_is_not_self_recursive() -> None:
    assert _deps.guard_portal_ready is not _deps._mapper_guard_portal_ready


def test_guard_portal_ready_passes_when_mapper_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_deps, "_mapper_guard_portal_ready", lambda ctx, settings: None)
    # Should not raise (and must not recurse).
    _deps.guard_portal_ready(ctx=object(), settings=object())


def test_guard_portal_ready_maps_permission_error_to_403(monkeypatch: pytest.MonkeyPatch) -> None:
    def _deny(ctx, settings):
        raise PermissionError("driver_not_onboarded")

    monkeypatch.setattr(_deps, "_mapper_guard_portal_ready", _deny)

    with pytest.raises(HTTPException) as exc_info:
        _deps.guard_portal_ready(ctx=object(), settings=object())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "driver_not_onboarded"
