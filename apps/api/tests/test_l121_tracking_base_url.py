"""L121: tracking base URL configurable per environment."""
from porterchain_api.config import Settings, public_url_errors
from porterchain_api.merchant_engine.shopify_fulfillment_ops import public_tracking_url


def test_falls_back_to_website_url():
    s = Settings(website_url="https://porterchain.ca/", public_tracking_base_url="")
    assert public_tracking_url(s, "PC-1") == "https://porterchain.ca/track/PC-1"


def test_uses_public_tracking_base_when_set():
    s = Settings(website_url="http://192.168.2.103:53005", public_tracking_base_url="https://track.porterchain.ca/")
    assert public_tracking_url(s, "PC-1") == "https://track.porterchain.ca/track/PC-1"


def test_loopback_tracking_base_rejected_outside_local():
    s = Settings().model_copy(update={"app_env": "production", "public_tracking_base_url": "http://localhost:3000"})
    assert any(e.startswith("PUBLIC_TRACKING_BASE_URL") for e in public_url_errors(s))
