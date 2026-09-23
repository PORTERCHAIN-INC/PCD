"""Admin FSA rate CRUD — keep pricing_components router thin."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import PricingFsaRate
from porterchain_api.schemas_pricing import FsaRateBody, FsaRateOut
from porterchain_pricing.components import normalize_fsa
from porterchain_pricing.gta150_fsa import is_gta150_fsa


class FsaAdminService:
    def validated_fsa(
        self,
        value: str | None,
        *,
        field: str,
        required: bool,
        require_in_tile: bool = True,
    ) -> str | None:
        if not value:
            if required:
                raise ValueError(f"{field}_required")
            return None
        normalized = normalize_fsa(value)
        if not normalized:
            raise ValueError(f"{field}_invalid: expected a form like M5V")
        if require_in_tile and not is_gta150_fsa(normalized):
            raise ValueError(f"{field}_out_of_gta150_tile: {normalized}")
        return normalized

    def to_out(self, row: PricingFsaRate) -> FsaRateOut:
        return FsaRateOut(
            id=row.id,
            dest_fsa=row.dest_fsa,
            flat_cents=row.flat_cents,
            merchant_id=row.merchant_id,
            origin_fsa=row.origin_fsa,
            vehicle_class=row.vehicle_class,
            includes_location_fees=bool(row.includes_location_fees),
            label=row.label,
            is_active=bool(row.is_active),
            config=dict(row.config or {}) or None,
        )

    def list_rates(
        self, db: Session, *, merchant_id: str | None = None, dest_fsa: str | None = None
    ) -> list[FsaRateOut]:
        q = db.query(PricingFsaRate)
        if merchant_id:
            q = q.filter(PricingFsaRate.merchant_id == merchant_id)
        if dest_fsa:
            q = q.filter(PricingFsaRate.dest_fsa == normalize_fsa(dest_fsa))
        rows = q.order_by(PricingFsaRate.dest_fsa, PricingFsaRate.flat_cents).all()
        return [self.to_out(r) for r in rows]

    def create_rate(self, db: Session, body: FsaRateBody) -> FsaRateOut:
        row = PricingFsaRate(
            dest_fsa=self.validated_fsa(body.dest_fsa, field="dest_fsa", required=True),
            origin_fsa=self.validated_fsa(body.origin_fsa, field="origin_fsa", required=False),
            flat_cents=body.flat_cents,
            merchant_id=body.merchant_id,
            vehicle_class=body.vehicle_class,
            includes_location_fees=body.includes_location_fees,
            label=body.label,
            is_active=body.is_active,
            config=dict(body.config or {}),
        )
        db.add(row)
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            raise ValueError("fsa_rate_already_exists") from exc
        db.refresh(row)
        return self.to_out(row)

    def update_rate(self, db: Session, rate_id: str, body: FsaRateBody) -> FsaRateOut:
        row = db.query(PricingFsaRate).filter(PricingFsaRate.id == rate_id).first()
        if not row:
            raise LookupError("fsa_rate_not_found")
        row.dest_fsa = self.validated_fsa(body.dest_fsa, field="dest_fsa", required=True)
        row.origin_fsa = self.validated_fsa(body.origin_fsa, field="origin_fsa", required=False)
        row.flat_cents = body.flat_cents
        row.merchant_id = body.merchant_id
        row.vehicle_class = body.vehicle_class
        row.includes_location_fees = body.includes_location_fees
        row.label = body.label
        row.is_active = body.is_active
        if body.config is not None:
            row.config = dict(body.config)
        db.commit()
        db.refresh(row)
        return self.to_out(row)

    def delete_rate(self, db: Session, rate_id: str) -> None:
        row = db.query(PricingFsaRate).filter(PricingFsaRate.id == rate_id).first()
        if not row:
            raise LookupError("fsa_rate_not_found")
        db.delete(row)
        db.commit()

    def bulk_upsert(
        self,
        db: Session,
        rows: list[FsaRateBody],
        *,
        merchant_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or update dest_fsa flats. Rejects out-of-tile codes (no silent Ottawa K*)."""
        created = updated = 0
        errors: list[dict[str, str]] = []
        for i, body in enumerate(rows):
            try:
                dest = self.validated_fsa(body.dest_fsa, field="dest_fsa", required=True)
                origin = self.validated_fsa(body.origin_fsa, field="origin_fsa", required=False)
                mid = merchant_id if merchant_id is not None else body.merchant_id
                q = db.query(PricingFsaRate).filter(PricingFsaRate.dest_fsa == dest)
                if mid is not None:
                    q = q.filter(PricingFsaRate.merchant_id == mid)
                else:
                    q = q.filter(PricingFsaRate.merchant_id.is_(None))
                if origin:
                    q = q.filter(PricingFsaRate.origin_fsa == origin)
                else:
                    q = q.filter(PricingFsaRate.origin_fsa.is_(None))
                if body.vehicle_class:
                    q = q.filter(PricingFsaRate.vehicle_class == body.vehicle_class)
                else:
                    q = q.filter(PricingFsaRate.vehicle_class.is_(None))
                existing = q.first()
                if existing:
                    existing.flat_cents = body.flat_cents
                    existing.includes_location_fees = body.includes_location_fees
                    existing.label = body.label
                    existing.is_active = body.is_active
                    if body.config is not None:
                        existing.config = dict(body.config)
                    updated += 1
                else:
                    db.add(
                        PricingFsaRate(
                            dest_fsa=dest,
                            origin_fsa=origin,
                            flat_cents=body.flat_cents,
                            merchant_id=mid,
                            vehicle_class=body.vehicle_class,
                            includes_location_fees=body.includes_location_fees,
                            label=body.label,
                            is_active=body.is_active,
                            config=dict(body.config or {}),
                        )
                    )
                    created += 1
            except ValueError as exc:
                errors.append(
                    {"index": str(i), "dest_fsa": body.dest_fsa or "", "error": str(exc)}
                )
        if created or updated:
            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                raise ValueError(f"fsa_bulk_commit_failed: {exc}") from exc
        return {
            "created": created,
            "updated": updated,
            "error_count": len(errors),
            "errors": errors[:40],
            "note": (
                "Out-of-tile FSAs are rejected. Unrated in-tile destinations "
                "use Valhalla distance floor when pricing_model=fsa."
            ),
        }

    def coverage_gap(
        self, db: Session, *, merchant_id: str | None = None
    ) -> dict[str, object]:
        """GTA150 tile vs priced FSA rows — admin checklist (Phase 1 / 2c)."""
        from porterchain_pricing.gta150_fsa import gta150_fsa_codes, gta150_registry_meta

        tile = gta150_fsa_codes()
        q = db.query(PricingFsaRate.dest_fsa).filter(PricingFsaRate.is_active.is_(True))
        if merchant_id:
            q = q.filter(PricingFsaRate.merchant_id == merchant_id)
        else:
            q = q.filter(PricingFsaRate.merchant_id.is_(None))
        rated = {str(r[0]).upper() for r in q.distinct().all() if r[0]}
        missing = sorted(tile - rated)
        extra = sorted(rated - tile)
        meta = gta150_registry_meta()
        return {
            "tile_fsa_count": len(tile),
            "rated_in_tile_count": len(tile & rated),
            "missing_rate_count": len(missing),
            "extra_out_of_tile_count": len(extra),
            "missing_sample": missing[:40],
            "extra_sample": extra[:20],
            "registry": meta,
            "scope": "merchant" if merchant_id else "platform",
            "merchant_id": merchant_id,
            "note": (
                "Unrated in-tile FSAs fall through to Valhalla distance floor. "
                "Do not invent CAD flats without pricing sign-off."
            ),
        }
