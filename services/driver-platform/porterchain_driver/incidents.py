"""Driver incident reporting — links to Claims module when applicable."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class IncidentService:
    def list_incidents(self, db: Session, driver_id: str, *, limit: int = 20) -> list[dict]:
        from porterchain_api.driver_models import DriverIncident

        rows = (
            db.query(DriverIncident)
            .filter(DriverIncident.driver_id == driver_id)
            .order_by(DriverIncident.created_at.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize(i) for i in rows]

    def report_incident(
        self,
        db: Session,
        driver: Any,
        *,
        incident_type: str,
        description: str,
        order_id: str | None = None,
        location: dict | None = None,
        evidence: dict | None = None,
    ) -> dict:
        from porterchain_api.driver_models import DriverIncident
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_driver.support_bridge import DriverSupportBridgeService

        bridge = DriverSupportBridgeService()
        meta = bridge.incident_type_meta(incident_type)
        priority = meta.get("priority", "normal") if meta else "normal"

        incident = DriverIncident(
            driver_id=driver.id,
            order_id=order_id,
            incident_type=incident_type,
            description=description,
            location=location or {},
            evidence={**(evidence or {}), "priority": priority},
            status="open",
        )
        db.add(incident)
        db.flush()

        claim_id = None
        if meta and meta.get("creates_claim") and order_id and meta.get("claim_type"):
            try:
                claim = bridge.open_claim(
                    db,
                    driver,
                    order_id=order_id,
                    claim_type=str(meta["claim_type"]),
                    description=description,
                )
                claim_id = claim.get("id")
                incident.evidence = {**(incident.evidence or {}), "claim_id": claim_id}
            except LookupError:
                pass

        from porterchain_shared.events.catalog import DomainEventType

        event_type = DomainEventType.CLAIM_OPENED if claim_id else "incident.reported"
        emit_event(
            db,
            event_type=event_type,
            aggregate_type="incident",
            aggregate_id=incident.id,
            correlation_id=order_id,
            actor_type="driver",
            actor_id=driver.id,
            payload={
                "incident_type": incident_type,
                "claim_id": claim_id,
                "driver_id": driver.id,
                "order_id": order_id,
                "actor_type": "driver",
                "actor_id": driver.id,
            },
        )
        db.flush()
        result = self._serialize(incident)
        if claim_id:
            result["claim_id"] = claim_id
        return result

    @staticmethod
    def _serialize(incident: Any) -> dict:
        return {
            "id": incident.id,
            "incident_type": incident.incident_type,
            "description": incident.description,
            "order_id": incident.order_id,
            "status": incident.status,
            "location": incident.location,
            "evidence": incident.evidence,
            "created_at": incident.created_at.isoformat(),
        }
