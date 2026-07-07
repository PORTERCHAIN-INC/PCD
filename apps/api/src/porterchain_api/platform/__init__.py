"""Platform integration layer — wires shared + services without changing route behavior."""

from porterchain_api.platform.bus import publish_domain_event
from porterchain_api.platform.registry import get_platform_registry

__all__ = ["get_platform_registry", "publish_domain_event"]
