"""Pricing engine factory for Porterchain API."""

from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_pricing import PricingService


def get_pricing_service(db: Session) -> PricingService:
    """Merchant prices go through the route-pricing hook (no-op unless the merchant opted in)."""
    from porterchain_api.pricing_engine.smart_apply import SmartAwarePricingService

    return SmartAwarePricingService(db, repository=SqlAlchemyPricingRepository(db))
