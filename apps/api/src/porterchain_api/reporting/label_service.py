"""LabelService — assemble 4×6 thermal PDFs from packages (not dock sheets)."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, Package
from porterchain_api.domain.sandbox import order_is_sandbox
from porterchain_api.merchant_engine.package_service import PackageService
from porterchain_api.reporting.qr_codec import encode_label_qr
from porterchain_api.reporting.thermal_pdf import render_thermal_labels


class PackagesRequired(LookupError):
    """No packages available for labels."""


def _addr(addr: dict[str, Any] | None) -> str:
    if not isinstance(addr, dict):
        return "—"
    parts = [
        addr.get("name") or addr.get("contact_name"),
        addr.get("formatted") or addr.get("street") or addr.get("address") or addr.get("line1"),
        addr.get("city"),
        addr.get("postal_code") or addr.get("postal") or addr.get("zip"),
    ]
    return ", ".join(str(p) for p in parts if p) or "—"


def _cod_line(order: Order) -> str:
    cents = getattr(order, "cod_amount_cents", None)
    if not cents or int(cents) <= 0:
        return "—"
    status = getattr(order, "cod_status", None) or ""
    amount = f"${int(cents) / 100:.2f}"
    return f"{amount} {status}".strip() if status else amount


def _cod_cents_for_qr(order: Order) -> int | None:
    cents = getattr(order, "cod_amount_cents", None)
    if cents is None or int(cents) <= 0:
        return None
    return int(cents)


class LabelService:
    def __init__(self) -> None:
        self._packages = PackageService()

    def build_order_labels_pdf(
        self,
        db: Session,
        order: Order,
        *,
        merchant_name: str | None = None,
    ) -> tuple[bytes, str]:
        packages = self._packages.ensure_for_order(db, order)
        if not packages:
            raise PackagesRequired("packages_required")
        pdf = self._render(order, packages, merchant_name=merchant_name)
        return pdf, f"labels-{order.tracking_number}.pdf"

    def build_bulk_labels_pdf(
        self,
        db: Session,
        orders: Sequence[Order],
        *,
        merchant_names: dict[str, str] | None = None,
        max_orders: int = 100,
        max_pages: int = 500,
    ) -> tuple[bytes, str]:
        if len(orders) > max_orders:
            raise ValueError("labels_bulk_too_many_orders")
        pages: list[dict[str, Any]] = []
        names = merchant_names or {}
        for order in orders:
            packages = self._packages.ensure_for_order(db, order)
            pages.extend(
                self._page_dicts(
                    order,
                    packages,
                    merchant_name=names.get(order.merchant_id or ""),
                )
            )
            if len(pages) > max_pages:
                raise ValueError("labels_bulk_too_many_pages")
        if not pages:
            raise PackagesRequired("packages_required")
        return render_thermal_labels(pages), "labels-bulk.pdf"

    def build_pickup_manifest_pdf(
        self,
        orders: Sequence[Order],
        *,
        package_counts: dict[str, int],
    ) -> tuple[bytes, str]:
        """Simple box-count manifest (dock secondary remains pickup-list.pdf)."""
        from porterchain_api.reporting.compliance_dossier import render_compliance_pdf

        total_boxes = sum(package_counts.get(o.id, 0) for o in orders)
        lines = [
            f"Orders: {len(orders)}",
            f"Boxes total: {total_boxes}",
            "",
        ]
        for order in orders:
            n = package_counts.get(order.id, 0)
            lines.append(f"{order.tracking_number} · boxes {n}")
        pdf = render_compliance_pdf(
            [("Pickup manifest", lines)],
            title="Pickup manifest",
            footer=f"{len(orders)} orders · {total_boxes} boxes",
        )
        return pdf, "pickup-manifest.pdf"

    def _render(
        self,
        order: Order,
        packages: Sequence[Package],
        *,
        merchant_name: str | None,
    ) -> bytes:
        return render_thermal_labels(
            self._page_dicts(order, packages, merchant_name=merchant_name)
        )

    def _page_dicts(
        self,
        order: Order,
        packages: Sequence[Package],
        *,
        merchant_name: str | None,
    ) -> list[dict[str, Any]]:
        pickup = order.pickup if isinstance(order.pickup, dict) else {}
        from_line = merchant_name or _addr(pickup)
        to_line = _addr(order.dropoff if isinstance(order.dropoff, dict) else None)
        cod_line = _cod_line(order)
        cod_cents = _cod_cents_for_qr(order)
        sandbox = order_is_sandbox(order)
        pages: list[dict[str, Any]] = []
        for pkg in packages:
            pages.append(
                {
                    "route_hint": "",
                    "stop_sequence": pkg.stop_sequence,
                    "from_line": from_line,
                    "to_line": to_line,
                    "order_number": order.order_number,
                    "tracking_base": order.tracking_number,
                    "cod_line": cod_line,
                    "qr_payload": encode_label_qr(
                        order_id=order.id,
                        package_id=pkg.id,
                        route_hint=None,
                        stop_sequence=pkg.stop_sequence,
                        cod_cents=cod_cents,
                    ),
                    "tracking_suffix": pkg.tracking_suffix,
                    "parcel_index": pkg.parcel_index,
                    "total_parcels": pkg.total_parcels,
                    "is_sandbox": sandbox,
                }
            )
        return pages
