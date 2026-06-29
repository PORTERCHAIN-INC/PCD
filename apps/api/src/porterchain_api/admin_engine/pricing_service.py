"""Pricing administration — rules, contracts, promotions, simulator."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import MerchantContract, PricingTariff, PricingZone, Promotion, SystemConfig
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.pricing_engine import get_pricing_simulator
from porterchain_pricing import GeoPoint, PricingRequest


class AdminPricingService:
    def list_tariffs(self, db: Session, *, tariff_type: str | None = None) -> list[PricingTariff]:
        q = db.query(PricingTariff).filter(PricingTariff.is_active.is_(True))
        if tariff_type:
            q = q.filter(PricingTariff.tariff_type == tariff_type)
        return q.order_by(PricingTariff.name).all()

    def create_tariff(self, db: Session, ctx: AdminContext, **fields) -> PricingTariff:
        record = PricingTariff(**fields)
        db.add(record)
        db.flush()
        emit_event(
            db,
            event_type=E.PRICING_UPDATED,
            aggregate_type="pricing_tariff",
            aggregate_id=record.id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(record)
        return record

    def list_promotions(self, db: Session) -> list[Promotion]:
        return db.query(Promotion).order_by(Promotion.created_at.desc()).all()

    def create_promotion(self, db: Session, code: str, **fields) -> Promotion:
        record = Promotion(code=code, **fields)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def list_zones(self, db: Session) -> list[PricingZone]:
        return db.query(PricingZone).filter(PricingZone.is_active.is_(True)).order_by(PricingZone.code).all()

    def create_zone(self, db: Session, **fields) -> PricingZone:
        record = PricingZone(**fields)
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def list_contracts(self, db: Session, *, merchant_id: str | None = None) -> list[MerchantContract]:
        q = db.query(MerchantContract).filter(MerchantContract.is_active.is_(True))
        if merchant_id:
            q = q.filter(MerchantContract.merchant_id == merchant_id)
        return q.order_by(MerchantContract.created_at.desc()).all()

    def create_contract(self, db: Session, ctx: AdminContext, **fields) -> MerchantContract:
        record = MerchantContract(**fields)
        db.add(record)
        db.flush()
        emit_event(
            db,
            event_type=E.PRICING_UPDATED,
            aggregate_type="merchant_contract",
            aggregate_id=record.id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(record)
        return record

    def get_tax_config(self, db: Session) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
        return dict(row.value) if row else {"hst_percent": 13.0, "tax_included": False}

    def update_tax_config(self, db: Session, value: dict) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
        if not row:
            row = SystemConfig(key="pricing_tax", value=value)
            db.add(row)
        else:
            row.value = value
        db.commit()
        return value

    def get_fuel_config(self, db: Session) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        return dict(row.value) if row else {"surcharge_percent": 8.5}

    def update_fuel_config(self, db: Session, value: dict) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        if not row:
            row = SystemConfig(key="pricing_fuel", value=value)
            db.add(row)
        else:
            row.value = value
        db.commit()
        return value

    def simulate(self, db: Session, body: dict) -> dict:
        simulator = get_pricing_simulator(db)
        request = PricingRequest(
            pickup=GeoPoint(**body["pickup"]),
            dropoff=GeoPoint(**body["dropoff"]),
            vehicle_class=body["vehicle_class"],
            package_type=body.get("package_type", "looseParcel"),
            service_type=body.get("service_type", "same_day"),
            weight_kg=body.get("weight_kg"),
            dimensions=body.get("dimensions"),
            declared_value_cents=body.get("declared_value_cents"),
            schedule_mode=body.get("schedule_mode", "now"),
            is_rush=body.get("schedule_mode", "now") == "now",
            channel=body.get("channel", "retail"),  # type: ignore[arg-type]
            merchant_id=body.get("merchant_id"),
            promo_code=body.get("promo_code"),
            distance_meters=body.get("distance_meters"),
        )
        breakdown = simulator.simulate(request, overrides=body.get("overrides"))
        from porterchain_pricing import PricingService

        return PricingService.to_api_breakdown(breakdown)
