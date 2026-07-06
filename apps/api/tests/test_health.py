"""Health probe tests."""

from unittest.mock import MagicMock, patch

from porterchain_api.config import Settings
from porterchain_api.platform.health import liveness, readiness


def test_liveness_ok() -> None:
    assert liveness() == {"status": "ok", "service": "porterchain-api"}


def test_readiness_local_without_redis() -> None:
    db = MagicMock()
    db.execute.return_value = None
    settings = Settings(app_env="local")
    with patch("porterchain_api.platform.health.ping_redis", return_value=False):
        with patch("porterchain_api.platform.health._routing_health", return_value="ok"):
            with patch(
                "porterchain_api.auth.clerk_registry.clerk_health_checks",
                return_value={"customer": "ok", "merchant": "ok", "admin": "ok", "driver": "ok"},
            ):
                with patch(
                    "porterchain_api.auth.clerk_registry.clerk_configuration_mode",
                    return_value="enterprise",
                ):
                    result = readiness(db, settings)
    assert result["status"] in ("ok", "degraded")
    assert result["checks"]["database"] == "ok"
    assert result["checks"]["routing"] == "ok"


def test_routing_health_unconfigured() -> None:
    from porterchain_api.platform.health import _routing_health

    with patch("porterchain_shared.config.settings.get_platform_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            routing_engine="valhalla", valhalla_url="", osrm_url=""
        )
        assert _routing_health() == "unconfigured"
