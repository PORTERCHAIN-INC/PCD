"""Pytest fixtures for admin_p0 suite."""

from __future__ import annotations

import pytest

from . import case_by_id


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "admin_p0: Admin/SuperAdmin P0 suite")
    config.addinivalue_line("markers", "tc_id(id): SSOT test-case ID from docs/testing/admin_p0_registry.json")


@pytest.fixture
def tc(request: pytest.FixtureRequest) -> dict:
    """Resolve the tc_id marker on the test into the registry row."""
    marker = request.node.get_closest_marker("tc_id")
    if marker is None:
        pytest.fail("admin_p0 tests must declare @pytest.mark.tc_id('CASE-ID')")
    case_id = marker.args[0]
    return case_by_id(case_id)
