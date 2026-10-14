import logging

from porterchain_api.platform.log_redact import RedactTokensFilter, install, redact


def test_redacts_ws_query_tokens() -> None:
    line = '1.2.3.4:5 - "WebSocket /v1/notifications/ws?token=staff_sess_abcDEF123" [accepted]'
    out = redact(line)
    assert "abcDEF123" not in out and "token=REDACTED" in out
    assert "abc" not in redact("/v1/admin/operations/live/ws?portal=admin&token=abc.def-ghi")
    assert redact("GET /v1/orders?limit=50") == "GET /v1/orders?limit=50"


def test_filter_rewrites_uvicorn_access_args(caplog) -> None:
    install()
    rec = logging.LogRecord("uvicorn.access", logging.INFO, "", 0,
                            '%s - "%s %s HTTP/%s" %d', ("1.2.3.4", "GET", "/ws?token=s3cret", "1.1", 101), None)
    RedactTokensFilter().filter(rec)
    assert "s3cret" not in rec.getMessage()
    assert any(isinstance(f, RedactTokensFilter) for f in logging.getLogger("uvicorn.access").filters)
