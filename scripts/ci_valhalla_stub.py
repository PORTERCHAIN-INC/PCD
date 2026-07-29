#!/usr/bin/env python3
"""Minimal Valhalla HTTP stub for CI / nightly E2E (stdlib only).

Serves /status and /route with GTA-scoped responses so pricing/routing
checks do not need a full Valhalla tile build. Bounding box matches
infrastructure/docker/scripts/prepare-valhalla-gta.sh (~150 km from
downtown Toronto).

Usage:
    python scripts/ci_valhalla_stub.py [--host 127.0.0.1] [--port 8002]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Downtown Toronto ±150 km (same as prepare-valhalla-gta.sh)
SW_LAT, SW_LNG = 42.306, -81.245
NE_LAT, NE_LNG = 45.000, -77.521


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _in_gta(lat: float, lon: float) -> bool:
    return SW_LAT <= lat <= NE_LAT and SW_LNG <= lon <= NE_LNG


def _route_payload(body: dict) -> dict:
    locs = body.get("locations") or []
    if len(locs) < 2:
        return {"error": "need at least two locations", "error_code": 154}
    total_km = 0.0
    for i in range(len(locs) - 1):
        a, b = locs[i], locs[i + 1]
        total_km += _haversine_km(float(a["lat"]), float(a["lon"]), float(b["lat"]), float(b["lon"]))
    # Road-network fudge (~1.25× great-circle) for downtown GTA trips
    length_km = max(total_km * 1.25, 0.1)
    time_s = max(int(length_km / 30.0 * 3600), 60)
    return {
        "trip": {
            "status": 0,
            "status_message": "Found route between points",
            "units": "kilometers",
            "summary": {"length": round(length_km, 3), "time": time_s},
            "legs": [{"summary": {"length": round(length_km, 3), "time": time_s}}],
            "locations": locs,
        },
        "ci_stub": True,
        "gta_bbox": [SW_LNG, SW_LAT, NE_LNG, NE_LAT],
        "locations_in_gta": all(_in_gta(float(p["lat"]), float(p["lon"])) for p in locs),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:  # quieter CI logs
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in ("/status", "/"):
            self._send(
                200,
                {
                    "version": "ci-valhalla-stub",
                    "tileset_last_modified": 0,
                    "available_actions": ["status", "route"],
                    "tile_extract": "gta-150km-stub",
                },
            )
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return
        if path == "/route":
            self._send(200, _route_payload(body if isinstance(body, dict) else {}))
            return
        self._send(404, {"error": "not found"})


def main() -> int:
    parser = argparse.ArgumentParser(description="CI Valhalla stub (GTA 150 km)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"ci_valhalla_stub listening on http://{args.host}:{args.port} (GTA ~150 km)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
