"""Label QR codec — LOGISTICSv1 pipe payload (shared by LabelService + ScanGate)."""

from __future__ import annotations

from dataclasses import dataclass


class InvalidLabelQr(ValueError):
    """Wrong version or arity — map to 400 invalid_label_qr."""


@dataclass(frozen=True)
class LabelQrPayload:
    order_id: str
    package_id: str
    route_hint: str = ""
    stop_sequence: str = ""
    cod_cents: str = ""

    def encode(self) -> str:
        return "|".join(
            [
                "LOGISTICSv1",
                self.order_id,
                self.package_id,
                self.route_hint or "",
                self.stop_sequence or "",
                self.cod_cents or "",
            ]
        )


def encode_label_qr(
    *,
    order_id: str,
    package_id: str,
    route_hint: str | None = None,
    stop_sequence: int | str | None = None,
    cod_cents: int | None = None,
) -> str:
    seq = "" if stop_sequence is None else str(stop_sequence)
    cod = "" if cod_cents is None else str(int(cod_cents))
    return LabelQrPayload(
        order_id=order_id,
        package_id=package_id,
        route_hint=route_hint or "",
        stop_sequence=seq,
        cod_cents=cod,
    ).encode()


def decode_label_qr(raw: str) -> LabelQrPayload:
    parts = (raw or "").strip().split("|")
    if len(parts) != 6 or parts[0] != "LOGISTICSv1":
        raise InvalidLabelQr("invalid_label_qr")
    return LabelQrPayload(
        order_id=parts[1],
        package_id=parts[2],
        route_hint=parts[3],
        stop_sequence=parts[4],
        cod_cents=parts[5],
    )
