"""Internal API gateway routes — service health and platform status."""

from fastapi import APIRouter

from porterchain_api.platform.registry import get_platform_registry

router = APIRouter(prefix="/internal", tags=["gateway"])


@router.get("/health")
def internal_health() -> dict[str, str]:
    return {"status": "ok", "layer": "gateway"}


@router.get("/services")
def service_health() -> dict[str, str]:
    return get_platform_registry().health()
