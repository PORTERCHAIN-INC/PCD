from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from porterchain_api.config import get_settings
from porterchain_api.db import init_db
from porterchain_api.gateway.router import router as gateway_router
from porterchain_api.routers import (
    admin,
    auth,
    crm,
    driver,
    drivers_admin,
    merchant,
    merchants,
    operations,
    orders,
    payments,
    quotes,
    webhooks,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    from porterchain_api.platform.bus import ensure_handlers_registered

    ensure_handlers_registered()
    yield


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
    app.include_router(gateway_router)
    app.include_router(auth.router)
    app.include_router(quotes.router)
    app.include_router(orders.router)
    app.include_router(payments.router)
    app.include_router(webhooks.router)
    app.include_router(merchant.router)
    app.include_router(admin.router)
    app.include_router(crm.router)
    app.include_router(merchants.router)
    app.include_router(drivers_admin.router)
    app.include_router(operations.router)
    app.include_router(driver.router)
    app.include_router(driver.legacy_router)

    from fastapi import Request
    from fastapi.responses import JSONResponse

    from porterchain_api.fleetbase_engine import BookingValidationError

    @app.exception_handler(BookingValidationError)
    async def _booking_validation_handler(_request: Request, exc: BookingValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.message, "code": exc.code})

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "porterchain-api"}

    return app


app = create_app()
