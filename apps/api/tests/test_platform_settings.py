"""Platform settings tests."""

from porterchain_shared.config.settings import PlatformSettings


def test_is_local_property() -> None:
    assert PlatformSettings(app_env="local").is_local is True
    assert PlatformSettings(app_env="production").is_local is False


def test_cors_origin_list() -> None:
    settings = PlatformSettings(cors_origins="http://a.com, http://b.com")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]
