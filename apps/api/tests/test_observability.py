"""Observability bootstrap tests."""

from porterchain_api.platform.observability import bind_request_context, init_observability


def test_bind_request_context_does_not_raise_without_sentry() -> None:
    bind_request_context(request_id="req-1", path="/health", method="GET")


def test_init_observability_no_dsn_is_noop() -> None:
    init_observability(sentry_dsn="", app_env="local")
