"""TrackingTranslator — one stable live-tracking shape for every portal.

Input is the last-known GPS payload built by ``TrackingFacade.fetch_raw``. Order state
always comes from the PorterChain order row, never from the tracker.
"""

from __future__ import annotations

from typing import Any


class TrackingTranslator:
    @staticmethod
    def translate(raw: dict[str, Any] | None) -> dict[str, Any]:
        raw = raw or {}
        location = raw.get("location") or raw.get("coordinates") or {}
        lat, lng = location.get("lat"), location.get("lng")
        return {
            "state": None,
            "location": {"lat": lat, "lng": lng} if (lat is not None and lng is not None) else None,
            "eta": raw.get("eta"),
            "distance_remaining_m": raw.get("distance_remaining"),
            "last_updated": raw.get("recorded_at") or raw.get("last_updated"),
            "activity": [],
        }
