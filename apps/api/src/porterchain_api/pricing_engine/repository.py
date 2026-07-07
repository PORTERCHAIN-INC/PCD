"""SQLAlchemy-backed pricing repository."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from porterchain_api.admin_models import MerchantContract, PricingTariff, PricingZone, Promotion, SystemConfig
from porterchain_api.db import engine
from porterchain_api.merchant_models import Merchant
from porterchain_pricing.types import (
    ContractRecord,
    FuelConfig,
    PricingContext,
    PricingRequest,
    PromotionRecord,
    TariffRecord,
    TaxConfig,
    ZoneRecord,
)


class SqlAlchemyPricingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _has_table(self, name: str) -> bool:
        return inspect(engine).has_table(name)

    def load_context(self, request: PricingRequest) -> PricingContext:
        ctx = PricingContext()
        ctx.tariffs = self._load_tariffs(request)
        ctx.promotions = self._load_promotions(request)
        ctx.zones = self._load_zones()
        ctx.tax = self._load_tax_config()
        ctx.fuel = self._load_fuel_config()

        if request.merchant_id:
            merchant = self.db.query(Merchant).filter(Merchant.id == request.merchant_id).first()
            if merchant:
                ctx.merchant_pricing_config = dict(merchant.pricing_config or {})
            contract = (
                self.db.query(MerchantContract)
                .filter(
                    MerchantContract.merchant_id == request.merchant_id,
                    MerchantContract.is_active.is_(True),
                )
                .order_by(MerchantContract.created_at.desc())
                .first()
            )
            if contract:
                ctx.contract = ContractRecord(
                    id=contract.id,
                    merchant_id=contract.merchant_id,
                    name=contract.name,
                    rules=dict(contract.rules or {}),
                    minimum_monthly_commitment_cents=contract.minimum_monthly_commitment_cents,
                    is_active=contract.is_active,
                )
        return ctx

    def _load_tariffs(self, request: PricingRequest) -> list[TariffRecord]:
        if not self._has_table("pricing_tariffs"):
            return []
        try:
            q = self.db.query(PricingTariff).filter(PricingTariff.is_active.is_(True))
            rows = q.all()
        except ProgrammingError:
            self.db.rollback()
            return []
        tariffs: list[TariffRecord] = []
        for row in rows:
            if row.merchant_id and request.merchant_id and row.merchant_id != request.merchant_id:
                continue
            tariffs.append(
                TariffRecord(
                    id=row.id,
                    name=row.name,
                    tariff_type=row.tariff_type,
                    vehicle_class=row.vehicle_class,
                    zone=row.zone,
                    merchant_id=row.merchant_id,
                    base_cents=row.base_cents,
                    per_km_cents=row.per_km_cents,
                    fuel_surcharge_percent=row.fuel_surcharge_percent,
                    config=dict(row.config or {}),
                )
            )
        return tariffs

    def _load_promotions(self, request: PricingRequest) -> list[PromotionRecord]:
        if not self._has_table("promotions"):
            return []
        try:
            rows = self.db.query(Promotion).filter(Promotion.is_active.is_(True)).all()
        except ProgrammingError:
            self.db.rollback()
            return []
        promos: list[PromotionRecord] = []
        for row in rows:
            config = dict(row.config or {})
            if row.expires_at:
                config["expires_at"] = row.expires_at.isoformat()
            promos.append(
                PromotionRecord(
                    id=row.id,
                    code=row.code,
                    promotion_type=getattr(row, "promotion_type", "coupon"),
                    discount_percent=row.discount_percent,
                    discount_cents=row.discount_cents,
                    merchant_id=getattr(row, "merchant_id", None),
                    is_active=row.is_active,
                    config=config,
                )
            )
        if request.promo_code:
            # ensure requested code is searchable even if inactive filter missed
            pass
        return promos

    def _load_zones(self) -> list[ZoneRecord]:
        if not self._has_table("pricing_zones"):
            return []
        try:
            rows = self.db.query(PricingZone).filter(PricingZone.is_active.is_(True)).all()
        except ProgrammingError:
            self.db.rollback()
            return []
        if not rows:
            return []
        return [
            ZoneRecord(code=r.code, name=r.name, bounds=dict(r.bounds or {}), multiplier=r.multiplier)
            for r in rows
        ]

    def _load_tax_config(self) -> TaxConfig:
        if not self._has_table("system_config"):
            return TaxConfig()
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
        except ProgrammingError:
            self.db.rollback()
            return TaxConfig()
        if row and row.value:
            return TaxConfig(**{k: v for k, v in row.value.items() if k in TaxConfig.__dataclass_fields__})
        return TaxConfig()

    def _load_fuel_config(self) -> FuelConfig:
        if not self._has_table("system_config"):
            return FuelConfig()
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        except ProgrammingError:
            self.db.rollback()
            return FuelConfig()
        if row and row.value:
            return FuelConfig(**{k: v for k, v in row.value.items() if k in FuelConfig.__dataclass_fields__})
        return FuelConfig()
