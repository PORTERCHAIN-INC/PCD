#!/usr/bin/env python3
"""Rebuild porterchain_pricing/data/gta150_fsa_registry.json from StatsCan 2021 FSA boundaries.

Requires: curl/unzip, Docker (ghcr.io/osgeo/gdal), network.

Usage (from repo root):
  python scripts/build_gta150_fsa_registry.py
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlretrieve

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "services/pricing-engine/porterchain_pricing/data/gta150_fsa_registry.json"
WORK = ROOT / "tmp/fsa_build"
ZIP_URL = (
    "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/"
    "boundary-limites/files-fichiers/lfsa000a21a_e.zip"
)
GDAL_IMAGE = "ghcr.io/osgeo/gdal:alpine-small-3.10.3"

# infrastructure/deploy/scripts/prepare-valhalla-gta.sh
SW_LNG, SW_LAT = -81.245, 42.306
NE_LNG, NE_LAT = -77.521, 45.000
HUB_LAT, HUB_LNG = 43.6532, -79.3832
RADIUS_KM = 150.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def walk_coords(coords, lons: list[float], lats: list[float]) -> None:
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        lons.append(float(coords[0]))
        lats.append(float(coords[1]))
        return
    for child in coords:
        walk_coords(child, lons, lats)


def geom_stats(geom: dict | None) -> tuple[float, float, float, float, float, float] | None:
    lons: list[float] = []
    lats: list[float] = []
    walk_coords((geom or {}).get("coordinates"), lons, lats)
    if not lons:
        return None
    return (
        min(lons),
        min(lats),
        max(lons),
        max(lats),
        sum(lats) / len(lats),
        sum(lons) / len(lons),
    )


def intersects_tile(min_lng: float, min_lat: float, max_lng: float, max_lat: float) -> bool:
    return not (max_lng < SW_LNG or min_lng > NE_LNG or max_lat < SW_LAT or min_lat > NE_LAT)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    zip_path = WORK / "lfsa000a21a_e.zip"
    if not zip_path.exists():
        print(f"Downloading {ZIP_URL} …")
        urlretrieve(ZIP_URL, zip_path)  # noqa: S310 — fixed StatsCan URL
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(WORK)

    shp = WORK / "lfsa000a21a_e" / "lfsa000a21a_e.shp"
    geojson = WORK / "ontario_fsa.geojson"
    if not geojson.exists():
        print(f"Reprojecting via {GDAL_IMAGE} …")
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{WORK}:/data",
                GDAL_IMAGE,
                "ogr2ogr",
                "-f",
                "GeoJSON",
                "-t_srs",
                "EPSG:4326",
                "-where",
                "PRUID='35'",
                "/data/ontario_fsa.geojson",
                "/data/lfsa000a21a_e/lfsa000a21a_e.shp",
            ],
            check=True,
        )
    if not shp.exists() and not geojson.exists():
        print("missing shapefile extract", file=sys.stderr)
        return 1

    data = json.loads(geojson.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for feature in data.get("features") or []:
        props = feature.get("properties") or {}
        code = str(props.get("CFSAUID") or "").strip().upper()
        if len(code) != 3:
            continue
        stats = geom_stats(feature.get("geometry"))
        if not stats:
            continue
        min_lng, min_lat, max_lng, max_lat, c_lat, c_lng = stats
        if not intersects_tile(min_lng, min_lat, max_lng, max_lat):
            continue
        dist = haversine_km(HUB_LAT, HUB_LNG, c_lat, c_lng)
        rows.append(
            {
                "code": code,
                "lat": round(c_lat, 6),
                "lng": round(c_lng, 6),
                "distance_km_from_hub": round(dist, 1),
                "land_area_km2": props.get("LANDAREA"),
                "in_tile": True,
                "province": "ON",
                "district": code[0],
                "active": True,
            }
        )

    seen: set[str] = set()
    uniq: list[dict] = []
    for row in sorted(rows, key=lambda r: r["code"]):
        if row["code"] in seen:
            continue
        seen.add(row["code"])
        uniq.append(row)

    artifact = {
        "version": 1,
        "source": {
            "provider": "Statistics Canada",
            "product": "2021 Census Forward Sortation Area Digital Boundary File (lfsa000a21a_e)",
            "url": ZIP_URL,
            "method": "boundary intersects Valhalla GTA bbox; centroid = mean vertex lat/lng (EPSG:4326)",
            "license_note": "StatsCan open data; regenerate via scripts/build_gta150_fsa_registry.py",
        },
        "tile": {
            "name": "PorterChain-GTA-150km",
            "hub": {"lat": HUB_LAT, "lng": HUB_LNG},
            "radius_km": RADIUS_KM,
            "bbox": {
                "sw_lng": SW_LNG,
                "sw_lat": SW_LAT,
                "ne_lng": NE_LNG,
                "ne_lat": NE_LAT,
            },
            "bbox_source": "infrastructure/deploy/scripts/prepare-valhalla-gta.sh",
        },
        "count": len(uniq),
        "ontario_fsa_count": len(data.get("features") or []),
        "fsas": uniq,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} count={len(uniq)} by_district={dict(Counter(r['district'] for r in uniq))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
