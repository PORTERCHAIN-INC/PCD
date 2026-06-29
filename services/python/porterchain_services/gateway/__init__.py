"""Internal API gateway — service registry and composition root."""

from porterchain_services.gateway.registry import ServiceRegistry, get_service_registry

__all__ = ["ServiceRegistry", "get_service_registry"]
