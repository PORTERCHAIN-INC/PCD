"""Integration health must reflect PORTERCHAIN_PHASE2_CUOPT_SHADOW.

Bug: build_integration_health read ``settings.phase2_flags["cuopt_shadow"]``,
a key Phase2Flags.as_dict() never emits, so nvidia_cuopt always reported
"disabled" even with the shadow flag on.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from porterchain_api.admin_engine.integration_health import build_integration_health
from porterchain_api.config import Settings

_READY = {"status": "ok", "checks": {"database": "ok", "redis": "ok", "stripe": "ok"}}


@pytest.mark.parametrize(("enabled", "raw"), [(True, "shadow"), (False, "disabled")])
def test_cuopt_shadow_flag_drives_integration_health(enabled: bool, raw: str) -> None:
    settings = Settings(app_env="local", phase2_cuopt_shadow=enabled)
    health = build_integration_health(
        MagicMock(), settings, ready=_READY, nvidia_nim_configured=False
    )
    assert health["nvidia_cuopt"]["raw"] == raw
    assert health["nvidia_cuopt"]["phase2_cuopt_shadow"] is enabled
