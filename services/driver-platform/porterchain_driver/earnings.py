"""Driver earnings — rate-card driven wallet credits on delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Fallback when SystemConfig/rate card cannot be loaded (matches RateCard default).
DEFAULT_PER_STOP_CENTS = 850


class EarningsService:
    def _finance(self):
        from porterchain_api.billing_engine.driver_finance_service import DriverFinanceService

        return DriverFinanceService()

    def today_cents(self, db: Session, driver_id: str) -> int:
        return self._finance().period_earnings_cents(db, driver_id, "today")

    def week_cents(self, db: Session, driver_id: str) -> int:
        return self._finance().period_earnings_cents(db, driver_id, "week")

    def month_cents(self, db: Session, driver_id: str) -> int:
        return self._finance().period_earnings_cents(db, driver_id, "month")

    def route_earnings_cents(self, db: Session, driver_id: str, route_id: str) -> int:
        return self._finance().route_earnings_cents(db, driver_id, route_id)

    def resolve_delivery_payout_cents(self, db: Session, *, order_id: str) -> int:
        """Resolve wallet credit from system (+ merchant) rate card for this order."""
        try:
            from porterchain_api.admin_models import SystemConfig
            from porterchain_api.booking_models import Order
            from porterchain_api.merchant_models import Merchant
            from porterchain_pricing.rate_card import (
                default_rate_card,
                merge_merchant_overlay,
                rate_card_from_dict,
            )

            order = db.query(Order).filter(Order.id == order_id).first()
            row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_rate_card").first()
            system = rate_card_from_dict(dict(row.value) if row and isinstance(row.value, dict) else None)
            merchant_config: dict[str, Any] = {}
            if order and order.merchant_id:
                merchant = db.query(Merchant).filter(Merchant.id == order.merchant_id).first()
                if merchant:
                    merchant_config = dict(merchant.pricing_config or {})
            card = merge_merchant_overlay(system, merchant_config) if merchant_config else system
            order_amount = int(order.amount_cents) if order and order.amount_cents is not None else 0
            return card.compute_driver_payout_cents(order_amount_cents=order_amount)
        except Exception:
            return DEFAULT_PER_STOP_CENTS

    def credit_delivery(
        self,
        db: Session,
        driver: Any,
        *,
        order_id: str,
        amount_cents: int | None = None,
        description: str = "Delivery completed",
    ) -> int:
        from porterchain_api.driver_models import DriverWalletTransaction
        from porterchain_driver.wallet import WalletService

        # Idempotent: one delivery credit per order
        existing = (
            db.query(DriverWalletTransaction)
            .filter(
                DriverWalletTransaction.driver_id == driver.id,
                DriverWalletTransaction.tx_type == "delivery",
                DriverWalletTransaction.reference_id == order_id,
            )
            .first()
        )
        if existing:
            return int(driver.wallet_balance_cents or 0)

        amount = (
            amount_cents
            if amount_cents is not None
            else self.resolve_delivery_payout_cents(db, order_id=order_id)
        )
        if amount <= 0:
            amount = DEFAULT_PER_STOP_CENTS

        mode_note = ""
        try:
            from porterchain_api.admin_models import SystemConfig
            from porterchain_pricing.rate_card import rate_card_from_dict

            row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_rate_card").first()
            card = rate_card_from_dict(dict(row.value) if row and isinstance(row.value, dict) else None)
            if card.driver_payout_mode == "percent":
                mode_note = f" ({card.driver_share_pct:g}% of order)"
            else:
                mode_note = " (flat rate card)"
        except Exception:
            mode_note = ""

        return WalletService().credit(
            db,
            driver,
            amount_cents=amount,
            tx_type="delivery",
            reference_id=order_id,
            description=f"{description}{mode_note}",
        )
