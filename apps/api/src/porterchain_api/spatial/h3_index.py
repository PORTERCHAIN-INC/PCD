"""Uber H3 helpers for dispatch candidate prefilter.

Valhalla still owns road ETA. This only decides *who* enters the matrix.
Missing ``h3`` degrades to empty rings — callers fall back to rating cap.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

RESOLUTION = 9
DENSITY_RESOLUTION = 8
MIN_NEIGHBORS = 8


def _h3():
    try:
        import h3

        return h3
    except Exception:
        logger.debug("h3 library unavailable", exc_info=True)
        return None


def cell(lat: float, lng: float, *, res: int = RESOLUTION) -> str | None:
    lib = _h3()
    if lib is None:
        return None
    try:
        return str(lib.latlng_to_cell(float(lat), float(lng), res))
    except Exception:
        logger.debug("h3 cell failed lat=%s lng=%s", lat, lng, exc_info=True)
        return None


def cell_center(h3_cell: str) -> tuple[float, float] | None:
    lib = _h3()
    if lib is None or not h3_cell:
        return None
    try:
        lat, lng = lib.cell_to_latlng(str(h3_cell))
        return float(lat), float(lng)
    except Exception:
        logger.debug("h3 cell_center failed cell=%s", h3_cell, exc_info=True)
        return None


def neighborhood_cells(lat: float, lng: float, k: int) -> set[str]:
    lib = _h3()
    origin = cell(lat, lng)
    if lib is None or origin is None:
        return set()
    try:
        return {str(c) for c in lib.grid_disk(origin, k)}
    except Exception:
        logger.debug("h3 grid_disk failed", exc_info=True)
        return {origin}


def pick_nearby(
    pickup: tuple[float, float],
    positions: dict[str, tuple[float, float, str | None]],
    *,
    min_count: int = MIN_NEIGHBORS,
    cap: int = 20,
) -> list[str]:
    """Driver ids whose H3 cell is in k=2, then k=3. Empty → caller uses rating fallback."""
    if not pickup or not positions:
        return []
    plat, plng = pickup
    chosen: list[str] = []
    for k in (2, 3):
        ring = neighborhood_cells(plat, plng, k)
        if not ring:
            return []
        chosen = [
            driver_id
            for driver_id, (_lat, _lng, h3_cell) in positions.items()
            if h3_cell and h3_cell in ring
        ]
        if len(chosen) >= min_count:
            break
    return chosen[:cap]
