import pytest

from porterchain_api.platform.outbound_url import UnsafeUrl, assert_public_https_url
from porterchain_api.platform import rate_limit_middleware as rl


@pytest.mark.parametrize("url", [
    "http://example.com/hook", "https://127.0.0.1/x", "https://169.254.169.254/metadata/v1/",
    "https://10.0.0.5/h", "https://pcd-redis:6379/", "https://redis/", "https://user:pw@example.com/",
    "https://example.com:6379/", "https://[::1]/", "https://100.64.1.1/", "https://foo.internal/",
])
def test_rejects_unsafe_webhook_urls(url):
    with pytest.raises(UnsafeUrl):
        assert_public_https_url(url, resolve=False)


def test_accepts_public_https():
    assert assert_public_https_url("https://hooks.example.com/pc", resolve=False)
    assert assert_public_https_url("https://8.8.8.8/x", resolve=False)


def test_public_tracking_is_rate_limited():
    assert any("/v1/orders/PC-1".startswith(p) for p in rl._PREFIXES)
