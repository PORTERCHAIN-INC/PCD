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
#: Not at pickup; the driver reported it with a photo. Accounted for at pickup,
#: never expected at delivery (it was never loaded).
STATUS_MISSING_AT_PICKUP = "missing_at_pickup"

_PICKUP_DONE = frozenset(
    {STATUS_PICKED_UP, STATUS_LOADED, STATUS_OUT_FOR_DELIVERY, STATUS_DELIVERED}
)
_PICKUP_ACCOUNTED = _PICKUP_DONE | {STATUS_MISSING_AT_PICKUP}
_DELIVERY_DONE = frozenset({STATUS_DELIVERED})
MISSING_REASONS = frozenset({"not_ready", "not_found", "damaged", "wrong_item", "other"})


def _phase_progress(rows: list[Package], phase: str) -> tuple[int, int, list[Package], int]:
    """(scanned, required, outstanding, missing) — missing boxes leave the delivery count."""
    missing = [p for p in rows if p.status == STATUS_MISSING_AT_PICKUP]
    if phase == "pickup":
        outstanding = [p for p in rows if p.status not in _PICKUP_ACCOUNTED]
        scanned = len([p for p in rows if p.status in _PICKUP_DONE])
        return scanned, len(rows), outstanding, len(missing)
    carried = [p for p in rows if p.status != STATUS_MISSING_AT_PICKUP]
    outstanding = [p for p in carried if p.status not in _DELIVERY_DONE]
    return len(carried) - len(outstanding), len(carried), outstanding, len(missing)


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
                "missing_at_pickup": p.status == STATUS_MISSING_AT_PICKUP,
                "item_key": getattr(p, "item_key", None),
                "box_index": getattr(p, "box_index", None),
                "box_count": getattr(p, "box_count", None),
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
            p_scanned, p_required, p_out, p_missing = _phase_progress(pkgs, "pickup")
            d_scanned, d_required, d_out, _ = _phase_progress(pkgs, "delivery")
            out[oid] = {
                "scan_pickup": {
                    "scanned": p_scanned,
                    "required": p_required,
                    "complete": p_required > 0 and not p_out,
                    "missing_suffixes": [p.tracking_suffix for p in p_out],
                    "reported_missing": p_missing,
                },
                "scan_delivery": {
                    "scanned": d_scanned,
                    "required": d_required,
                    "complete": d_required > 0 and not d_out,
                    "missing_suffixes": [p.tracking_suffix for p in d_out],
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
        scanned, required, outstanding, reported = _phase_progress(rows, phase)
        return {
            "phase": phase,
            "scanned": scanned,
            "required": required,
            "complete": len(outstanding) == 0 and required > 0,
            "missing_suffixes": [p.tracking_suffix for p in outstanding],
            "reported_missing": reported,
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
            if pkg.status in (STATUS_MANIFESTED, STATUS_MISSING_AT_PICKUP):
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

    def pickup_checklist(self, db: Session, order: Order) -> dict[str, Any]:
        """
        Pickup checklist grouped by item: each multi-box item lists its boxes
        (n of N); a single parcel is its own one-box item. Item names are
        "Item n" / "Parcel n" — never contents, same as the labels.
        """
        from porterchain_api.merchant_engine.package_service import item_ordinals

        rows = [] if _whole_vehicle(order) else self._packages.ensure_for_order(db, order)
        ordinals = item_ordinals(rows)
        items: dict[str, dict[str, Any]] = {}
        for pkg in sorted(rows, key=lambda r: r.parcel_index or 0):
            multi = bool(pkg.item_key and (pkg.box_count or 0) > 1)
            key = pkg.item_key if multi else f"parcel:{pkg.id}"
            entry = items.get(key)
            if entry is None:
                entry = items[key] = {
                    "item_key": pkg.item_key if multi else None,
                    "label": f"Item {ordinals[pkg.item_key]}" if multi else f"Parcel {pkg.parcel_index}",
                    "box_count": pkg.box_count if multi else 1,
                    "boxes": [],
                }
            entry["boxes"].append(
                {
                    "package_id": pkg.id,
                    "box_index": pkg.box_index if multi else 1,
                    "parcel_index": pkg.parcel_index,
                    "tracking_suffix": pkg.tracking_suffix,
                    "status": pkg.status,
                    "scanned": pkg.status in _PICKUP_DONE,
                    "missing": pkg.status == STATUS_MISSING_AT_PICKUP,
                }
            )
        out_items = []
        for entry in items.values():
            boxes = entry["boxes"]
            entry["scanned"] = sum(1 for b in boxes if b["scanned"])
            entry["missing"] = sum(1 for b in boxes if b["missing"])
            entry["complete"] = all(b["scanned"] or b["missing"] for b in boxes)
            out_items.append(entry)
        scanned, required, outstanding, reported = _phase_progress(rows, "pickup")
        return {
            "order_id": order.id,
            "whole_vehicle": _whole_vehicle(order),
            "items": out_items,
            "scanned": scanned,
            "missing": reported,
            "required": required,
            "can_confirm": _whole_vehicle(order) or (required > 0 and not outstanding),
        }

    def report_missing(
        self,
        db: Session,
        order: Order,
        package_id: str,
        *,
        photo_url: str,
        reason: str,
        notes: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        """
        A box is not at pickup: photo + reason are required. The box counts as
        accounted for at pickup (so pickup can be confirmed) and drops out of
        the delivery count. Opens a `package_missing` exception and raises
        `incident.reported` (ops alert), like a stop exception.
        """
        from porterchain_api.platform.package_events import emit_package_missing
        from porterchain_api.booking_models import OrderException

        photo = (photo_url or "").strip()
        if not photo:
            raise ValueError("photo_required")
        # Same photo forms as stop exceptions / POD: an uploaded URL or the
        # compressed camera data URL the driver app produces.
        if not photo.startswith(("https://", "http://", "data:image/")):
            raise ValueError("photo_url_invalid")
        if len(photo) > 3_000_000:
            raise ValueError("photo_too_large")
        code = (reason or "").strip().lower()
        if code not in MISSING_REASONS:
            raise ValueError("reason_invalid")
        self._packages.ensure_for_order(db, order)
        pkg = db.query(Package).filter(Package.id == package_id, Package.order_id == order.id).first()
        if not pkg:
            raise LookupError("package_not_found")
        if pkg.status in _PICKUP_DONE:
            raise ValueError("package_already_picked_up")
        pkg.status = STATUS_MISSING_AT_PICKUP
        exc = OrderException(
            order_id=order.id,
            type="package_missing",
            status="open",
            reported_by_type="driver",
            reported_by_id=actor_id,
            evidence={
                "package_id": pkg.id,
                "tracking_suffix": pkg.tracking_suffix,
                "item_key": pkg.item_key,
                "box_index": pkg.box_index,
                "box_count": pkg.box_count,
                "phase": "pickup",
                "reason": code,
                "notes": (notes or "").strip()[:500],
                "photo_url": photo,
            },
        )
        db.add(exc)
        db.flush()
        emit_package_missing(
            db,
            order_id=order.id,
            driver_id=actor_id,
            exception_id=exc.id,
            package_id=pkg.id,
            reason=code,
        )
        result = {"exception_id": exc.id, "package_id": pkg.id, "status": pkg.status}
        checklist = self.pickup_checklist(db, order)
        db.commit()
        return {**result, "checklist": checklist}

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
