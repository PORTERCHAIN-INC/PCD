"""Platform service registry — composition root for internal services."""

from functools import lru_cache

from porterchain_services.gateway.registry import ServiceRegistry, get_service_registry


@lru_cache
def get_platform_registry() -> ServiceRegistry:
    return get_service_registry()
