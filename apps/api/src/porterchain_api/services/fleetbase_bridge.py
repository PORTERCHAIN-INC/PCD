"""Legacy Fleetbase bridge — delegates to integration service."""

import logging

from porterchain_api.config import Settings
from porterchain_api.models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)


def sync_order_to_fleetbase(settings: Settings, order: Order) -> str | None:
    """Backward-compatible order sync helper."""
    if not settings.fleetbase_dispatch_bridge:
        logger.info("Fleetbase dispatch bridge disabled; skipping order %s", order.id)
        return None

    integration = get_fleetbase_integration(settings)
    payload = {
        "porterchain_order_id": order.id,
        "fleetbase_order_id": order.fleetbase_order_id,
        "order_number": order.order_number,
        "tracking_number": order.tracking_number,
        "pickup": order.pickup,
        "dropoff": order.dropoff,
        "scheduled_at": order.scheduled_at.isoformat(),
    }
    return integration.sync_order(payload)
