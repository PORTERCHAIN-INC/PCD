"""Order platform service — Application Service (masterrule §3).

PorterChain owns the order lifecycle. Tracking and GPS come from PorterChain
services (Redis last_known + day plan), never from a vendor console or UI HTTP.
"""

from __future__ import annotations

from porterchain_api.order_engine.platform_dashboard import OrderPlatformDashboardMixin
from porterchain_api.order_engine.platform_detail import OrderPlatformDetailMixin
from porterchain_api.order_engine.platform_enriched import OrderPlatformEnrichedMixin
from porterchain_api.order_engine.platform_helpers import OrderPlatformHelpersMixin
from porterchain_api.order_engine.platform_legacy import OrderPlatformLegacyMixin
from porterchain_api.order_engine.platform_reports import OrderPlatformReportsMixin


class OrderPlatformService(
    OrderPlatformHelpersMixin,
    OrderPlatformLegacyMixin,
    OrderPlatformDashboardMixin,
    OrderPlatformEnrichedMixin,
    OrderPlatformDetailMixin,
    OrderPlatformReportsMixin,
):
    """Unified order platform service composed from domain mixins."""

    def __init__(self) -> None:
        from porterchain_api.admin_engine.control_tower_service import ControlTowerService
        from porterchain_api.booking_engine.tracking_service import TrackingService

        self._tower = ControlTowerService()
        self._tracking = TrackingService()


__all__ = ["OrderPlatformService"]
