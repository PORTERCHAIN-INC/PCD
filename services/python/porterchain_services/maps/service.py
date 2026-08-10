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

    def route_multi(self, points: list[tuple[float, float]]) -> dict[str, Any] | None:
        """Multi-waypoint Valhalla /route (geometry + summary). Falls back to None."""
        if len(points) < 2 or not self.settings.valhalla_url:
            return None
        return self._valhalla_route_locations(points)

    def matrix_durations(
        self,
        sources: list[tuple[float, float]],
        targets: list[tuple[float, float]],
    ) -> tuple[list[list[tuple[int | None, int | None]]], str | None]:
        """Time-distance matrix: sources×targets → (seconds, meters) cells.

        Valhalla `/sources_to_targets` first; OSRM `/table` fallback. Never Google.
        """
        if not sources or not targets:
            return [], None
        if self.engine == "valhalla" and self.settings.valhalla_url:
            matrix = self._valhalla_matrix(sources, targets)
            if matrix is not None:
                return matrix, "valhalla"
            if self.settings.osrm_url:
                logger.warning("Valhalla matrix unavailable — falling back to OSRM table")
                matrix = self._osrm_table(sources, targets)
                if matrix is not None:
                    return matrix, "osrm"
            return [], None
        if self.settings.osrm_url:
            matrix = self._osrm_table(sources, targets)
            if matrix is not None:
                return matrix, "osrm"
        return [], None

    def _valhalla_matrix(
        self,
        sources: list[tuple[float, float]],
        targets: list[tuple[float, float]],
    ) -> list[list[tuple[int | None, int | None]]] | None:
        if not self.settings.valhalla_url:
            return None
        url = f"{self.settings.valhalla_url.rstrip('/')}/sources_to_targets"
        body = {
            "sources": [{"lat": p[0], "lon": p[1]} for p in sources],
            "targets": [{"lat": p[0], "lon": p[1]} for p in targets],
            "costing": "auto",
            "units": "kilometers",
        }
        try:
            with httpx.Client(timeout=25.0) as client:
                response = client.post(url, json=body)
                if response.status_code >= 400:
                    return None
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Valhalla matrix unreachable: %s", exc)
            return None
        rows = data.get("sources_to_targets")
        if not isinstance(rows, list):
            return None
        out: list[list[tuple[int | None, int | None]]] = []
        for row in rows:
            if not isinstance(row, list):
                out.append([(None, None)] * len(targets))
                continue
            parsed_row: list[tuple[int | None, int | None]] = []
            for cell in row:
                if not isinstance(cell, dict) or cell.get("time") is None:
                    parsed_row.append((None, None))
                    continue
                try:
                    seconds = int(cell["time"])
                    dist_km = cell.get("distance")
                    meters = int(float(dist_km) * 1000) if dist_km is not None else None
                except (TypeError, ValueError):
                    parsed_row.append((None, None))
                    continue
                parsed_row.append((seconds, meters))
            out.append(parsed_row)
        return out

    def _osrm_table(
        self,
        sources: list[tuple[float, float]],
        targets: list[tuple[float, float]],
    ) -> list[list[tuple[int | None, int | None]]] | None:
        if not self.settings.osrm_url:
            return None
        points = list(sources) + list(targets)
        coords = ";".join(f"{p[1]},{p[0]}" for p in points)
        src_idx = ";".join(str(i) for i in range(len(sources)))
        dst_idx = ";".join(str(len(sources) + i) for i in range(len(targets)))
        url = f"{self.settings.osrm_url.rstrip('/')}/table/v1/driving/{coords}"
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.get(
                    url,
                    params={
                        "sources": src_idx,
                        "destinations": dst_idx,
                        "annotations": "duration,distance",
                    },
                )
                if response.status_code >= 400:
                    return None
                data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("OSRM table unreachable: %s", exc)
            return None
        if data.get("code") not in (None, "Ok"):
            return None
        durations = data.get("durations")
        distances = data.get("distances")
        if not isinstance(durations, list):
            return None
        out: list[list[tuple[int | None, int | None]]] = []
        for i, row in enumerate(durations):
            if not isinstance(row, list):
                out.append([(None, None)] * len(targets))
                continue
            parsed_row: list[tuple[int | None, int | None]] = []
            for j, dur in enumerate(row):
                meters = None
                if isinstance(distances, list) and i < len(distances):
                    drow = distances[i]
                    if isinstance(drow, list) and j < len(drow) and drow[j] is not None:
                        try:
                            meters = int(float(drow[j]))
                        except (TypeError, ValueError):
                            meters = None
                if dur is None:
                    parsed_row.append((None, meters))
                else:
                    try:
                        parsed_row.append((int(float(dur)), meters))
                    except (TypeError, ValueError):
                        parsed_row.append((None, meters))
            out.append(parsed_row)
        return out

    def _valhalla_route(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> dict[str, Any] | None:
        return self._valhalla_route_locations([origin, destination])

    def _valhalla_route_locations(
        self, points: list[tuple[float, float]]
    ) -> dict[str, Any] | None:
        if not self.settings.valhalla_url or len(points) < 2:
            return None
        url = f"{self.settings.valhalla_url.rstrip('/')}/route"
        body = {
            "locations": [{"lat": p[0], "lon": p[1]} for p in points],
            "costing": "auto",
        }
        try:
            with httpx.Client(timeout=20.0) as client:
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
