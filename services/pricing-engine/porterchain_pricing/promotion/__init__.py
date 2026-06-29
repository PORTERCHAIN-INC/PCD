"""Promotions — promo codes, credits, coupons, campaigns."""

from __future__ import annotations

from datetime import UTC, datetime

from porterchain_pricing.types import PriceBreakdown, PricingContext, PricingRequest, PromotionRecord


class PromotionService:
    def find_promotion(self, ctx: PricingContext, code: str | None, merchant_id: str | None) -> PromotionRecord | None:
        if not code:
            return None
        normalized = code.strip().upper()
        for promo in ctx.promotions:
            if not promo.is_active:
                continue
            if promo.code.upper() != normalized:
                continue
            if promo.merchant_id and merchant_id and promo.merchant_id != merchant_id:
                continue
            expires = promo.config.get("expires_at")
            if expires:
                try:
                    exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
                    if exp <= datetime.now(UTC):
                        continue
                except ValueError:
                    pass
            return promo
        return None

    def apply(
        self,
        request: PricingRequest,
        ctx: PricingContext,
        breakdown: PriceBreakdown,
    ) -> None:
        subtotal_before = sum(i.amount_cents for i in breakdown.items if i.amount_cents > 0)

        promo = self.find_promotion(ctx, request.promo_code, request.merchant_id)
        if promo:
            discount = self._promo_discount(promo, subtotal_before)
            if discount:
                breakdown.discount_cents += discount
                breakdown.promo_code = promo.code
                breakdown.add_item("promo", f"Promo {promo.code}", -discount)

        for credit_field, label in (
            (request.wallet_credit_cents, "Wallet credit"),
            (request.referral_credit_cents, "Referral credit"),
        ):
            if credit_field > 0:
                applied = min(credit_field, subtotal_before - breakdown.discount_cents)
                if applied > 0:
                    breakdown.discount_cents += applied
                    breakdown.add_item("credit", label, -applied)

        merchant_discount = ctx.merchant_pricing_config.get("merchant_discount_percent")
        if merchant_discount and request.channel == "merchant":
            pct = float(merchant_discount)
            discount = int(subtotal_before * pct / 100)
            if discount:
                breakdown.discount_cents += discount
                breakdown.add_item("merchant_discount", f"Merchant discount ({pct}%)", -discount)

        campaign = ctx.merchant_pricing_config.get("campaign_discount_cents")
        if campaign and request.channel == "merchant":
            amount = int(campaign)
            if amount:
                breakdown.discount_cents += amount
                breakdown.add_item("campaign", "Campaign discount", -amount)

    @staticmethod
    def _promo_discount(promo: PromotionRecord, subtotal: int) -> int:
        if promo.discount_cents:
            return min(promo.discount_cents, subtotal)
        if promo.discount_percent:
            return int(subtotal * promo.discount_percent / 100)
        promo_type = promo.promotion_type
        if promo_type == "referral_credit":
            return min(int(promo.config.get("amount_cents", 0)), subtotal)
        if promo_type == "wallet_credit":
            return min(int(promo.config.get("amount_cents", 0)), subtotal)
        return 0
