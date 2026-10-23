"""Label QR codec — LOGISTICSv1 pipe payload (shared by LabelService + ScanGate)."""

from __future__ import annotations

import base64 as _b64
import hashlib as _hashlib
import hmac as _hmac
from dataclasses import dataclass


class InvalidLabelQr(ValueError):
    """Wrong version or arity — map to 400 invalid_label_qr."""


@dataclass(frozen=True)
class LabelQrPayload:
    order_id: str
    package_id: str
    route_hint: str = ""
    stop_sequence: str = ""
    #: Legacy 6th slot (was COD cents). Cash on delivery is retired: new labels
    #: always write it empty; old printed labels may still carry a value, ignored.
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
) -> str:
    seq = "" if stop_sequence is None else str(stop_sequence)
    return LabelQrPayload(
        order_id=order_id,
        package_id=package_id,
        route_hint=route_hint or "",
        stop_sequence=seq,
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


# ---------------------------------------------------------------------------
# PC1 signed label code (Oct 2026). Opaque: carries no order id, COD, name or
# address. ``PC1.<package uuid hex>.<hmac-sha256 truncated, base32>``.
# A forged or mistyped code fails verification and resolves to nothing.
# Legacy LOGISTICSv1 labels already printed keep scanning.
# ---------------------------------------------------------------------------


PC1_PREFIX = "PC1"
_SIG_BYTES = 10


def _label_key() -> bytes:
    from porterchain_api.config import get_settings

    s = get_settings()
    explicit = (getattr(s, "label_signing_secret", "") or "").strip()
    if explicit:
        return explicit.encode()
    base = (getattr(s, "jwt_secret", "") or getattr(s, "sso_jwt_secret", "") or "").strip()
    if not base:
        base = "porterchain-dev-label-key"  # tests / local only; prod always has JWT_SECRET
    return _hmac.new(base.encode(), b"porterchain-label-v1", _hashlib.sha256).digest()


def _sig(pkg_hex: str, key: bytes | None = None) -> str:
    mac = _hmac.new(key or _label_key(), f"{PC1_PREFIX}.{pkg_hex}".encode(), _hashlib.sha256).digest()
    return _b64.b32encode(mac[:_SIG_BYTES]).decode().rstrip("=")


def encode_signed_label(package_id: str, *, key: bytes | None = None) -> str:
    pkg_hex = package_id.replace("-", "").lower()
    if len(pkg_hex) != 32 or any(c not in "0123456789abcdef" for c in pkg_hex):
        raise ValueError("package_id_not_uuid")
    return f"{PC1_PREFIX}.{pkg_hex.upper()}.{_sig(pkg_hex, key)}"


def is_signed_label(raw: str) -> bool:
    return (raw or "").strip().upper().startswith(PC1_PREFIX + ".")


def decode_signed_label(raw: str, *, key: bytes | None = None) -> str:
    """Return the package UUID, or raise InvalidLabelQr (bad shape or signature)."""
    parts = (raw or "").strip().upper().split(".")
    if len(parts) != 3 or parts[0] != PC1_PREFIX:
        raise InvalidLabelQr("invalid_label_qr")
    pkg_hex = parts[1].lower()
    if len(pkg_hex) != 32:
        raise InvalidLabelQr("invalid_label_qr")
    if not _hmac.compare_digest(_sig(pkg_hex, key), parts[2]):
        raise InvalidLabelQr("invalid_label_qr")
    h = pkg_hex
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
