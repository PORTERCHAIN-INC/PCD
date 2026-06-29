"""Maps and routing service — Google Places, Valhalla, OSRM."""

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
        if self.engine == "valhalla" and self.settings.valhalla_url:
            return self._valhalla_route(origin, destination)
        if self.settings.osrm_url:
            return self._osrm_route(origin, destination)
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
