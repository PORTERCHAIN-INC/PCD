"""Pricing engine factory for Porterchain API."""

from sqlalchemy.orm import Session

from porterchain_api.pricing_engine.repository import SqlAlchemyPricingRepository
from porterchain_pricing import PricingService, PricingSimulator


def get_pricing_service(db: Session) -> PricingService:
    return PricingService(repository=SqlAlchemyPricingRepository(db))


def get_pricing_simulator(db: Session) -> PricingSimulator:
    repo = SqlAlchemyPricingRepository(db)
    service = PricingService(repository=repo)
    return service.simulator
