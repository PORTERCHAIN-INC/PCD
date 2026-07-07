"""TrackingTranslator — normalize Fleetbase tracking snapshots for Porterchain.

Fleetbase tracker payloads vary by version; this produces a stable shape that
the merchant/customer dashboards and public tracking page can rely on.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.fleetbase_engine.status_translator import StatusTranslator


class TrackingTranslator:
    @staticmethod
    def translate(raw: dict[str, Any] | None) -> dict[str, Any]:
        raw = raw or {}
        # Fleetbase tracker fields can be nested under different keys across versions.
        location = (
            raw.get("location")
            or raw.get("current_location")
            or raw.get("position")
            or {}
        )
        lat = location.get("lat") or location.get("latitude") or raw.get("lat")
        lng = location.get("lng") or location.get("longitude") or raw.get("lng")

        status = raw.get("status") or raw.get("status_code")
        state = StatusTranslator.to_state(status=status)

        activity = []
        for item in raw.get("activity") or raw.get("tracker_status") or raw.get("events") or []:
            if not isinstance(item, dict):
                continue
            activity.append(
                {
                    "status": item.get("status") or item.get("code"),
                    "note": item.get("details") or item.get("note"),
                    "at": item.get("created_at") or item.get("updated_at") or item.get("timestamp"),
                    "location": item.get("location"),
                }
            )

        return {
            "state": state.value if state else None,
            "fleetbase_status": status,
            "location": {"lat": lat, "lng": lng} if (lat is not None and lng is not None) else None,
            "eta": raw.get("eta") or raw.get("estimated_arrival"),
            "distance_remaining_m": raw.get("distance") or raw.get("distance_remaining"),
            "last_updated": raw.get("updated_at") or raw.get("last_updated"),
            "activity": activity,
        }
