"""Production must refuse the local auth bypass (Keycloak is the only provider)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from porterchain_api.config import Settings


def test_production_rejects_dev_bypass() -> None:
    with pytest.raises((ValueError, ValidationError)) as exc:
        Settings(_env_file=None, app_env="production", auth_dev_bypass=True, jwt_secret="a" * 32)  # type: ignore[call-arg]
    assert "AUTH_DEV_BYPASS" in str(exc.value)
