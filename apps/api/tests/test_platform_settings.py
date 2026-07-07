"""Platform settings tests."""

import os
from unittest import mock

from porterchain_shared.config.settings import PlatformSettings


def test_is_local_property() -> None:
    assert PlatformSettings(app_env="local").is_local is True
    assert PlatformSettings(app_env="production").is_local is False


def test_cors_origin_list() -> None:
    settings = PlatformSettings(cors_origins="http://a.com, http://b.com")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]


def test_google_maps_api_key_accepts_server_alias() -> None:
    # Production templates/Doppler use GOOGLE_MAPS_SERVER_API_KEY for the API.
    with mock.patch.dict(os.environ, {"GOOGLE_MAPS_SERVER_API_KEY": "server-key-123"}, clear=False):
        settings = PlatformSettings(_env_file=None)
    assert settings.google_maps_api_key == "server-key-123"


def test_google_maps_api_key_prefers_canonical_name() -> None:
    env = {"GOOGLE_MAPS_API_KEY": "canonical", "GOOGLE_MAPS_SERVER_API_KEY": "server"}
    with mock.patch.dict(os.environ, env, clear=False):
        settings = PlatformSettings(_env_file=None)
    assert settings.google_maps_api_key == "canonical"
