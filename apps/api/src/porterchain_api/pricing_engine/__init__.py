"""Pricing engine factory for Porterchain API."""

from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_pricing import PricingService


def get_pricing_service(db: Session) -> PricingService:
    return PricingService(repository=SqlAlchemyPricingRepository(db))
