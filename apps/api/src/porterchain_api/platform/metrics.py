"""Lightweight metrics — Prometheus text format."""

from __future__ import annotations

from porterchain_shared.config.settings import get_platform_settings
from porterchain_shared.queue.names import QueueName
from porterchain_shared.queue.publisher import get_queue_publisher, queue_depths

from porterchain_api.db import SessionLocal

_routing_source_counts: dict[str, int] = {}


def note_routing_source(source: str | None) -> None:
    key = (source or "unknown").strip() or "unknown"
    _routing_source_counts[key] = _routing_source_counts.get(key, 0) + 1


def prometheus_metrics() -> str:
    lines = ["# HELP porterchain_up Porterchain API is running", "# TYPE porterchain_up gauge", "porterchain_up 1"]
    settings = get_platform_settings()
    depths = queue_depths(get_queue_publisher())
    for queue in QueueName:
        depth = depths.get(queue.value, 0)
        lines.append(f'porterchain_queue_depth{{queue="{queue.value}"}} {depth}')
    lines.append(f'porterchain_redis_configured{{env="{settings.app_env}"}} {1 if settings.redis_url else 0}')

    db = SessionLocal()
    try:
        from porterchain_api.admin_engine.business_metrics import (
            assess_business_metrics,
        )
        from porterchain_api.admin_engine.execution_metrics import (
            assess_orders_per_week,
        )
        from porterchain_api.merchant_engine.webhook_delivery_health import (
            assess_merchant_webhook_delivery,
        )
        from porterchain_api.notification_engine.sli_metrics import (
            assess_notification_channel_slis,
            prometheus_notification_lines,
        )

        orders = assess_orders_per_week(db)
        webhook_slo = assess_merchant_webhook_delivery(db)
        business = assess_business_metrics(db)
        notify_sli = assess_notification_channel_slis(db)
        lines.extend(
            [
                "# HELP porterchain_orders_last_7d Orders created in the last 7 days",
                "# TYPE porterchain_orders_last_7d gauge",
                f"porterchain_orders_last_7d {orders.get('orders_last_7d', 0)}",
                "# HELP porterchain_merchant_webhook_delivery_success_pct Outbound merchant webhook success rate",
                "# TYPE porterchain_merchant_webhook_delivery_success_pct gauge",
                f"porterchain_merchant_webhook_delivery_success_pct {webhook_slo.get('success_pct', 100.0)}",
                "# HELP porterchain_merchant_webhook_delivery_meets_slo 1 when success rate >= 99%",
                "# TYPE porterchain_merchant_webhook_delivery_meets_slo gauge",
                f"porterchain_merchant_webhook_delivery_meets_slo {1 if webhook_slo.get('meets_slo') else 0}",
                "# HELP porterchain_merchant_webhook_deliveries Outbound merchant webhook finals in SLO window",
                "# TYPE porterchain_merchant_webhook_deliveries gauge",
                f'porterchain_merchant_webhook_deliveries{{outcome="succeeded"}} {webhook_slo.get("succeeded_deliveries", 0)}',
                f'porterchain_merchant_webhook_deliveries{{outcome="failed"}} {webhook_slo.get("failed_deliveries", 0)}',
                "# HELP porterchain_auto_dispatch_pct Orders with an assigned driver in the dispatch pipeline",
                "# TYPE porterchain_auto_dispatch_pct gauge",
                f"porterchain_auto_dispatch_pct {business['auto_dispatch'].get('pct', 100.0)}",
                "# HELP porterchain_on_time_delivery_pct Delivered orders within scheduled window",
                "# TYPE porterchain_on_time_delivery_pct gauge",
                f"porterchain_on_time_delivery_pct {business['on_time_delivery'].get('pct', 100.0)}",
                "# HELP porterchain_support_first_response_avg_hours Mean hours to first support reply",
                "# TYPE porterchain_support_first_response_avg_hours gauge",
                f"porterchain_support_first_response_avg_hours {business['support_first_response'].get('avg_hours', 0.0)}",
            ]
        )
        lines.extend(prometheus_notification_lines(notify_sli))
    finally:
        db.close()

    from porterchain_api.auth.sli_metrics import prometheus_auth_lines
    from porterchain_api.merchant_engine.commerce_metrics import (
        prometheus_commerce_lines,
    )
    from porterchain_api.platform.rate_limit import prometheus_rate_limit_lines

    lines.extend(prometheus_rate_limit_lines())
    lines.extend(prometheus_auth_lines())
    lines.extend(prometheus_commerce_lines())
    if _routing_source_counts:
        lines.extend(
            [
                "# HELP porterchain_routing_source_total Quote/book routing engine selections",
                "# TYPE porterchain_routing_source_total counter",
            ]
        )
        for source, count in sorted(_routing_source_counts.items()):
            lines.append(f'porterchain_routing_source_total{{source="{source}"}} {count}')
    return "\n".join(lines) + "\n"
