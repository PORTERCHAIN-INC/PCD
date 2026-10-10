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


def test_public_endpoints_are_rate_limited():
    for path in ("/v1/orders/PC-1", "/v1/quotes", "/v1/public/inquiries", "/v1/auth/staff/login"):
        assert any(path.startswith(p) for p in rl._PUBLIC_PREFIXES), path


class _Req:
    def __init__(self, peer, xff=None):
        self.client = type("C", (), {"host": peer})()
        self.headers = {"x-forwarded-for": xff} if xff else {}


def test_client_ip_ignores_spoofed_left_entries():
    from porterchain_api.platform.client_ip import client_ip, is_trusted_server

    assert client_ip(_Req("172.18.0.5", "1.2.3.4, 203.0.113.9")) == "203.0.113.9"
    assert client_ip(_Req("172.18.0.5", "203.0.113.9")) == "203.0.113.9"
    # Direct (non-proxy) peer: header ignored entirely.
    assert client_ip(_Req("8.8.4.4", "10.0.0.1")) == "8.8.4.4"
    assert is_trusted_server("172.18.0.1") and not is_trusted_server("8.8.4.4")


class _Redis:
    def __init__(self):
        self.d = {}

    def incr(self, k):
        self.d[k] = int(self.d.get(k, 0)) + 1
        return self.d[k]

    def expire(self, *a):
        return True

    def set(self, k, v, nx=False, ex=None):
        if nx and k in self.d:
            return False
        self.d[k] = v
        return True


def test_failed_login_alert_once_per_ip(monkeypatch):
    from porterchain_api.auth import staff_login_alerts as a

    r = _Redis()
    monkeypatch.setattr(a, "_redis", lambda: r)
    monkeypatch.setattr(a, "recipients", lambda db, s: ["owner@example.com"])
    sent = []
    results = [a.note_failed_login(None, None, client_ip="203.0.113.9", factor="passkey",
                                   send=lambda to, m: sent.append(to)) for _ in range(8)]
    assert results.count(True) == 1 and sent == ["owner@example.com"]


def test_admin_ip_allowlist(monkeypatch):
    from porterchain_api.platform import admin_ip_allowlist as al

    off = al.normalize_admin_access(None)
    assert off == {"ip_allowlist_enabled": False, "ip_allowlist": []}
    assert al.ip_allowed("8.8.8.8", off)
    on = al.normalize_admin_access({"ip_allowlist_enabled": True, "ip_allowlist": "203.0.113.0/24\n8.8.4.4"})
    assert al.ip_allowed("203.0.113.77", on) and al.ip_allowed("8.8.4.4", on)
    assert not al.ip_allowed("8.8.8.8", on)
    assert al.ip_allowed("8.8.8.8", {"ip_allowlist_enabled": True, "ip_allowlist": []})  # empty = off
    monkeypatch.setenv("ADMIN_IP_ALLOWLIST_BREAK_GLASS", "true")
    assert al.ip_allowed("8.8.8.8", on)
    with pytest.raises(ValueError):
        al.normalize_admin_access({"ip_allowlist": ["not-an-ip"]})


def test_staff_session_timeouts():
    from porterchain_api.auth import staff_session as ss

    assert ss.DEFAULT_TTL_SECONDS == 30 * 60 and ss.ABSOLUTE_MAX_SECONDS == 12 * 3600


def test_offboarding_revokes_clerk_sessions(monkeypatch):
    from porterchain_api.admin_engine import driver_service as ds
    from porterchain_api.auth import clerk_registry

    calls = []

    class _C:
        def revoke_sessions(self, uid):
            calls.append(uid)
            return 2

    monkeypatch.setattr(clerk_registry, "clerk_client_for_kind", lambda s, k: _C())
    d = type("D", (), {"id": "d1", "clerk_user_id": "user_x"})()
    ds.revoke_driver_sessions(d, object())
    assert calls == ["user_x"]
    ds.revoke_driver_sessions(type("D", (), {"id": "d2", "clerk_user_id": None})(), object())
    assert calls == ["user_x"]
