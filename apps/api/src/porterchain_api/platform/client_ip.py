"""Real client IP behind our own reverse proxy (Caddy), spoof-resistant.

Clients can send any X-Forwarded-For. Our proxy appends the address it saw, so the
trusted value is the entry ``TRUSTED_PROXY_HOPS`` from the RIGHT (default 1 = Caddy's).
X-Forwarded-For is only honoured when the direct peer is a private/loopback address
(i.e. the request really came through our proxy on the docker network).
"""

from __future__ import annotations

import ipaddress
import os
from typing import Any


def _hops() -> int:
    try:
        return max(1, int(os.environ.get("TRUSTED_PROXY_HOPS", "1")))
    except ValueError:
        return 1


def _is_internal(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host in {"testclient", "localhost"}
    return ip.is_private or ip.is_loopback


def client_ip(request: Any, default: str = "unknown") -> str:
    peer = ""
    try:
        peer = (getattr(getattr(request, "client", None), "host", None) or "").strip()
        raw = request.headers.get("x-forwarded-for") or ""
    except Exception:  # noqa: BLE001
        raw = ""
    if raw and (not peer or _is_internal(peer)):
        chain = [p.strip() for p in raw.split(",") if p.strip()]
        if chain:
            return chain[-min(_hops(), len(chain))][:64]
    return peer[:64] or default


def is_trusted_server(ip: str) -> bool:
    """Our own servers (docker network, loopback, TRUSTED_SERVER_IPS e.g. the droplet's
    public IP for server-side renders that hairpin through Caddy): never rate limited."""
    extra = {x.strip() for x in os.environ.get("TRUSTED_SERVER_IPS", "").split(",") if x.strip()}
    return ip in extra or _is_internal(ip)
