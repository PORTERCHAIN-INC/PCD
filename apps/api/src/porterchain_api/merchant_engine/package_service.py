"""Package SoT — ``packages`` table is authority; JSON is FB projection only.

Cutover: after PACKAGES_JSON_CUTOVER, merchant cargo still may arrive in request
JSON once, but is immediately synced to the table and re-projected onto stops
for Fleetbase. Readers (labels/scans) always prefer the table.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package
from porterchain_api.merchant_engine.stop_cargo import meaningful_packages

# After this date, prolonged JSON+table dual SoT is anti-Dean — table wins;
# stops[].packages exists only as a derived Fleetbase payload cache.
PACKAGES_JSON_CUTOVER = date(2026, 9, 26)


def dual_write_json_enabled() -> bool:
    """True = accept inbound JSON cargo shapes; False = table-only authority.

    Either way, ``project_packages_onto_stops`` runs after sync so FB sees entities.
    """
    return date.today() < PACKAGES_JSON_CUTOVER


def _dims(pkg: dict[str, Any]) -> dict[str, Any] | None:
    out: dict[str, Any] = {}
    if pkg.get("length_cm") or pkg.get("width_cm") or pkg.get("height_cm"):
        out = {
            "length_cm": pkg.get("length_cm"),
            "width_cm": pkg.get("width_cm"),
            "height_cm": pkg.get("height_cm"),
        }
    else:
        raw = pkg.get("dimensions")
        if isinstance(raw, dict):
            out = dict(raw)
    name = str(pkg.get("name") or "").strip()
    if name:
        out["display_name"] = name
    sku = str(pkg.get("sku") or "").strip()
    if sku:
        out["sku"] = sku
    return out or None


def _weight(pkg: dict[str, Any]) -> Decimal | None:
    raw = pkg.get("weight_kg")
    if raw is None or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return None


def extract_json_parcels(order: Order) -> list[dict[str, Any]]:
    """Flatten stop packages into ordered parcel dicts with stop_key / stop_sequence."""
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    stops = meta.get("stops") if isinstance(meta.get("stops"), list) else []
    out: list[dict[str, Any]] = []
    for stop in stops:
        if not isinstance(stop, dict):
            continue
        stop_key = stop.get("id")
        if stop_key is None and stop.get("sequence") is not None:
            stop_key = str(stop.get("sequence"))
        seq = stop.get("sequence")
        try:
            seq_i = int(seq) if seq is not None else None
        except (TypeError, ValueError):
            seq_i = None
        for pkg in meaningful_packages(stop.get("packages")):
            row = dict(pkg)
            row["_stop_key"] = str(stop_key) if stop_key else None
            row["_stop_sequence"] = seq_i
            out.append(row)
    return out


def _package_to_stop_dict(pkg: Package) -> dict[str, Any]:
    dims = pkg.dimensions if isinstance(pkg.dimensions, dict) else {}
    display = str(dims.get("display_name") or "").strip()
    sku = str(dims.get("sku") or "").strip() or None
    # Projection keeps merchant label when present; tracking_suffix remains label barcode SoT.
    geo = {
        k: dims[k]
        for k in ("length_cm", "width_cm", "height_cm")
        if k in dims and dims[k] is not None
    }
    return {
        "id": pkg.id,
        "name": display or pkg.tracking_suffix or f"BOX {pkg.parcel_index}",
        "sku": sku,
        "quantity": 1,
        "weight_kg": float(pkg.weight_kg) if pkg.weight_kg is not None else None,
        "length_cm": geo.get("length_cm"),
        "width_cm": geo.get("width_cm"),
        "height_cm": geo.get("height_cm"),
        "dimensions": geo or None,
        "parcel_index": pkg.parcel_index,
        "total_parcels": pkg.total_parcels,
        "tracking_suffix": pkg.tracking_suffix,
        "status": pkg.status,
    }


class PackageService:
    def list_for_order(self, db: Session, order_id: str) -> list[Package]:
        return (
            db.query(Package)
            .filter(Package.order_id == order_id)
            .order_by(Package.parcel_index.asc())
            .all()
        )

    def project_packages_onto_stops(self, order: Order, rows: list[Package]) -> None:
        """Derive ``compliance_metadata.stops[].packages`` from the table (FB cache)."""
        meta = dict(order.compliance_metadata) if isinstance(order.compliance_metadata, dict) else {}
        stops = meta.get("stops") if isinstance(meta.get("stops"), list) else []
        if not stops:
            # Minimal projection: all packages on first synthetic stop for FB.
            meta["stops"] = [
                {
                    "id": "pc-cargo",
                    "sequence": 1,
                    "stop_type": "pickup",
                    "packages": [_package_to_stop_dict(p) for p in rows],
                }
            ]
            order.compliance_metadata = meta
            return

        by_key: dict[str | None, list[Package]] = {}
        for pkg in rows:
            by_key.setdefault(pkg.stop_key, []).append(pkg)

        new_stops: list[dict[str, Any]] = []
        assigned: set[str] = set()
        for stop in stops:
            if not isinstance(stop, dict):
                continue
            stop = dict(stop)
            key = stop.get("id")
            if key is None and stop.get("sequence") is not None:
                key = str(stop.get("sequence"))
            key_s = str(key) if key is not None else None
            matched = by_key.get(key_s) or []
            if not matched and key_s is None:
                matched = by_key.get(None) or []
            for p in matched:
                assigned.add(p.id)
            stop["packages"] = [_package_to_stop_dict(p) for p in matched]
            new_stops.append(stop)

        leftover = [p for p in rows if p.id not in assigned]
        if leftover and new_stops:
            # Attach unscoped packages to first pickup-ish stop.
            first = new_stops[0]
            first["packages"] = list(first.get("packages") or []) + [
                _package_to_stop_dict(p) for p in leftover
            ]

        meta["stops"] = new_stops
        order.compliance_metadata = meta

    def sync_from_order(self, db: Session, order: Order, *, replace: bool = True) -> list[Package]:
        """Upsert packages from inbound JSON (or one default box), then project for FB."""
        parcels = extract_json_parcels(order)
        if not parcels:
            existing = self.list_for_order(db, order.id)
            if existing:
                self.project_packages_onto_stops(order, existing)
                return existing
            meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
            stops = meta.get("stops") if isinstance(meta.get("stops"), list) else []
            # Empty packages[] means "no parcel list", not "zero boxes", when weight_kg is set
            # (CSV bulk / API weight-only). Invent a box so scan-gate pickup can complete.
            if stops and all(isinstance(s, dict) and "packages" in s for s in stops):
                if meta.get("weight_kg") is None:
                    self.project_packages_onto_stops(order, [])
                    return []
            parcels = [
                {
                    "name": "Parcel",
                    "weight_kg": meta.get("weight_kg") if isinstance(meta, dict) else None,
                    "_stop_key": None,
                    "_stop_sequence": None,
                }
            ]

        total = len(parcels)
        tracking = order.tracking_number or order.id[:8]
        existing = {p.parcel_index: p for p in self.list_for_order(db, order.id)}

        kept: list[Package] = []
        for idx, pkg in enumerate(parcels, start=1):
            row = existing.get(idx)
            if row is None:
                row = Package(order_id=order.id, parcel_index=idx)
                db.add(row)
            row.total_parcels = total
            row.tracking_suffix = f"{tracking}-{idx:02d}"
            if not row.barcode:
                row.barcode = row.tracking_suffix
            row.stop_key = pkg.get("_stop_key")
            row.stop_sequence = pkg.get("_stop_sequence")
            row.weight_kg = _weight(pkg)
            row.dimensions = _dims(pkg)
            if not row.status:
                row.status = "manifested"
            kept.append(row)

        if replace:
            for idx, row in existing.items():
                if idx > total:
                    db.delete(row)

        db.flush()
        # Always project table → JSON so Fleetbase entities stay aligned (SoT = table).
        self.project_packages_onto_stops(order, kept)
        if not dual_write_json_enabled():
            # Post-cutover: strip free-form cargo keys that aren't projected packages.
            meta = dict(order.compliance_metadata or {})
            meta.pop("dimensions", None)  # prefer package rows for dims
            order.compliance_metadata = meta
        return kept

    def ensure_for_order(self, db: Session, order: Order) -> list[Package]:
        rows = self.list_for_order(db, order.id)
        if rows:
            return rows
        return self.sync_from_order(db, order)
