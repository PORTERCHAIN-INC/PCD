"""Pricing administration — rules, contracts, promotions, simulator.

All commercial price calculation delegates to porterchain_pricing (masterrule §11).
This service manages rules, config, and admin views only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, MerchantContract, PricingTariff, PricingZone, Promotion, SystemConfig
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.merchant_models import Merchant
from porterchain_api.models import Order, Quote
from porterchain_api.pricing_engine import get_pricing_simulator
from porterchain_pricing import GeoPoint, PricingRequest

TARIFF_TYPES = frozenset({
    "public",
    "merchant",
    "contract",
    "zone",
    "distance",
    "weight",
    "volume",
    "vehicle",
    "express",
    "same_day",
    "scheduled",
    "recurring",
    "return",
    "bulk",
    "minimum",
    "maximum",
    "fuel",
    "waiting",
    "loading",
    "holiday",
    "weekend",
    "after_hours",
    "rush",
    "cancellation",
    "failed_delivery",
    "redelivery",
    "manual",
    "tax",
    "discount",
})

RULE_STATUSES = frozenset({"draft", "pending_approval", "approved", "published", "archived"})


def _meta(record: PricingTariff | Promotion | MerchantContract) -> dict[str, Any]:
    cfg = dict(getattr(record, "config", None) or getattr(record, "rules", None) or {})
    return dict(cfg.get("_meta") or {})


def _set_meta(record: PricingTariff | Promotion, **updates: Any) -> None:
    cfg = dict(record.config or {})
    meta = dict(cfg.get("_meta") or {})
    meta.update(updates)
    cfg["_meta"] = meta
    record.config = cfg


@dataclass
class PricingFilters:
    tariff_type: str | None = None
    vehicle_class: str | None = None
    merchant_id: str | None = None
    zone: str | None = None
    status: str | None = None
    search: str | None = None
    include_inactive: bool = False
    limit: int = 500


class AdminPricingService:
    # ------------------------------------------------------------------ #
    # Tariffs
    # ------------------------------------------------------------------ #
    def list_tariffs(self, db: Session, *, tariff_type: str | None = None) -> list[PricingTariff]:
        q = db.query(PricingTariff).filter(PricingTariff.is_active.is_(True))
        if tariff_type:
            q = q.filter(PricingTariff.tariff_type == tariff_type)
        return q.order_by(PricingTariff.name).all()

    def list_tariffs_enriched(self, db: Session, filters: PricingFilters) -> list[dict[str, Any]]:
        q = db.query(PricingTariff).order_by(PricingTariff.created_at.desc())
        if not filters.include_inactive:
            q = q.filter(PricingTariff.is_active.is_(True))
        if filters.tariff_type:
            q = q.filter(PricingTariff.tariff_type == filters.tariff_type)
        if filters.vehicle_class:
            q = q.filter(PricingTariff.vehicle_class == filters.vehicle_class)
        if filters.merchant_id:
            q = q.filter(PricingTariff.merchant_id == filters.merchant_id)
        if filters.zone:
            q = q.filter(PricingTariff.zone == filters.zone)
        if filters.search:
            like = f"%{filters.search}%"
            q = q.filter(or_(PricingTariff.name.ilike(like), PricingTariff.zone.ilike(like)))
        merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
        rows: list[dict[str, Any]] = []
        for t in q.limit(filters.limit).all():
            meta = _meta(t)
            status = meta.get("status", "published" if t.is_active else "archived")
            if filters.status and status != filters.status:
                continue
            rows.append(self._tariff_row(t, merchants, meta, status))
        return rows

    def _tariff_row(
        self,
        t: PricingTariff,
        merchants: dict[str, str],
        meta: dict[str, Any],
        status: str,
    ) -> dict[str, Any]:
        return {
            "id": t.id,
            "name": t.name,
            "tariff_type": t.tariff_type,
            "vehicle_class": t.vehicle_class,
            "zone": t.zone,
            "merchant_id": t.merchant_id,
            "merchant_name": merchants.get(t.merchant_id) if t.merchant_id else None,
            "base_cents": t.base_cents,
            "per_km_cents": t.per_km_cents,
            "fuel_surcharge_percent": t.fuel_surcharge_percent,
            "is_active": t.is_active,
            "status": status,
            "version": int(meta.get("version", 1)),
            "priority": int(meta.get("priority", 100)),
            "effective_from": meta.get("effective_from"),
            "effective_to": meta.get("effective_to"),
            "created_at": t.created_at,
            "config": dict(t.config or {}),
        }

    def create_tariff(self, db: Session, ctx: AdminContext, **fields) -> PricingTariff:
        config = dict(fields.pop("config", {}) or {})
        meta = dict(config.get("_meta") or {})
        meta.setdefault("status", "draft")
        meta.setdefault("version", 1)
        meta["created_by"] = ctx.user.id
        config["_meta"] = meta
        record = PricingTariff(**fields, config=config)
        db.add(record)
        db.flush()
        log_admin_audit(
            db, ctx, action="pricing.tariff.create", resource_type="pricing_tariff", resource_id=record.id
        )
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

    def update_tariff(self, db: Session, ctx: AdminContext, tariff_id: str, **fields) -> PricingTariff:
        record = db.query(PricingTariff).filter(PricingTariff.id == tariff_id).first()
        if not record:
            raise LookupError("tariff_not_found")
        for key, val in fields.items():
            if key == "config" and val is not None:
                record.config = val
            elif hasattr(record, key) and val is not None:
                setattr(record, key, val)
        meta = _meta(record)
        meta["version"] = int(meta.get("version", 1)) + 1
        meta["updated_by"] = ctx.user.id
        _set_meta(record, **meta)
        db.flush()
        log_admin_audit(db, ctx, action="pricing.tariff.update", resource_type="pricing_tariff", resource_id=record.id)
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

    def publish_tariff(self, db: Session, ctx: AdminContext, tariff_id: str) -> PricingTariff:
        record = db.query(PricingTariff).filter(PricingTariff.id == tariff_id).first()
        if not record:
            raise LookupError("tariff_not_found")
        record.is_active = True
        _set_meta(record, status="published", published_at=datetime.now(UTC).isoformat(), published_by=ctx.user.id)
        db.flush()
        log_admin_audit(db, ctx, action="pricing.tariff.publish", resource_type="pricing_tariff", resource_id=record.id)
        db.commit()
        db.refresh(record)
        return record

    # ------------------------------------------------------------------ #
    # Promotions
    # ------------------------------------------------------------------ #
    def list_promotions(self, db: Session, *, merchant_id: str | None = None) -> list[Promotion]:
        q = db.query(Promotion).order_by(Promotion.created_at.desc())
        if merchant_id:
            q = q.filter(Promotion.merchant_id == merchant_id)
        return q.all()

    def list_promotions_enriched(self, db: Session) -> list[dict[str, Any]]:
        merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
        return [
            {
                "id": p.id,
                "code": p.code,
                "promotion_type": p.promotion_type,
                "merchant_id": p.merchant_id,
                "merchant_name": merchants.get(p.merchant_id) if p.merchant_id else None,
                "discount_percent": p.discount_percent,
                "discount_cents": p.discount_cents,
                "is_active": p.is_active,
                "expires_at": p.expires_at,
                "status": _meta(p).get("status", "published" if p.is_active else "archived"),
                "created_at": p.created_at,
            }
            for p in self.list_promotions(db)
        ]

    def create_promotion(self, db: Session, ctx: AdminContext | None, code: str, **fields) -> Promotion:
        config = dict(fields.pop("config", {}) or {})
        config.setdefault("_meta", {"status": "published", "version": 1})
        record = Promotion(code=code, **fields, config=config)
        db.add(record)
        db.flush()
        log_admin_audit(
            db,
            ctx,
            action="pricing.promotion.create",
            resource_type="promotion",
            resource_id=record.id,
            payload={"code": code},
        )
        db.commit()
        db.refresh(record)
        return record

    # ------------------------------------------------------------------ #
    # Zones & contracts
    # ------------------------------------------------------------------ #
    def list_zones(self, db: Session) -> list[PricingZone]:
        return db.query(PricingZone).filter(PricingZone.is_active.is_(True)).order_by(PricingZone.code).all()

    def list_zones_enriched(self, db: Session) -> list[dict[str, Any]]:
        return [
            {
                "id": z.id,
                "code": z.code,
                "name": z.name,
                "multiplier": z.multiplier,
                "is_active": z.is_active,
                "bounds": dict(z.bounds or {}),
                "created_at": z.created_at,
            }
            for z in db.query(PricingZone).order_by(PricingZone.code).all()
        ]

    def create_zone(self, db: Session, ctx: AdminContext | None, **fields) -> PricingZone:
        record = PricingZone(**fields)
        db.add(record)
        db.flush()
        log_admin_audit(db, ctx, action="pricing.zone.create", resource_type="pricing_zone", resource_id=record.id)
        db.commit()
        db.refresh(record)
        return record

    def list_contracts(self, db: Session, *, merchant_id: str | None = None) -> list[MerchantContract]:
        q = db.query(MerchantContract).filter(MerchantContract.is_active.is_(True))
        if merchant_id:
            q = q.filter(MerchantContract.merchant_id == merchant_id)
        return q.order_by(MerchantContract.created_at.desc()).all()

    def list_contracts_enriched(self, db: Session, *, merchant_id: str | None = None) -> list[dict[str, Any]]:
        merchants = {m.id: m.company_name for m in db.query(Merchant).all()}
        rows = []
        for c in self.list_contracts(db, merchant_id=merchant_id):
            rows.append(
                {
                    "id": c.id,
                    "merchant_id": c.merchant_id,
                    "merchant_name": merchants.get(c.merchant_id),
                    "name": c.name,
                    "minimum_monthly_commitment_cents": c.minimum_monthly_commitment_cents,
                    "is_active": c.is_active,
                    "effective_from": c.effective_from,
                    "effective_to": c.effective_to,
                    "rules": dict(c.rules or {}),
                    "created_at": c.created_at,
                }
            )
        return rows

    def create_contract(self, db: Session, ctx: AdminContext, **fields) -> MerchantContract:
        record = MerchantContract(**fields)
        db.add(record)
        db.flush()
        log_admin_audit(
            db,
            ctx,
            action="pricing.contract.create",
            resource_type="merchant_contract",
            resource_id=record.id,
        )
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

    # ------------------------------------------------------------------ #
    # Tax / fuel
    # ------------------------------------------------------------------ #
    def get_tax_config(self, db: Session) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
        return dict(row.value) if row else {"hst_percent": 13.0, "tax_included": False, "gst_percent": 5.0, "pst_percent": 0.0}

    def update_tax_config(self, db: Session, ctx: AdminContext | None, value: dict) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_tax").first()
        if not row:
            row = SystemConfig(key="pricing_tax", value=value)
            db.add(row)
        else:
            row.value = value
        db.flush()
        log_admin_audit(db, ctx, action="pricing.tax.update", resource_type="system_config", resource_id="pricing_tax")
        db.commit()
        return value

    def get_fuel_config(self, db: Session) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        return dict(row.value) if row else {"surcharge_percent": 8.5}

    def update_fuel_config(self, db: Session, ctx: AdminContext | None, value: dict) -> dict:
        row = db.query(SystemConfig).filter(SystemConfig.key == "pricing_fuel").first()
        if not row:
            row = SystemConfig(key="pricing_fuel", value=value)
            db.add(row)
        else:
            row.value = value
        db.flush()
        log_admin_audit(db, ctx, action="pricing.fuel.update", resource_type="system_config", resource_id="pricing_fuel")
        db.commit()
        return value

    # ------------------------------------------------------------------ #
    # Dashboard / reports / conflicts
    # ------------------------------------------------------------------ #
    def dashboard(self, db: Session) -> dict[str, Any]:
        now = datetime.now(UTC).replace(tzinfo=None)
        week_ago = now - timedelta(days=7)

        active_tariffs = db.query(func.count(PricingTariff.id)).filter(PricingTariff.is_active.is_(True)).scalar() or 0
        vehicle_rules = (
            db.query(func.count(PricingTariff.id))
            .filter(PricingTariff.is_active.is_(True), PricingTariff.tariff_type == "vehicle")
            .scalar()
            or 0
        )
        distance_rules = (
            db.query(func.count(PricingTariff.id))
            .filter(PricingTariff.is_active.is_(True), PricingTariff.tariff_type == "distance")
            .scalar()
            or 0
        )
        weight_rules = (
            db.query(func.count(PricingTariff.id))
            .filter(PricingTariff.is_active.is_(True), PricingTariff.tariff_type == "weight")
            .scalar()
            or 0
        )

        recent_changes = (
            db.query(AdminAuditLog)
            .filter(AdminAuditLog.action.like("pricing.%"), AdminAuditLog.created_at >= week_ago)
            .order_by(AdminAuditLog.created_at.desc())
            .limit(10)
            .all()
        )

        upcoming = []
        for c in db.query(MerchantContract).filter(MerchantContract.effective_from > now).limit(10).all():
            upcoming.append(
                {"type": "contract", "id": c.id, "name": c.name, "effective_from": c.effective_from}
            )

        month_start = datetime(now.year, now.month, 1)
        revenue = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(Order.created_at >= month_start)
            .scalar()
            or 0
        )
        quotes = db.query(func.count(Quote.id)).filter(Quote.created_at >= month_start).scalar() or 0

        return {
            "active_pricing_rules": int(active_tariffs),
            "merchant_contracts": db.query(func.count(MerchantContract.id)).filter(MerchantContract.is_active.is_(True)).scalar() or 0,
            "vehicle_pricing_rules": int(vehicle_rules),
            "zone_pricing_rules": db.query(func.count(PricingZone.id)).filter(PricingZone.is_active.is_(True)).scalar() or 0,
            "distance_pricing_rules": int(distance_rules),
            "weight_pricing_rules": int(weight_rules),
            "fuel_surcharge_percent": self.get_fuel_config(db).get("surcharge_percent", 8.5),
            "tax_hst_percent": self.get_tax_config(db).get("hst_percent", 13.0),
            "active_coupons": db.query(func.count(Promotion.id)).filter(Promotion.is_active.is_(True)).scalar() or 0,
            "active_promotions": db.query(func.count(Promotion.id)).filter(Promotion.is_active.is_(True)).scalar() or 0,
            "revenue_forecast_cents": int(revenue * 1.05),
            "monthly_quotes": int(quotes),
            "recent_changes": [
                {
                    "action": a.action,
                    "resource_type": a.resource_type,
                    "resource_id": a.resource_id,
                    "created_at": a.created_at,
                }
                for a in recent_changes
            ],
            "upcoming_scheduled": upcoming,
            "conflict_count": len(self.detect_conflicts(db)),
        }

    def reports(self, db: Session) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for t in db.query(PricingTariff).filter(PricingTariff.is_active.is_(True)).all():
            by_type[t.tariff_type] = by_type.get(t.tariff_type, 0) + 1

        month_start = datetime.now(UTC).replace(tzinfo=None).replace(day=1)
        avg_order = (
            db.query(func.avg(Order.amount_cents))
            .filter(Order.created_at >= month_start)
            .scalar()
            or 0
        )
        changes = (
            db.query(func.count(AdminAuditLog.id))
            .filter(AdminAuditLog.action.like("pricing.%"), AdminAuditLog.created_at >= month_start)
            .scalar()
            or 0
        )

        return {
            "rules_by_type": sorted(by_type.items(), key=lambda x: -x[1]),
            "active_coupons": db.query(func.count(Promotion.id)).filter(Promotion.is_active.is_(True)).scalar() or 0,
            "avg_order_value_cents": int(avg_order),
            "pricing_changes_month": int(changes),
            "active_contracts": db.query(func.count(MerchantContract.id)).filter(MerchantContract.is_active.is_(True)).scalar() or 0,
        }

    def detect_conflicts(self, db: Session) -> list[dict[str, Any]]:
        """Heuristic duplicate / overlapping rule detection."""
        tariffs = db.query(PricingTariff).filter(PricingTariff.is_active.is_(True)).all()
        seen: dict[tuple, str] = {}
        conflicts: list[dict[str, Any]] = []
        for t in tariffs:
            key = (t.tariff_type, t.vehicle_class or "", t.zone or "", t.merchant_id or "")
            if key in seen:
                conflicts.append(
                    {
                        "type": "duplicate",
                        "tariff_id": t.id,
                        "conflicts_with": seen[key],
                        "message": f"Duplicate rule: {t.name} ({t.tariff_type})",
                    }
                )
            else:
                seen[key] = t.id
        return conflicts

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

        result = PricingService.to_api_breakdown(breakdown)
        result["rules_applied"] = breakdown.metadata.get("rules_applied", breakdown.metadata)
        return result
