"""Package SoT — ``packages`` table is authority; JSON is FB projection only.

Cutover: after PACKAGES_JSON_CUTOVER, merchant cargo still may arrive in request
JSON once, but is immediately synced to the table and re-projected onto stops
for stop payloads. Readers (labels/scans) always prefer the table.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package
from porterchain_api.merchant_engine.stop_cargo import expand_item_boxes, meaningful_packages

# After this date, prolonged JSON+table dual SoT is anti-Dean — table wins;
# stops[].packages exists only as a derived payload cache.
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
    name = str(pkg.get("name") or pkg.get("preset_label") or "").strip()
    if name:
        out["display_name"] = name
    if pkg.get("preset_id"):
        out["preset_id"] = pkg.get("preset_id")
    if pkg.get("preset_label"):
        out["preset_label"] = pkg.get("preset_label")
    instructions = str(pkg.get("instructions") or "").strip()
    if instructions:
        out["instructions"] = instructions
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


def _int_or_none(raw: Any) -> int | None:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 1 else None


def _item_fields(pkg: dict[str, Any]) -> dict[str, Any]:
    """Multi-box item fields from an inbound / projected package dict."""
    key = str(pkg.get("item_key") or pkg.get("item_id") or "").strip()[:64] or None
    label = str(pkg.get("item_label") or pkg.get("item_name") or "").strip()[:120] or None
    box_count = _int_or_none(pkg.get("box_count"))
    box_index = _int_or_none(pkg.get("box_index"))
    if box_count and box_index and box_index > box_count:
        box_index = None
    return {"item_key": key, "item_label": label, "box_index": box_index, "box_count": box_count}


def item_ordinals(rows: Sequence[Package]) -> dict[str, int]:
    """item_key → 1-based item number in parcel order ("Item 2" on labels / checklist)."""
    out: dict[str, int] = {}
    for row in sorted(rows, key=lambda r: r.parcel_index or 0):
        if row.item_key and row.item_key not in out:
            out[row.item_key] = len(out) + 1
    return out


def item_box_line(row: Package, ordinals: dict[str, int]) -> str:
    """
    "Item 2 · box 1 of 3" for a multi-box item, else "".

    Never the product title or SKU: labels must not reveal contents (PHI for
    pharmacy / lab orders). The item number matches the driver checklist.
    """
    if not row.item_key or not row.box_count or row.box_count < 2:
        return ""
    n = ordinals.get(row.item_key)
    return f"Item {n} · box {row.box_index or '?'} of {row.box_count}" if n else ""


def _number_item_boxes(rows: list[Package]) -> None:
    """Fill box n-of-N for item boxes that arrived without numbers (order kept)."""
    groups: dict[str, list[Package]] = {}
    for row in rows:
        if row.item_key:
            groups.setdefault(row.item_key, []).append(row)
    for boxes in groups.values():
        indexes = [b.box_index for b in boxes]
        if all(indexes) and len(set(indexes)) == len(boxes) and all(b.box_count == len(boxes) for b in boxes):
            continue
        for n, box in enumerate(boxes, start=1):
            box.box_index = n
            box.box_count = len(boxes)


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
    if out:
        return out
    stored = meta.get("parcels")
    if isinstance(stored, dict):
        if stored.get("booking_mode") == "vehicle":
            return []
        stored = stored.get("items")
    if isinstance(stored, list):
        for pkg in stored:
            if isinstance(pkg, dict):
                out.append(dict(pkg))
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
    out = {
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
    if pkg.item_key:
        out.update(
            item_key=pkg.item_key,
            item_label=pkg.item_label,
            box_index=pkg.box_index,
            box_count=pkg.box_count,
        )
    return out


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
            if meta.get("booking_mode") == "vehicle":
                self.project_packages_onto_stops(order, [])
                return []
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

        parcels = expand_item_boxes(parcels)
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
            item = _item_fields(pkg)
            row.item_key = item["item_key"]
            row.item_label = item["item_label"]
            row.box_index = item["box_index"] if item["item_key"] else None
            row.box_count = item["box_count"] if item["item_key"] else None
            if not row.status:
                row.status = "manifested"
            kept.append(row)

        _number_item_boxes(kept)

        if replace:
            for idx, row in existing.items():
                if idx > total:
                    db.delete(row)

        db.flush()
        # Always project table → JSON (SoT = table).
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
