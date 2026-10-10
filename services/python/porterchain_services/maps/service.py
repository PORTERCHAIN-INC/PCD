"""Maps and routing service — Valhalla (optimization path) and OSRM (distance/ETA)."""

import logging
from typing import Any

import httpx

from porterchain_services.base import BaseService

logger = logging.getLogger(__name__)

# Quote/book/nav HTTP budget. 25s was a uvicorn stall; 2s matches leftover GET ops.
HTTP_TIMEOUT_S = 2.0

# Labeled last resort only. Never the compose/env default. Gated by osrm_allow_public_demo.
OSRM_PUBLIC_DEMO_LAST_RESORT = "https://router.project-osrm.org"


class MapsService(BaseService):
    service_name = "maps"

    def __init__(self, ctx=None) -> None:
        super().__init__(ctx)
        self._http: httpx.Client | None = None

    def _client(self) -> httpx.Client:
        if self._http is None or self._http.is_closed:
            self._http = httpx.Client(timeout=HTTP_TIMEOUT_S)
        return self._http

    @property
    def engine(self) -> str:
        return self.settings.routing_engine

    def _osrm_base(self) -> str | None:
        configured = (getattr(self.settings, "osrm_url", None) or "").strip().rstrip("/")
        if configured:
            return configured
        if getattr(self.settings, "osrm_allow_public_demo", False):
            logger.warning("OSRM using labeled public demo last-resort")
            return OSRM_PUBLIC_DEMO_LAST_RESORT.rstrip("/")
        return None

    def route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> dict[str, Any] | None:
        leg, _source = self.route_with_source(
            origin, destination, costing=costing, vehicle_class=vehicle_class
        )
        return leg

    def route_with_source(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None]:
        profile = self._resolve_costing(costing=costing, vehicle_class=vehicle_class)
        if self.engine == "valhalla" and self.settings.valhalla_url:
            leg = self._valhalla_route(origin, destination, costing=profile)
            if leg is not None:
                return leg, "valhalla"
            if self._osrm_base():
                logger.warning("Valhalla unavailable — falling back to OSRM")
                leg = self._osrm_route(origin, destination)
                if leg is not None:
                    return leg, "osrm"
            return None, None
        if self._osrm_base():
            leg = self._osrm_route(origin, destination)
            if leg is not None:
                return leg, "osrm"
        return None, None

    def route_distance_meters(
        self,
        points: list[tuple[float, float]],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> tuple[int | None, int | None, str | None]:
        """One multi-waypoint /route. Returns (meters, duration_seconds, routing_source)."""
        if len(points) < 2:
            return None, None, None
        profile = self._resolve_costing(costing=costing, vehicle_class=vehicle_class)
        if self.engine == "valhalla" and self.settings.valhalla_url:
            parsed = self._parse_leg(
                self._valhalla_route_locations(points, costing=profile)
            )
            if parsed is not None:
                return parsed[0], parsed[1], "valhalla"
            if self._osrm_base():
                logger.warning("Valhalla multi-route unavailable — falling back to OSRM")
                parsed = self._parse_leg(self._osrm_route_locations(points))
                if parsed is not None:
                    return parsed[0], parsed[1], "osrm"
            return None, None, None
        if self._osrm_base():
            parsed = self._parse_leg(self._osrm_route_locations(points))
            if parsed is not None:
                return parsed[0], parsed[1], "osrm"
        return None, None, None

    @staticmethod
    def _resolve_costing(
        *, costing: str | None = None, vehicle_class: str | None = None
    ) -> str:
        from porterchain_services.maps.costing import resolve_valhalla_costing

        return resolve_valhalla_costing(costing=costing, vehicle_class=vehicle_class)

    def eta_between(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> dict[str, Any] | None:
        """Public ETA. Valhalla first, OSRM fallback. Engines must not call _osrm/_valhalla."""
        leg, source = self.route_with_source(
            origin, destination, costing=costing, vehicle_class=vehicle_class
        )
        parsed = self._parse_leg(leg)
        if not parsed or not source or not leg:
            return None
        meters, seconds = parsed
        polyline = None
        if source == "osrm" and leg.get("routes"):
            polyline = leg["routes"][0].get("geometry")
        elif source == "valhalla":
            from porterchain_services.maps.route_helpers import optimized_route_from_valhalla

            opt = optimized_route_from_valhalla(leg)
            polyline = (opt or {}).get("polyline")
        return {
            "source": source,
            "duration_seconds": seconds,
            "distance_meters": meters,
            "polyline": polyline,
        }

    def optimized_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> dict[str, Any] | None:
        """Public map geometry. Valhalla first; OSRM polyline fallback."""
        from porterchain_services.maps.route_helpers import optimized_route_from_valhalla

        leg, source = self.route_with_source(
            origin, destination, costing=costing, vehicle_class=vehicle_class
        )
        if source == "valhalla":
            return optimized_route_from_valhalla(leg)
        if source == "osrm" and leg and leg.get("routes"):
            route = leg["routes"][0]
            return {
                "source": "osrm",
                "duration_seconds": int(route.get("duration", 0)),
                "distance_meters": int(route.get("distance", 0)),
                "polyline": route.get("geometry"),
                "polyline_encoding": "google",
            }
        return None

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

    def route_multi(
        self,
        points: list[tuple[float, float]],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> dict[str, Any] | None:
        """Multi-waypoint Valhalla /route (geometry + summary). Falls back to None."""
        if len(points) < 2 or not self.settings.valhalla_url:
            return None
        profile = self._resolve_costing(costing=costing, vehicle_class=vehicle_class)
        return self._valhalla_route_locations(points, costing=profile)

    def matrix_durations(
        self,
        sources: list[tuple[float, float]],
        targets: list[tuple[float, float]],
        *,
        costing: str | None = None,
        vehicle_class: str | None = None,
        date_time: Any = None,
        date_time_type: int = 1,
    ) -> tuple[list[list[tuple[int | None, int | None]]], str | None]:
        """Time-distance matrix: sources×targets → (seconds, meters) cells.

        Valhalla `/sources_to_targets` first; OSRM `/table` fallback. Never Google.
        Prefer ``vehicle_class=box_truck`` → costing ``truck`` (right-turn / restriction aware).
        Optional ``date_time`` probes time-dependent Valhalla (Phase 6); OSRM ignores it.
        """
        if not sources or not targets:
            return [], None
        profile = self._resolve_costing(costing=costing, vehicle_class=vehicle_class)
        if self.engine == "valhalla" and self.settings.valhalla_url:
            matrix = self._valhalla_matrix(
                sources,
                targets,
                costing=profile,
                date_time=date_time,
                date_time_type=date_time_type,
            )
            if matrix is not None:
                return matrix, "valhalla"
            if self._osrm_base():
                logger.warning("Valhalla matrix unavailable — falling back to OSRM table")
                matrix = self._osrm_table(sources, targets)
                if matrix is not None:
                    return matrix, "osrm"
            return [], None
        if self._osrm_base():
            matrix = self._osrm_table(sources, targets)
            if matrix is not None:
                return matrix, "osrm"
        return [], None

    def _valhalla_matrix(
        self,
        sources: list[tuple[float, float]],
        targets: list[tuple[float, float]],
        *,
        costing: str = "auto",
        date_time: Any = None,
        date_time_type: int = 1,
    ) -> list[list[tuple[int | None, int | None]]] | None:
        if not self.settings.valhalla_url:
            return None
        url = f"{self.settings.valhalla_url.rstrip('/')}/sources_to_targets"
        body: dict[str, Any] = {
            "sources": [{"lat": p[0], "lon": p[1]} for p in sources],
            "targets": [{"lat": p[0], "lon": p[1]} for p in targets],
            "costing": costing or "auto",
            "units": "kilometers",
        }
        if date_time is not None:
            from porterchain_services.maps.date_time import attach_date_time

            attach_date_time(body, date_time, time_type=date_time_type)
        try:
            response = self._client().post(url, json=body)
            if response.status_code >= 400:
                # Retry without date_time if tile/engine rejects time-dependent request.
                if "date_time" in body:
                    body.pop("date_time", None)
                    response = self._client().post(url, json=body)
                    if response.status_code >= 400:
                        return None
                else:
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
        if not self._osrm_base():
            return None
        points = list(sources) + list(targets)
        coords = ";".join(f"{p[1]},{p[0]}" for p in points)
        src_idx = ";".join(str(i) for i in range(len(sources)))
        dst_idx = ";".join(str(len(sources) + i) for i in range(len(targets)))
        url = f"{self._osrm_base().rstrip('/')}/table/v1/driving/{coords}"
        try:
            response = self._client().get(
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

    def isochrone(
        self,
        origin: tuple[float, float],
        *,
        contours_minutes: list[int] | None = None,
        costing: str | None = None,
        vehicle_class: str | None = None,
    ) -> dict[str, Any] | None:
        """Valhalla /isochrone for coverage UI. Never used by GTA CAD quotes (P2-1)."""
        if not self.settings.valhalla_url:
            return None
        minutes = contours_minutes or [10, 20, 30]
        profile = self._resolve_costing(costing=costing, vehicle_class=vehicle_class)
        url = f"{self.settings.valhalla_url.rstrip('/')}/isochrone"
        body = {
            "locations": [{"lat": origin[0], "lon": origin[1]}],
            "costing": profile,
            "contours": [{"time": int(m)} for m in minutes],
            "polygons": True,
        }
        try:
            response = self._client().post(url, json=body)
            if response.status_code >= 400:
                return None
            data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("Valhalla isochrone unreachable: %s", exc)
            return None
        return data if isinstance(data, dict) else None

    def snap(self, point: tuple[float, float]) -> tuple[float, float]:
        """Snap a GPS fix / address pin to the nearest drivable road (OSRM nearest,
        Valhalla locate fallback). Returns the input when neither answers or the
        snap would move the point more than 300 m (a bad geocode beats a wrong road)."""
        from math import cos, radians, sqrt

        def close(p: tuple[float, float]) -> bool:
            dy = (p[0] - point[0]) * 111_000
            dx = (p[1] - point[1]) * 111_000 * cos(radians(point[0]))
            return sqrt(dx * dx + dy * dy) <= 300

        base = self._osrm_base()
        if base:
            try:
                r = self._client().get(f"{base}/nearest/v1/driving/{point[1]},{point[0]}")
                wp = (r.json().get("waypoints") or [None])[0] if r.status_code < 400 else None
                if wp:
                    p = (float(wp["location"][1]), float(wp["location"][0]))
                    if close(p):
                        return p
            except (httpx.HTTPError, ValueError, KeyError, TypeError):
                pass
        if self.settings.valhalla_url:
            try:
                r = self._client().post(
                    f"{self.settings.valhalla_url.rstrip('/')}/locate",
                    json={"locations": [{"lat": point[0], "lon": point[1]}], "costing": "auto"},
                )
                edges = (r.json() or [{}])[0].get("edges") or [] if r.status_code < 400 else []
                if edges:
                    p = (float(edges[0]["correlated_lat"]), float(edges[0]["correlated_lon"]))
                    if close(p):
                        return p
            except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
                pass
        return point

    def map_match(
        self, points: list[tuple[float, float]], *, vehicle_class: str | None = None
    ) -> dict[str, Any] | None:
        """Snap a noisy GPS trace to roads: Valhalla trace_route, OSRM /match fallback.

        Returns ``{"path": [[lat, lng], ...], "distance_m": int, "source": str}`` or None.
        """
        if len(points) < 2:
            return None
        if self.settings.valhalla_url:
            url = f"{self.settings.valhalla_url.rstrip('/')}/trace_route"
            body = {
                "shape": [{"lat": p[0], "lon": p[1]} for p in points],
                "costing": self._resolve_costing(costing=None, vehicle_class=vehicle_class),
                "shape_match": "map_snap",
                "units": "kilometers",
            }
            try:
                r = self._client().post(url, json=body)
                if r.status_code < 400:
                    from porterchain_services.maps.polyline import decode_polyline

                    trip = (r.json() or {}).get("trip") or {}
                    path: list[list[float]] = []
                    for leg in trip.get("legs") or []:
                        shape = leg.get("shape") or ""
                        path.extend([lat, lng] for lat, lng in decode_polyline(shape, precision=6))
                    if len(path) >= 2:
                        km = float((trip.get("summary") or {}).get("length") or 0)
                        return {"path": path, "distance_m": int(km * 1000), "source": "valhalla"}
            except httpx.HTTPError as exc:
                logger.warning("Valhalla trace_route unreachable: %s", exc)
        base = self._osrm_base()
        if base:
            coords = ";".join(f"{p[1]},{p[0]}" for p in points[:100])
            try:
                r = self._client().get(
                    f"{base}/match/v1/driving/{coords}",
                    params={"geometries": "geojson", "overview": "full", "tidy": "true"},
                )
                data = r.json() if r.status_code < 400 else {}
                legs = data.get("matchings") or []
                if legs:
                    path = [[c[1], c[0]] for m in legs for c in m["geometry"]["coordinates"]]
                    dist = sum(float(m.get("distance") or 0) for m in legs)
                    return {"path": path, "distance_m": int(dist), "source": "osrm"}
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                logger.warning("OSRM match failed: %s", exc)
        return None

    def _valhalla_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        *,
        costing: str = "auto",
    ) -> dict[str, Any] | None:
        return self._valhalla_route_locations(
            [origin, destination], costing=costing
        )

    def _valhalla_route_locations(
        self,
        points: list[tuple[float, float]],
        *,
        costing: str = "auto",
        date_time: Any = None,
        date_time_type: int = 1,
    ) -> dict[str, Any] | None:
        if not self.settings.valhalla_url or len(points) < 2:
            return None
        url = f"{self.settings.valhalla_url.rstrip('/')}/route"
        body: dict[str, Any] = {
            "locations": [{"lat": p[0], "lon": p[1]} for p in points],
            "costing": costing or "auto",
        }
        if date_time is not None:
            from porterchain_services.maps.date_time import attach_date_time

            attach_date_time(body, date_time, time_type=date_time_type)
        try:
            response = self._client().post(url, json=body)
            if response.status_code >= 400 and "date_time" in body:
                body.pop("date_time", None)
                response = self._client().post(url, json=body)
            if response.status_code >= 400:
                return None
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("Valhalla unreachable: %s", exc)
            return None

    def _osrm_route(
        self, origin: tuple[float, float], destination: tuple[float, float]
    ) -> dict[str, Any] | None:
        return self._osrm_route_locations([origin, destination])

    def _osrm_route_locations(self, points: list[tuple[float, float]]) -> dict[str, Any] | None:
        if not self._osrm_base() or len(points) < 2:
            return None
        coords = ";".join(f"{p[1]},{p[0]}" for p in points)
        url = f"{self._osrm_base().rstrip('/')}/route/v1/driving/{coords}"
        try:
            response = self._client().get(url, params={"overview": "full", "geometries": "polyline"})
            if response.status_code >= 400:
                return None
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning("OSRM unreachable: %s", exc)
            return None
