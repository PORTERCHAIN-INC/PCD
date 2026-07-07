"""Lightweight metrics — Prometheus text format."""

from __future__ import annotations

from porterchain_shared.config.settings import get_platform_settings
from porterchain_shared.queue.names import QueueName
from porterchain_shared.queue.publisher import get_queue_publisher, queue_depths


def prometheus_metrics() -> str:
    lines = ["# HELP porterchain_up Porterchain API is running", "# TYPE porterchain_up gauge", "porterchain_up 1"]
    settings = get_platform_settings()
    depths = queue_depths(get_queue_publisher())
    for queue in QueueName:
        depth = depths.get(queue.value, 0)
        lines.append(f'porterchain_queue_depth{{queue="{queue.value}"}} {depth}')
    lines.append(f'porterchain_redis_configured{{env="{settings.app_env}"}} {1 if settings.redis_url else 0}')
    return "\n".join(lines) + "\n"
