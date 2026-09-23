"""ScanGate — all packages scanned before pickup/delivery confirm (and COD)."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package
from porterchain_api.merchant_engine.package_service import PackageService
from porterchain_api.reporting.qr_codec import InvalidLabelQr, decode_label_qr

Phase = Literal["pickup", "delivery"]

STATUS_MANIFESTED = "manifested"
STATUS_PICKED_UP = "picked_up"
STATUS_LOADED = "loaded"
STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
STATUS_DELIVERED = "delivered"

_PICKUP_DONE = frozenset(
    {STATUS_PICKED_UP, STATUS_LOADED, STATUS_OUT_FOR_DELIVERY, STATUS_DELIVERED}
)
_DELIVERY_DONE = frozenset({STATUS_DELIVERED})


class PackagesIncomplete(Exception):
    """Map to HTTP 409 packages_incomplete."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        super().__init__("packages_incomplete")


def _whole_vehicle(order: Order) -> bool:
    """A hired vehicle has no parcel labels. Scan-gate must not block pickup or delivery."""
    meta = order.compliance_metadata if isinstance(getattr(order, "compliance_metadata", None), dict) else {}
    if meta.get("booking_mode") == "vehicle":
        return True
    parcels = meta.get("parcels")
    return isinstance(parcels, dict) and parcels.get("booking_mode") == "vehicle"


class ScanGateService:
    def __init__(self) -> None:
        self._packages = PackageService()

    def package_rows(self, db: Session, order: Order) -> list[dict[str, Any]]:
        if _whole_vehicle(order):
            return []
        rows = self._packages.ensure_for_order(db, order)
        return [
            {
                "id": p.id,
                "parcel_index": p.parcel_index,
                "total_parcels": p.total_parcels,
                "tracking_suffix": p.tracking_suffix,
                "status": p.status,
                "weight_kg": float(p.weight_kg) if p.weight_kg is not None else None,
                "dimensions": p.dimensions,
                "preset_label": (p.dimensions or {}).get("preset_label") or (p.dimensions or {}).get("display_name")
                if isinstance(p.dimensions, dict)
                else None,
                "instructions": (p.dimensions or {}).get("instructions") if isinstance(p.dimensions, dict) else None,
                "scanned_pickup": p.status in _PICKUP_DONE,
                "scanned_delivery": p.status in _DELIVERY_DONE,
            }
            for p in rows
        ]

    def progress_by_order_ids(self, db: Session, order_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Read-only parcel rollup. Does not create package rows."""
        empty_scan = {
            "scanned": 0,
            "required": 0,
            "complete": False,
            "missing_suffixes": [],
        }
        if not order_ids:
            return {}
        rows = db.query(Package).filter(Package.order_id.in_(order_ids)).all()
        by_order: dict[str, list[Package]] = {oid: [] for oid in order_ids}
        for pkg in rows:
            by_order.setdefault(pkg.order_id, []).append(pkg)
        out: dict[str, dict[str, Any]] = {}
        for oid, pkgs in by_order.items():
            pickup_missing = [p for p in pkgs if p.status not in _PICKUP_DONE]
            delivery_missing = [p for p in pkgs if p.status not in _DELIVERY_DONE]
            required = len(pkgs)
            out[oid] = {
                "scan_pickup": {
                    "scanned": required - len(pickup_missing),
                    "required": required,
                    "complete": required > 0 and not pickup_missing,
                    "missing_suffixes": [p.tracking_suffix for p in pickup_missing],
                },
                "scan_delivery": {
                    "scanned": required - len(delivery_missing),
                    "required": required,
                    "complete": required > 0 and not delivery_missing,
                    "missing_suffixes": [p.tracking_suffix for p in delivery_missing],
                },
            }
        for oid in order_ids:
            out.setdefault(oid, {"scan_pickup": dict(empty_scan), "scan_delivery": dict(empty_scan)})
        return out

    def scan_progress(self, db: Session, order: Order, *, phase: Phase) -> dict[str, Any]:
        if _whole_vehicle(order):
            return {
                "phase": phase,
                "scanned": 0,
                "required": 0,
                "complete": True,
                "missing_suffixes": [],
                "packages": [],
            }
        rows = self._packages.ensure_for_order(db, order)
        required = _PICKUP_DONE if phase == "pickup" else _DELIVERY_DONE
        missing = [p for p in rows if p.status not in required]
        scanned = len(rows) - len(missing)
        return {
            "phase": phase,
            "scanned": scanned,
            "required": len(rows),
            "complete": len(missing) == 0 and len(rows) > 0,
            "missing_suffixes": [p.tracking_suffix for p in missing],
            "packages": self.package_rows(db, order),
        }

    def assert_complete(self, db: Session, order: Order, *, phase: Phase) -> None:
        progress = self.scan_progress(db, order, phase=phase)
        if progress["complete"]:
            return
        raise PackagesIncomplete(
            {
                "error": "packages_incomplete",
                "phase": phase,
                "scanned": progress["scanned"],
                "required": progress["required"],
                "missing_suffixes": progress["missing_suffixes"],
            }
        )

    def assert_cod_scans(self, db: Session, order: Order) -> None:
        """COD Payment Link requires pickup scans (boxes accounted for)."""
        self.assert_complete(db, order, phase="pickup")

    def _package_for_scan(self, db: Session, order: Order, raw: str) -> Package:
        """LOGISTICSv1 QR first; else unique tracking_suffix / barcode on this order."""
        token = (raw or "").strip()
        if not token:
            raise ValueError("invalid_label_qr")
        self._packages.ensure_for_order(db, order)
        try:
            decoded = decode_label_qr(token)
        except InvalidLabelQr:
            decoded = None
        if decoded is not None:
            if decoded.order_id != order.id:
                raise ValueError("qr_order_mismatch")
            pkg = (
                db.query(Package)
                .filter(Package.id == decoded.package_id, Package.order_id == order.id)
                .first()
            )
            if not pkg:
                raise LookupError("package_not_found")
            return pkg
        pkg = (
            db.query(Package)
            .filter(or_(Package.tracking_suffix == token, Package.barcode == token))
            .first()
        )
        if not pkg:
            raise ValueError("invalid_label_qr")
        if pkg.order_id != order.id:
            raise ValueError("qr_order_mismatch")
        return pkg

    def scan_qr(
        self,
        db: Session,
        order: Order,
        qr_payload: str,
        *,
        phase: Phase,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        pkg = self._package_for_scan(db, order, qr_payload)

        if phase == "pickup":
            if pkg.status not in _PICKUP_DONE:
                pkg.status = STATUS_PICKED_UP
        else:
            if pkg.status == STATUS_MANIFESTED:
                raise ValueError("scan_pickup_required_first")
            pkg.status = STATUS_DELIVERED

        db.add(pkg)
        db.flush()
        progress = self.scan_progress(db, order, phase=phase)
        result = {
            "package_id": pkg.id,
            "tracking_suffix": pkg.tracking_suffix,
            "status": pkg.status,
            "actor_id": actor_id,
            **progress,
        }
        db.commit()
        return result

    def scan_qr_from_body(
        self,
        db: Session,
        order: Order,
        body: dict[str, Any] | None,
        *,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        qr = (body or {}).get("qr_payload") or (body or {}).get("qr") or ""
        phase = str((body or {}).get("phase") or "pickup").lower()
        if phase not in ("pickup", "delivery"):
            raise ValueError("phase_must_be_pickup_or_delivery")
        return self.scan_qr(db, order, str(qr), phase=phase, actor_id=actor_id)
