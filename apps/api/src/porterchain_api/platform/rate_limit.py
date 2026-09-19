"""Shared Redis fixed-window rate limiter — policy plane for portal + merchant-api."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Final

# Traffic classes for metrics / bucket keys (single policy plane).
TRAFFIC_PORTAL: Final = "portal"
TRAFFIC_MERCHANT_API: Final = "merchant_api"
TRAFFIC_MERCHANT_API_SANDBOX: Final = "merchant_api_sandbox"
TRAFFIC_MERCHANT_API_OAUTH: Final = "merchant_api_oauth"
TRAFFIC_MERCHANT_API_OAUTH_SANDBOX: Final = "merchant_api_oauth_sandbox"
TRAFFIC_SHOPIFY_CARRIER: Final = "shopify_carrier"
TRAFFIC_SHOPIFY_WEBHOOK: Final = "shopify_webhook"

_rate_limited: dict[str, int] = defaultdict(int)
_rate_limit_unavailable: dict[str, int] = defaultdict(int)
_merchant_api_auth_reject: dict[str, int] = defaultdict(int)


def bucket_key(traffic_class: str, identity: str) -> str:
    return f"porterchain:ratelimit:{traffic_class}:{identity}"


def rate_limit_headers(limit: int, current: int) -> dict[str, str]:
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(max(0, limit - current)),
    }


def check_fixed_window(key: str, limit: int, *, window: int | None = None) -> tuple[bool, int, str | None]:
    """Return (allowed, current_count, error_message). Fail closed when Redis is unavailable."""
    minute = int(time.time() // 60) if window is None else window
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        bucket = f"{key}:{minute}"
        current = int(client.incr(bucket))
        if current == 1:
            client.expire(bucket, 70)
        return current <= limit, current, None
    except Exception as exc:
        return False, 0, str(exc)


def peek_fixed_window(key: str, *, window: int | None = None) -> tuple[int, str | None]:
    """Read current window count without incrementing. Returns (count, error)."""
    minute = int(time.time() // 60) if window is None else window
    try:
        from porterchain_shared.redis_client import get_redis_client

        client = get_redis_client()
        raw = client.get(f"{key}:{minute}")
        return (int(raw) if raw is not None else 0), None
    except Exception as exc:
        return 0, str(exc)


def incr_rate_limited(traffic_class: str) -> None:
    _rate_limited[traffic_class] += 1


def incr_rate_limit_unavailable(traffic_class: str) -> None:
    _rate_limit_unavailable[traffic_class] += 1


def incr_merchant_api_auth_reject(reason: str) -> None:
    _merchant_api_auth_reject[reason] += 1


def prometheus_rate_limit_lines() -> list[str]:
    lines = [
        "# HELP porterchain_http_rate_limited_total HTTP 429 responses from edge rate limits",
        "# TYPE porterchain_http_rate_limited_total counter",
    ]
    for traffic_class, value in sorted(_rate_limited.items()):
        lines.append(f'porterchain_http_rate_limited_total{{traffic_class="{traffic_class}"}} {value}')
    lines.extend(
        [
            "# HELP porterchain_http_rate_limit_unavailable_total Redis rate-limit backend failures",
            "# TYPE porterchain_http_rate_limit_unavailable_total counter",
        ]
    )
    for traffic_class, value in sorted(_rate_limit_unavailable.items()):
        lines.append(
            f'porterchain_http_rate_limit_unavailable_total{{traffic_class="{traffic_class}"}} {value}'
        )
    lines.extend(
        [
            "# HELP porterchain_merchant_api_auth_reject_total Merchant-api edge auth rejects",
            "# TYPE porterchain_merchant_api_auth_reject_total counter",
        ]
    )
    for reason, value in sorted(_merchant_api_auth_reject.items()):
        lines.append(f'porterchain_merchant_api_auth_reject_total{{reason="{reason}"}} {value}')
    return lines


# Back-compat alias used by older tests / imports.
def _check_rate(key: str, window: int, limit: int) -> tuple[bool, int, str | None]:
    return check_fixed_window(key, limit, window=window)
