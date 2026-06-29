from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from porterchain_api.config import get_settings
from porterchain_api.db import init_db
from porterchain_api.gateway.router import router as gateway_router
from porterchain_api.routers import admin, auth, driver, merchant, orders, payments, quotes, webhooks


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
    app.include_router(driver.router)
    app.include_router(driver.legacy_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "porterchain-api"}

    return app


app = create_app()
