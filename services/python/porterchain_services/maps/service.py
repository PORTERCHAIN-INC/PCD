"""Maps and routing service — Valhalla (optimization path) and OSRM (distance/ETA)."""

import logging
from typing import Any

import httpx

from porterchain_services.base import BaseService

logger = logging.getLogger(__name__)


class MapsService(BaseService):
    service_name = "maps"

    @property
    def engine(self) -> str:
        return self.settings.routing_engine

    def route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> dict[str, Any] | None:
        leg, _source = self.route_with_source(origin, destination)
        return leg

    def route_with_source(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> tuple[dict[str, Any] | None, str | None]:
        if self.engine == "valhalla" and self.settings.valhalla_url:
            leg = self._valhalla_route(origin, destination)
            if leg is not None:
                return leg, "valhalla"
            if self.settings.osrm_url:
                logger.warning("Valhalla unavailable — falling back to OSRM")
                leg = self._osrm_route(origin, destination)
                if leg is not None:
                    return leg, "osrm"
            return None, None
        if self.settings.osrm_url:
            leg = self._osrm_route(origin, destination)
            if leg is not None:
                return leg, "osrm"
        return None, None

    def route_distance_meters(
        self,
        points: list[tuple[float, float]],
    ) -> tuple[int | None, int | None, str | None]:
        """Sum leg distances across waypoints. Returns (meters, duration_seconds, routing_source)."""
        if len(points) < 2:
            return None, None, None
        total_m = 0
        total_s = 0
        source: str | None = None
        for i in range(len(points) - 1):
            leg, leg_source = self.route_with_source(points[i], points[i + 1])
            parsed = self._parse_leg(leg)
            if parsed is None:
                return None, None, None
            meters, seconds = parsed
            total_m += meters
            total_s += seconds
            source = leg_source
        return total_m, total_s, source

    def _parse_leg(self, leg: dict[str, Any] | None) -> tuple[int, int] | None:
        if not leg:
            return None
        if "trip" in leg:
            summary = leg.get("trip", {}).get("summary", {})
            if not summary:
                return None
            return int(summary.get("length", 0) * 1000), int(summary.get("time", 0))
        if leg.get("code") == "Ok" and leg.get("routes"):
            route = leg["routes"][0]
            return int(route.get("distance", 0)), int(route.get("duration", 0))
        return None

    def _valhalla_route(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> dict[str, Any] | None:
        url = f"{self.settings.valhalla_url.rstrip('/')}/route"
        body = {
            "locations": [
                {"lat": origin[0], "lon": origin[1]},
                {"lat": destination[0], "lon": destination[1]},
            ],
            "costing": "auto",
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=body)
                if response.status_code >= 400:
                    return None
                return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Valhalla unreachable: %s", exc)
            return None

    def _osrm_route(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> dict[str, Any] | None:
        url = (
            f"{self.settings.osrm_url.rstrip('/')}/route/v1/driving/"
            f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        )
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(url, params={"overview": "full", "geometries": "polyline"})
                if response.status_code >= 400:
                    return None
                return response.json()
        except httpx.HTTPError as exc:
            logger.warning("OSRM unreachable: %s", exc)
            return None
