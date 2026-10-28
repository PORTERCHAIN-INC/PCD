"""Partner / marketplace barcodes that resolve to a PorterChain package.

A merchant (or an integration such as Shopify) registers the barcode already printed on a
box; the driver can then scan that barcode instead of the PorterChain PC1 label and the scan
lookup resolves it to the same package (always scoped to the order being scanned).
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package, PackageExternalIdentifier

SOURCES = frozenset({"shopify", "merchant", "marketplace", "partner_carrier"})
_STRIP = re.compile(r"[\s\-]+")
MAX_LEN = 128


def partner_barcodes_enabled(db: Session, order: Order) -> bool:
    """Ops switch per merchant: ``profile.custody.partner_barcodes_enabled`` (default on).

    Set by staff through ``PATCH /v1/admin/merchants/{id}`` (``partner_barcodes_enabled``).
    When off, no new partner barcodes can be registered and scans only accept PC1 labels.
    """
    from porterchain_api.merchant_models import Merchant

    merchant = db.get(Merchant, order.merchant_id) if order.merchant_id else None
    custody = ((merchant.profile or {}).get("custody") or {}) if merchant else {}
    return custody.get("partner_barcodes_enabled", True) is not False


def normalize(value: str) -> str:
    return _STRIP.sub("", (value or "").strip()).upper()


class ExternalIdentifierService:
    def list_for_order(self, db: Session, order: Order) -> list[PackageExternalIdentifier]:
        return (
            db.query(PackageExternalIdentifier)
            .filter(PackageExternalIdentifier.order_id == order.id)
            .order_by(PackageExternalIdentifier.created_at.asc())
            .all()
        )

    def register(
        self,
        db: Session,
        order: Order,
        package_id: str,
        *,
        source: str,
        value: str,
        created_by: str | None = None,
    ) -> PackageExternalIdentifier:
        if not partner_barcodes_enabled(db, order):
            raise ValueError("partner_barcodes_disabled")
        src = (source or "").strip().lower()
        if src not in SOURCES:
            raise ValueError("external_id_source_invalid")
        norm = normalize(value)
        if not norm or len(norm) > MAX_LEN:
            raise ValueError("external_id_value_invalid")
        pkg = db.query(Package).filter(Package.id == package_id, Package.order_id == order.id).first()
        if not pkg:
            raise LookupError("package_not_found")
        existing = (
            db.query(PackageExternalIdentifier)
            .filter(PackageExternalIdentifier.source == src, PackageExternalIdentifier.value_normalized == norm)
            .first()
        )
        if existing:
            if existing.package_id == pkg.id:
                return existing
            raise ValueError("external_id_already_assigned")
        row = PackageExternalIdentifier(
            package_id=pkg.id,
            order_id=order.id,
            source=src,
            value=value.strip()[:MAX_LEN],
            value_normalized=norm,
            created_by=created_by,
        )
        db.add(row)
        try:
            db.flush()
        except IntegrityError as exc:  # concurrent duplicate
            raise ValueError("external_id_already_assigned") from exc
        return row

    def remove(self, db: Session, order: Order, identifier_id: str) -> bool:
        row = (
            db.query(PackageExternalIdentifier)
            .filter(PackageExternalIdentifier.id == identifier_id, PackageExternalIdentifier.order_id == order.id)
            .first()
        )
        if not row:
            return False
        db.delete(row)
        db.flush()
        return True

    def resolve(self, db: Session, order: Order, raw: str) -> Package | None:
        """The package on ``order`` that ``raw`` was registered for, if any."""
        norm = normalize(raw)
        if not norm or not partner_barcodes_enabled(db, order):
            return None
        row = (
            db.query(PackageExternalIdentifier)
            .filter(
                PackageExternalIdentifier.value_normalized == norm,
                PackageExternalIdentifier.order_id == order.id,
            )
            .first()
        )
        return db.get(Package, row.package_id) if row else None

    @staticmethod
    def packages_for_order(db: Session, order: Order) -> list[dict[str, Any]]:
        rows = db.query(Package).filter(Package.order_id == order.id).order_by(Package.parcel_index.asc()).all()
        return [
            {
                "id": p.id,
                "parcel_index": p.parcel_index,
                "total_parcels": p.total_parcels,
                "tracking_suffix": p.tracking_suffix,
                "status": p.status,
            }
            for p in rows
        ]

    @staticmethod
    def serialize(row: PackageExternalIdentifier) -> dict[str, Any]:
        return {
            "id": row.id,
            "package_id": row.package_id,
            "source": row.source,
            "value": row.value,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
