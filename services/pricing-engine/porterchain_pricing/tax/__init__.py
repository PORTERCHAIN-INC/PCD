"""Tax calculation — Porterchain owns tax logic."""

from __future__ import annotations

from porterchain_pricing.types import PriceBreakdown, PricingContext, PricingRequest, TaxConfig


class TaxService:
    def __init__(self, config: TaxConfig | None = None) -> None:
        self.config = config or TaxConfig()

    def with_context(self, ctx: PricingContext) -> TaxService:
        return TaxService(ctx.tax)

    def calculate(self, request: PricingRequest, breakdown: PriceBreakdown) -> int:
        if request.merchant_id and request.merchant_id in self.config.exempt_merchant_ids:
            return 0
        taxable = breakdown.subtotal_cents
        if taxable <= 0:
            return 0
        return int(taxable * (self.config.hst_percent / 100.0))
