"""Redis health helper tests."""

from porterchain_shared.redis_health import is_local_env


def test_local_env_aliases() -> None:
    assert is_local_env("local") is True
    assert is_local_env("development") is True
    assert is_local_env("production") is False
