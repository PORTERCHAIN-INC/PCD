"""P0 skeletons — keep SSOT IDs visible until filled.

Flip registry status to ``implemented`` and move/replace with a real assert.
"""

from __future__ import annotations

import pytest

from . import cases

_SKELETONS = cases(runner="pytest", status="skeleton")


@pytest.mark.merchant_p0
@pytest.mark.parametrize(
    "case_id",
    [c["id"] for c in _SKELETONS],
    ids=[c["id"] for c in _SKELETONS],
)
def test_merchant_p0_pytest_skeleton(case_id: str) -> None:
    row = next(c for c in _SKELETONS if c["id"] == case_id)
    pytest.skip(f"{case_id}: skeleton — {row['title']}")
