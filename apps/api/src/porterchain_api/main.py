from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.db import get_db, init_db
from porterchain_api.gateway.router import router as gateway_router
from porterchain_api.platform.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from porterchain_api.routers import (
    admin,
    auth,
    booking_drafts,
    collaboration,
    customers,
    customers_admin,
    driver,
    drivers_admin,
    drivers_admin_account,
    lead_webhooks,
    merchant,
    merchant_api,
    merchants,
    merchants_integrations,
    notifications,
    notifications_admin,
    operations,
    orders,
    payments,
    public_inquiries,
    zeptomail_webhook,
    public_guide,
    public_blog,
    pricing_admin,
    pricing_components,
    quotes,
    shopify,
    security,
    webhooks,
    diagnostics,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from porterchain_shared.redis_health import require_redis_for_production

    settings = get_settings()
    from porterchain_api.platform.observability import init_observability, instrument_app

    init_observability(sentry_dsn=settings.sentry_dsn, app_env=settings.app_env)
    instrument_app(_app, app_env=settings.app_env)
    require_redis_for_production()
    init_db()
    from porterchain_api.platform.bus import ensure_handlers_registered
    from porterchain_api.notification_engine.realtime import realtime_hub

    ensure_handlers_registered()
    await realtime_hub.start()
    # Permanent Fleetbase bond: best-effort auth handshake (never blocks boot).
    try:
        from porterchain_api.fleetbase_engine.bond import run_boot_handshake

        run_boot_handshake(settings)
    except Exception:  # noqa: BLE001
        pass
    try:
        yield
    finally:
        await realtime_hub.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Porterchain API",
        version="0.1.0",
        lifespan=lifespan,
    )
    cors_kwargs: dict = {
        "allow_origins": settings.cors_origin_list,
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        # Downloads name themselves. Without this the portals cannot read the
        # filename off a cross-origin response and have to guess it (BR).
        "expose_headers": ["Content-Disposition", REQUEST_ID_HEADER],
    }
    # Next.js "Network" URLs (http://192.168.x.x:3000) in local/dev.
    if settings.app_env in {"local", "development"}:
        cors_kwargs["allow_origin_regex"] = (
            r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})"
            r":(3000|3001|3002|3003|3004)$"
        )
    app.add_middleware(CORSMiddleware, **cors_kwargs)
    app.add_middleware(RequestIdMiddleware)
    from porterchain_api.platform.rate_limit_middleware import PortalRateLimitMiddleware

    app.add_middleware(PortalRateLimitMiddleware)
    from porterchain_api.gateway_engine.middleware import MerchantApiGatewayMiddleware

    app.add_middleware(MerchantApiGatewayMiddleware)
    app.include_router(gateway_router)
    app.include_router(auth.router)
    from porterchain_api.routers import oauth

    app.include_router(oauth.router)
    app.include_router(quotes.router)
    app.include_router(pricing_components.router)
    app.include_router(pricing_admin.router)
    app.include_router(shopify.router)
    app.include_router(public_inquiries.router)
    app.include_router(zeptomail_webhook.router)
    app.include_router(public_guide.router)
    app.include_router(lead_webhooks.router)
    app.include_router(public_blog.router)
    app.include_router(booking_drafts.router)
    app.include_router(orders.router)
    app.include_router(customers.router)
    app.include_router(payments.router)
    app.include_router(webhooks.router)
    app.include_router(merchant.router)
    app.include_router(merchant_api.router)
    app.include_router(admin.router)
    app.include_router(collaboration.router)
    app.include_router(merchants.router)
    app.include_router(merchants_integrations.router)
    app.include_router(drivers_admin.router)
    app.include_router(drivers_admin_account.router)
    app.include_router(customers_admin.router)
    app.include_router(notifications_admin.router)
    app.include_router(notifications.router)
    app.include_router(security.router)
    app.include_router(operations.router)
    app.include_router(operations.dispatch_router)
    app.include_router(diagnostics.router)
    app.include_router(driver.router)

    from fastapi import HTTPException, Request
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse

    from porterchain_api.fleetbase_engine import BookingValidationError
    from porterchain_api.platform.errors import error_envelope
    import logging

    _logger = logging.getLogger(__name__)

    def _request_id(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(BookingValidationError)
    async def _booking_validation_handler(request: Request, exc: BookingValidationError) -> JSONResponse:
        rid = _request_id(request)
        return JSONResponse(
            status_code=422,
            content=error_envelope(exc.message, code=exc.code, request_id=rid),
            headers={REQUEST_ID_HEADER: rid} if rid else None,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        rid = _request_id(request)
        return JSONResponse(
            status_code=422,
            content=error_envelope(exc.errors(), request_id=rid),
            headers={REQUEST_ID_HEADER: rid} if rid else None,
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        rid = _request_id(request)
        headers = dict(exc.headers or {})
        if rid:
            headers[REQUEST_ID_HEADER] = rid
        return JSONResponse(
            status_code=exc.status_code,
            content=error_envelope(exc.detail, request_id=rid),
            headers=headers or None,
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        _logger.exception("unhandled error: %s", exc)
        detail = str(exc) if settings.app_env != "production" else "internal_server_error"
        rid = _request_id(request)
        return JSONResponse(
            status_code=500,
            content=error_envelope(detail, code="internal_server_error", request_id=rid),
            headers={REQUEST_ID_HEADER: rid} if rid else None,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        from porterchain_api.platform.health import liveness

        return liveness()

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        from porterchain_api.platform.health import liveness

        return liveness()

    @app.get("/health/ready")
    def health_ready(db: Session = Depends(get_db)) -> dict:
        from porterchain_api.platform.health import readiness

        return readiness(db, settings)

    @app.get("/health/status")
    def health_status(db: Session = Depends(get_db)) -> dict:
        from porterchain_api.platform.health import public_status

        return public_status(db, settings)

    @app.get("/metrics")
    def metrics():
        from fastapi.responses import PlainTextResponse
        from porterchain_api.platform.metrics import prometheus_metrics

        return PlainTextResponse(prometheus_metrics(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
