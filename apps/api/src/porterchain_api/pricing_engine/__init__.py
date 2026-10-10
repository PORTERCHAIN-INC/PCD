"""Pricing engine factory for Porterchain API."""

from porterchain_pricing import PricingService
from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository


def get_pricing_service(db: Session) -> PricingService:
    return PricingService(repository=SqlAlchemyPricingRepository(db))
