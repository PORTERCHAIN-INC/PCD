#!/usr/bin/env python3
"""Patch Valhalla valhalla.json for a 4GB host. Does not change the GTA ±150 km extract.

Runtime fields (cache, LRU, reserved labels) take effect on Valhalla restart.
include_bicycle / include_pedestrian only shrink the graph on the next tile rebuild.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 256 MiB tile cache — default image json uses 1_000_000_000 (~1 GB).
MAX_CACHE_SIZE = 268_435_456
# Planet-scale default is 1.3e9; GTA extract does not need that during tile build.
ID_TABLE_SIZE = 80_000_000


def tune(doc: dict[str, Any]) -> dict[str, Any]:
    mj = doc.setdefault("mjolnir", {})
    mj["max_cache_size"] = MAX_CACHE_SIZE
    mj["id_table_size"] = ID_TABLE_SIZE
    mj["concurrency"] = "1"
    mj["use_lru_mem_cache"] = True
    mj["include_bicycle"] = False
    mj["include_pedestrian"] = False
    mj["include_driving"] = True

    thor = doc.setdefault("thor", {})
    thor["clear_reserved_memory"] = True
    thor["max_reserved_labels_count_astar"] = 250_000
    thor["max_reserved_labels_count_bidir_astar"] = 150_000
    thor["max_reserved_labels_count_dijkstras"] = 400_000
    thor["max_reserved_labels_count_bidir_dijkstras"] = 200_000
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default="-",
        help="valhalla.json to patch in place, or - for stdin→stdout",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write to this path instead of overwriting PATH",
    )
    args = parser.parse_args()

    if args.path == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            print("empty stdin", file=sys.stderr)
            return 1
        doc = json.loads(raw)
        out_path = Path(args.output) if args.output else None
    else:
        src = Path(args.path)
        doc = json.loads(src.read_text(encoding="utf-8"))
        out_path = Path(args.output) if args.output else src

    tuned = json.dumps(tune(doc), indent=2) + "\n"
    if out_path is None:
        sys.stdout.write(tuned)
    else:
        out_path.write_text(tuned, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
