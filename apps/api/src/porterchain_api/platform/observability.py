"""Sentry + OpenTelemetry bootstrap (DD-02)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def init_observability(*, sentry_dsn: str, app_env: str, service_name: str = "porterchain-api") -> None:
    """Initialize error tracking when configured."""
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=app_env,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.2 if app_env == "production" else 1.0,
            send_default_pii=False,
        )
        logger.info("Sentry initialized for %s (%s)", service_name, app_env)
    else:
        logger.debug("SENTRY_DSN not set — Sentry disabled")


def instrument_app(app, *, app_env: str, service_name: str = "porterchain-api") -> None:
    """Attach OpenTelemetry tracing to FastAPI when OTLP endpoint is configured."""
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not otel_endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment": app_env,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    logger.info("OpenTelemetry initialized for %s → %s", service_name, otel_endpoint)


def bind_request_context(*, request_id: str, path: str, method: str) -> None:
    """Attach correlation ID to Sentry scope and active OTel span."""
    try:
        import sentry_sdk

        sentry_sdk.set_tag("request_id", request_id)
        sentry_sdk.set_context(
            "request",
            {"request_id": request_id, "path": path, "method": method},
        )
    except Exception:  # noqa: BLE001 — observability must not break requests
        pass

    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("porterchain.request_id", request_id)
            span.set_attribute("http.route", path)
            span.set_attribute("http.method", method)
    except Exception:  # noqa: BLE001
        pass
