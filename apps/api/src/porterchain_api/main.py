from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from porterchain_api.config import get_settings
from porterchain_api.db import get_db, init_db
from porterchain_api.gateway.router import router as gateway_router
from porterchain_api.platform.middleware import RequestIdMiddleware
from porterchain_api.routers import (
    admin,
    auth,
    booking_drafts,
    collaboration,
    customers,
    driver,
    drivers_admin,
    merchant,
    merchant_api,
    merchants,
    notifications,
    notifications_admin,
    operations,
    orders,
    payments,
    quotes,
    security,
    webhooks,
    diagnostics,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from porterchain_shared.redis_health import require_redis_for_production

    settings = get_settings()
    from porterchain_api.startup_checks import validate_required_settings

    # Fail fast on incomplete production config before serving any traffic.
    validate_required_settings(settings)

    from porterchain_api.platform.observability import init_observability, instrument_app

    init_observability(sentry_dsn=settings.sentry_dsn, app_env=settings.app_env)
    instrument_app(_app, app_env=settings.app_env)
    require_redis_for_production()
    init_db()
    from porterchain_api.platform.bus import ensure_handlers_registered
    from porterchain_api.notification_engine.realtime import realtime_hub

    ensure_handlers_registered()
    await realtime_hub.start()
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)
    from porterchain_api.platform.rate_limit_middleware import PortalRateLimitMiddleware

    app.add_middleware(PortalRateLimitMiddleware)
    from porterchain_api.gateway_engine.middleware import MerchantApiGatewayMiddleware

    app.add_middleware(MerchantApiGatewayMiddleware)
    app.include_router(gateway_router)
    app.include_router(auth.router)
    app.include_router(quotes.router)
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
    app.include_router(drivers_admin.router)
    app.include_router(notifications_admin.router)
    app.include_router(notifications.router)
    app.include_router(security.router)
    app.include_router(operations.router)
    app.include_router(diagnostics.router)
    app.include_router(driver.router)
    app.include_router(driver.legacy_router)

    from fastapi import HTTPException, Request
    from fastapi.responses import JSONResponse

    from porterchain_api.fleetbase_engine import BookingValidationError
    import logging

    _logger = logging.getLogger(__name__)

    @app.exception_handler(BookingValidationError)
    async def _booking_validation_handler(_request: Request, exc: BookingValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=exc.headers,
            )
        _logger.exception("unhandled error: %s", exc)
        detail = str(exc) if settings.app_env != "production" else "internal_server_error"
        return JSONResponse(status_code=500, content={"detail": detail})

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

    @app.get("/metrics")
    def metrics():
        from fastapi.responses import PlainTextResponse
        from porterchain_api.platform.metrics import prometheus_metrics

        return PlainTextResponse(prometheus_metrics(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
