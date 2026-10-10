"""SQLAlchemy-backed pricing repository."""

from __future__ import annotations

from sqlalchemy import inspect, or_
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from porterchain_api.admin_models import (
    MerchantContract,
    PricingFsaRate,
    PricingTariff,
    PricingZone,
    Promotion,
    SystemConfig,
)
from porterchain_api.db import engine
from porterchain_api.merchant_models import Merchant
from porterchain_api.domain.pricing_version import VERSION_KEY, format_version
from porterchain_pricing.gta_rate import (
    customer_gta_from_dict,
    default_customer_distance_dict,
    default_gta_rate_config,
    gta_rate_config_from_dict,
    merge_merchant_gta_overlay,
)
from porterchain_pricing.policy import MODEL_DISTANCE, MODEL_FSA, policy_from_config
from porterchain_pricing.rate_card import default_rate_card, merge_merchant_overlay, rate_card_from_dict
from porterchain_pricing.types import (
    ContractRecord,
    FsaRateRecord,
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
        is_merchant = request.channel == "merchant" and bool(request.merchant_id)
        ctx.tariffs = self._load_tariffs(request) if is_merchant else []
        ctx.promotions = self._load_promotions(request)
        ctx.zones = self._load_zones()
        ctx.tax = self._load_tax_config()
        ctx.fuel = self._load_fuel_config()
        ctx.price_book = self._load_system_value("pricing_book")
        ctx.price_version = format_version(self._load_system_value(VERSION_KEY))
        ctx.coverage = self._load_system_value("parcel_coverage")
        system_card = self._load_rate_card()
        if request.channel == "retail":
            # Customer distance card only. Merchant FSA, rate card, and fuel stay off this quote.
            ctx.gta_rate = self._load_customer_distance()
            ctx.fsa_rates = []
            ctx.tariffs = []
            ctx.rate_card = system_card
            return ctx

        ctx.gta_rate = self._load_gta_rate_config()
        ctx.fsa_rates = self._load_fsa_rates(request.merchant_id) if is_merchant else []

        if is_merchant:
            merchant = self.db.query(Merchant).filter(Merchant.id == request.merchant_id).first()
            if merchant:
                ctx.merchant_pricing_config = dict(merchant.pricing_config or {})
                ctx.merchant_policy = policy_from_config(ctx.merchant_pricing_config)
                model = getattr(merchant, "pricing_model", None) or MODEL_DISTANCE
                ctx.merchant_policy.pricing_model = (
                    model if model in (MODEL_FSA, MODEL_DISTANCE) else MODEL_DISTANCE
                )
                # Per-merchant Distance matrix — platform Settings as base.
                ctx.gta_rate = merge_merchant_gta_overlay(ctx.gta_rate, ctx.merchant_pricing_config)
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
                # Fold contract rule knobs into merchant overlay when not already set
                rules = dict(contract.rules or {})
                cfg = dict(ctx.merchant_pricing_config)
                rate_overlay = dict(cfg.get("rate_card") or {})
                for key in ("weekend_multiplier", "holiday_multiplier", "holidays", "minimum_charge_cents"):
                    if key in rules and key not in rate_overlay and key not in cfg:
                        rate_overlay[key] = rules[key]
                if rate_overlay:
                    cfg["rate_card"] = rate_overlay
                    ctx.merchant_pricing_config = cfg

            ctx.rate_card = merge_merchant_overlay(system_card, ctx.merchant_pricing_config)
        else:
            ctx.rate_card = system_card
        return ctx

    def _load_system_value(self, key: str):
        """Raw `system_config` value, or None (missing table / row)."""
        if not self._has_table("system_config"):
            return None
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == key).first()
        except ProgrammingError:
            self.db.rollback()
            return None
        return row.value if row else None

    def _load_rate_card(self):
        if not self._has_table("system_config"):
            return default_rate_card()
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_rate_card").first()
        except ProgrammingError:
            self.db.rollback()
            return default_rate_card()
        if row and isinstance(row.value, dict):
            return rate_card_from_dict(row.value)
        return default_rate_card()

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

    def _load_fsa_rates(self, merchant_id: str | None = None) -> list[FsaRateRecord]:
        """Platform-wide rows plus this merchant's own. Other merchants' rows never load."""
        if not self._has_table("pricing_fsa_rates"):
            return []
        try:
            rows = (
                self.db.query(PricingFsaRate)
                .filter(
                    PricingFsaRate.is_active.is_(True),
                    or_(
                        PricingFsaRate.merchant_id.is_(None),
                        PricingFsaRate.merchant_id == merchant_id,
                    ),
                )
                .all()
            )
        except ProgrammingError:
            self.db.rollback()
            return []
        return [
            FsaRateRecord(
                id=row.id,
                dest_fsa=row.dest_fsa,
                flat_cents=row.flat_cents,
                merchant_id=row.merchant_id,
                origin_fsa=row.origin_fsa,
                vehicle_class=row.vehicle_class,
                includes_location_fees=bool(row.includes_location_fees),
                label=row.label or "",
                is_active=row.is_active,
                config=dict(row.config or {}),
            )
            for row in rows
        ]

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
            return TaxConfig(hst_percent=13.0)
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
        except ProgrammingError:
            self.db.rollback()
            return TaxConfig(hst_percent=13.0)
        if row and row.value:
            return TaxConfig(**{k: v for k, v in row.value.items() if k in TaxConfig.__dataclass_fields__})
        return TaxConfig(hst_percent=13.0)

    def _load_fuel_config(self) -> FuelConfig:
        if not self._has_table("system_config"):
            return FuelConfig(surcharge_percent=5.0)
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        except ProgrammingError:
            self.db.rollback()
            return FuelConfig(surcharge_percent=5.0)
        if row and row.value:
            return FuelConfig(**{k: v for k, v in row.value.items() if k in FuelConfig.__dataclass_fields__})
        return FuelConfig(surcharge_percent=5.0)

    def _load_customer_distance(self):
        if not self._has_table("system_config"):
            return customer_gta_from_dict(default_customer_distance_dict())
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_customer_distance").first()
        except ProgrammingError:
            self.db.rollback()
            return customer_gta_from_dict(default_customer_distance_dict())
        if row and isinstance(row.value, dict):
            return customer_gta_from_dict(row.value)
        return customer_gta_from_dict(default_customer_distance_dict())

    def _load_gta_rate_config(self):
        if not self._has_table("system_config"):
            return default_gta_rate_config()
        try:
            row = self.db.query(SystemConfig).filter(SystemConfig.key == "pricing_gta_rate").first()
        except ProgrammingError:
            self.db.rollback()
            return default_gta_rate_config()
        if row and isinstance(row.value, dict):
            return gta_rate_config_from_dict(row.value)
        return default_gta_rate_config()


def current_price_version(db: Session) -> str:
    """`pv-<n>` for the admin pricing views (the engine reads it via load_context)."""
    row = db.query(SystemConfig).filter(SystemConfig.key == VERSION_KEY).first()
    return format_version(row.value if row else None)
