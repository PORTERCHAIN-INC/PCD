"""P0 skeletons — parametrize unimplemented pytest-runner cases so IDs stay visible.

Fill a body, flip registry status to ``implemented``, and move the case into
``test_*_implemented.py`` (or keep it here with a real assert).
"""

from __future__ import annotations

import pytest

from . import cases

_SKELETONS = cases(runner="pytest", status="skeleton")


@pytest.mark.admin_p0
@pytest.mark.parametrize(
    "case_id",
    [c["id"] for c in _SKELETONS],
    ids=[c["id"] for c in _SKELETONS],
)
def test_p0_pytest_skeleton(case_id: str) -> None:
    """Placeholder — replace with a real assert and mark registry status=implemented."""
    row = next(c for c in _SKELETONS if c["id"] == case_id)
    pytest.skip(f"{case_id}: skeleton — {row['title']}")
