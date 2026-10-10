"""SSRF guard for user-supplied outbound URLs (merchant webhooks).

Only public https endpoints: no loopback, private, link-local (cloud metadata
169.254.169.254), CGNAT, multicast or reserved addresses, no internal docker
hostnames, no credentials in the URL. Checked at registration and again at
delivery time (DNS can change).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeUrl(ValueError):
    pass


def _bad_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast
            or ip.is_reserved or ip.is_unspecified
            or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10")))


def assert_public_https_url(url: str, *, resolve: bool = True) -> str:
    parts = urlsplit((url or "").strip())
    if parts.scheme != "https":
        raise UnsafeUrl("webhook_url_must_be_https")
    if parts.username or parts.password:
        raise UnsafeUrl("webhook_url_credentials_not_allowed")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host or "." not in host or host.endswith((".local", ".internal", ".localhost")):
        raise UnsafeUrl("webhook_url_host_not_public")
    if parts.port not in (None, 443, 8443):
        raise UnsafeUrl("webhook_url_port_not_allowed")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _bad_ip(literal):
            raise UnsafeUrl("webhook_url_host_not_public")
        return url
    if resolve:
        try:
            infos = socket.getaddrinfo(host, parts.port or 443, proto=socket.IPPROTO_TCP)
        except OSError as exc:
            raise UnsafeUrl("webhook_url_unresolvable") from exc
        for info in infos:
            if _bad_ip(ipaddress.ip_address(info[4][0])):
                raise UnsafeUrl("webhook_url_host_not_public")
    return url
