"""Service registry — single composition root for all internal services."""

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from porterchain_services.customer.service import CustomerService
    from porterchain_services.dispatch.service import DispatchService
    from porterchain_services.driver.service import DriverService
    from porterchain_services.maps.service import MapsService
    from porterchain_services.merchant.service import MerchantService
    from porterchain_services.pricing.service import PricingService
    from porterchain_services.stripe.service import StripeService
    from porterchain_services.visitor.service import VisitorService


class ServiceRegistry:
    """Lazy-loaded service container — used by API gateway and workers."""

    def __init__(self) -> None:
        self._stripe: StripeService | None = None
        self._maps: MapsService | None = None
        self._pricing: PricingService | None = None
        self._merchant: MerchantService | None = None
        self._driver: DriverService | None = None
        self._dispatch: DispatchService | None = None
        self._customer: CustomerService | None = None
        self._visitor: VisitorService | None = None

    @property
    def stripe(self) -> "StripeService":
        if self._stripe is None:
            from porterchain_services.stripe.service import StripeService

            self._stripe = StripeService()
        return self._stripe

    @property
    def maps(self) -> "MapsService":
        if self._maps is None:
            from porterchain_services.maps.service import MapsService

            self._maps = MapsService()
        return self._maps

    @property
    def pricing(self) -> "PricingService":
        if self._pricing is None:
            from porterchain_services.pricing.service import PricingService

            self._pricing = PricingService()
        return self._pricing

    @property
    def merchant(self) -> "MerchantService":
        if self._merchant is None:
            from porterchain_services.merchant.service import MerchantService

            self._merchant = MerchantService()
        return self._merchant

    @property
    def driver(self) -> "DriverService":
        if self._driver is None:
            from porterchain_services.driver.service import DriverService

            self._driver = DriverService()
        return self._driver

    @property
    def dispatch(self) -> "DispatchService":
        if self._dispatch is None:
            from porterchain_services.dispatch.service import DispatchService

            self._dispatch = DispatchService()
        return self._dispatch

    @property
    def customer(self) -> "CustomerService":
        if self._customer is None:
            from porterchain_services.customer.service import CustomerService

            self._customer = CustomerService()
        return self._customer

    @property
    def visitor(self) -> "VisitorService":
        if self._visitor is None:
            from porterchain_services.visitor.service import VisitorService

            self._visitor = VisitorService()
        return self._visitor

    def health(self) -> dict[str, str]:
        import os

        bridge_on = os.getenv("FLEETBASE_DISPATCH_BRIDGE", "true").lower() not in ("0", "false", "no")
        has_key = bool(os.getenv("FLEETBASE_API_KEY", "").strip())
        fleetbase_status = "configured" if bridge_on and has_key else "disabled"
        return {
            "gateway": "ok",
            "fleetbase": fleetbase_status,
            "stripe": "configured" if self.stripe.is_configured else "mock",
            "maps": self.maps.engine,
            # Notifications: porterchain_api.notification_engine (domain events).
            "notifications": "engine",
        }


@lru_cache
def get_service_registry() -> ServiceRegistry:
    return ServiceRegistry()
