"""Base service contract — all domain services extend this."""

from abc import ABC
from dataclasses import dataclass

from porterchain_shared.config.settings import PlatformSettings, get_platform_settings
from porterchain_shared.events.publisher import EventPublisher, get_event_publisher
from porterchain_shared.queue.publisher import QueuePublisher, get_queue_publisher


@dataclass
class ServiceContext:
    settings: PlatformSettings
    events: EventPublisher
    queues: QueuePublisher


def build_service_context() -> ServiceContext:
    return ServiceContext(
        settings=get_platform_settings(),
        events=get_event_publisher(),
        queues=get_queue_publisher(),
    )


class BaseService(ABC):
    """Shared dependencies for all Porterchain services."""

    service_name: str = "base"

    def __init__(self, ctx: ServiceContext | None = None) -> None:
        self.ctx = ctx or build_service_context()

    @property
    def settings(self) -> PlatformSettings:
        return self.ctx.settings
