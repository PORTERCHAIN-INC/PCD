"""Pricing context repository protocol."""

from __future__ import annotations

from typing import Protocol

from porterchain_pricing.types import PricingContext, PricingRequest


class PricingRepository(Protocol):
    def load_context(self, request: PricingRequest) -> PricingContext: ...


class InMemoryPricingRepository:
    """Default rules when no database is available."""

    def load_context(self, request: PricingRequest) -> PricingContext:
        return PricingContext()
