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
        result = readiness(db, settings)
    assert result["status"] in ("ok", "degraded")
    assert result["checks"]["database"] == "ok"
