"""Proof of delivery (POD) service — capture artifacts from Fleetbase."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)


class PodService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def fetch_proofs(self, fleetbase_order_id: str) -> list[dict[str, Any]]:
        try:
            response = self.client.get(f"/v1/orders/{fleetbase_order_id}/proofs")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase proofs fetch failed for {fleetbase_order_id}")
            return []

        proofs = response.get("proofs") or response.get("data")
        if isinstance(proofs, list):
            return proofs
        if isinstance(proofs, dict):
            return [proofs]
        return []

    def normalize_proof(self, proof: dict[str, Any]) -> dict[str, Any]:
        """Map Fleetbase proof payload to Porterchain POD shape."""
        return {
            "fleetbase_proof_id": proof.get("id") or proof.get("uuid"),
            "type": proof.get("type") or proof.get("proof_type"),
            "url": proof.get("url") or proof.get("file_url"),
            "captured_at": proof.get("captured_at") or proof.get("created_at"),
            "signature": proof.get("signature"),
            "notes": proof.get("notes") or proof.get("comment"),
            "raw": proof,
        }

    def fetch_normalized(self, fleetbase_order_id: str) -> list[dict[str, Any]]:
        return [self.normalize_proof(p) for p in self.fetch_proofs(fleetbase_order_id)]

    def upload_proof(
        self,
        fleetbase_order_id: str,
        *,
        proof_type: str,
        data: dict[str, Any],
    ) -> bool:
        body = {"type": proof_type, **data}
        try:
            self.client.post(f"/v1/orders/{fleetbase_order_id}/proofs", json=body)
            return True
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase POD upload failed ({proof_type})")
            return False

    def upload_photo(self, fleetbase_order_id: str, file_url: str) -> bool:
        return self.upload_proof(fleetbase_order_id, proof_type="photo", data={"url": file_url})

    def upload_signature(self, fleetbase_order_id: str, signature_data: str) -> bool:
        return self.upload_proof(fleetbase_order_id, proof_type="signature", data={"signature": signature_data})

    def upload_barcode(self, fleetbase_order_id: str, barcode: str) -> bool:
        return self.upload_proof(fleetbase_order_id, proof_type="barcode", data={"barcode": barcode})
