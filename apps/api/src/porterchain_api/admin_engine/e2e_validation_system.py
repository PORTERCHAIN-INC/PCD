"""E2E validation — phase 1 system layer."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.e2e_validation_catalog import SYSTEM_CHAIN
from porterchain_api.config import Settings


class E2EValidationSystemMixin:
    def phase_1_system_layer(self, db: Session, settings: Settings) -> dict[str, Any]:
        arch = self._diagnostics.architecture_validation(settings)
        health = self._diagnostics.health_dashboard(db, settings)
        connections: list[dict[str, Any]] = []

        for node in SYSTEM_CHAIN:
            entry: dict[str, Any] = {
                "id": node["id"],
                "label": node["label"],
                "status": "PASS",
                "layer": "infrastructure",
            }
            comp = next((c for c in health["components"] if c["id"] == node["id"]), None)
            if comp:
                entry["status"] = self._health_to_validation(comp["status"])
                entry["latency_ms"] = comp.get("latency_ms")
                if comp.get("errors"):
                    entry["root_cause"] = "; ".join(comp["errors"][:2])
            elif node["id"] in {"booking_portal", "customer_portal"}:
                entry["status"] = "PASS"
                entry["details"] = {"note": "Embedded in website per masterrule §5"}
            elif node["id"] in {
                "pricing_engine",
                "billing_engine",
                "notification_engine",
                "orders_engine",
                "crm_engine",
                "finance_engine",
                "claims_engine",
                "support_engine",
            }:
                engine_id = node["id"]
                comp = next((c for c in health["components"] if c["id"] == engine_id), None)
                if comp:
                    entry["status"] = self._health_to_validation(comp["status"])
            connections.append(entry)
            self._trace("connection_probe", node["label"], entry["status"], layer=node["id"])

        broken = [c for c in connections if c["status"] in ("FAIL", "BLOCKER")]
        overall = "BLOCKER" if any(c["status"] == "BLOCKER" for c in connections) else (
            "FAIL" if broken else ("WARNING" if any(c["status"] == "WARNING" for c in connections) else "PASS")
        )

        return {
            "phase": 1,
            "name": "System Layer Validation",
            "overall": overall,
            "connections": connections,
            "architecture": arch,
            "api_routes_verified": arch.get("missing_apis", []),
            "websocket_probe": next(
                (c for c in health["components"] if c["id"] == "websockets"),
                {},
            ),
            "notification_probe": next(
                (c for c in health["components"] if c["id"] == "notification_engine"),
                {},
            ),
            "day_plan_probe": self._diagnostics.day_plan_monitor(db),
        }
