#!/usr/bin/env python3
"""Split fat FastAPI routers into packages (masterrule Appendix D)."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS = ROOT / "apps/api/src/porterchain_api/routers"

SPLITS: dict[str, list[tuple[str, int, int | None]]] = {
    "admin": [
        ("dashboard", 197, 255),
        ("orders", 257, 614),
        ("claims", 615, 857),
        ("finance", 1081, 1220),
        ("support", 1221, 1491),
        ("settings", 1492, None),
    ],
    "merchant": [
        ("dashboard_booking", 149, 442),
        ("orders_tracking", 443, 629),
        ("billing", 630, 774),
        ("reports", 775, 960),
        ("profile_team", 961, 1196),
        ("settings", 1198, 1360),
        ("support_claims", 1362, 1440),
        ("integrations", 1443, None),
    ],
    "driver": [
        ("auth", 61, 107),
        ("profile", 108, 129),
        ("dashboard", 130, 362),
        ("shift", 363, 422),
        ("support", 423, 538),
        ("communications", 540, 637),
        ("jobs", 639, 866),
        ("navigation_pod", 867, None),
    ],
}


def split_router(name: str, sections: list[tuple[str, int, int | None]]) -> None:
    src = ROUTERS / f"{name}.py"
    if not src.exists():
        raise SystemExit(f"missing {src}")
    lines = src.read_text().splitlines(keepends=True)
    first_route = next(i for i, line in enumerate(lines) if line.startswith("@router."))
    header = "".join(lines[:first_route])

    pkg = ROUTERS / name
    if pkg.exists():
        for child in pkg.iterdir():
            child.unlink()
    else:
        pkg.mkdir()

    (pkg / "_deps.py").write_text(header)

    imports: list[str] = []
    for mod, start, end in sections:
        chunk_lines = lines[start - 1 :] if end is None else lines[start - 1 : end]
        body = (
            f'"""{name} routes — {mod}."""\n\n'
            f"from porterchain_api.routers.{name}._deps import *  # noqa: F403\n\n"
            + "".join(chunk_lines)
        )
        (pkg / f"{mod}.py").write_text(body)
        imports.append(f"from porterchain_api.routers.{name} import {mod}  # noqa: F401")

    init = (
        f'"""{name.title()} API package — thin sub-routers on shared `router`."""\n\n'
        f"from porterchain_api.routers.{name}._deps import router\n\n"
        + "\n".join(imports)
        + '\n\n__all__ = ["router"]\n'
    )
    (pkg / "__init__.py").write_text(init)
    src.unlink()
    print(f"split {name} -> {pkg.relative_to(ROOT)} ({len(sections)} modules)")


def main() -> None:
    for name, sections in SPLITS.items():
        split_router(name, sections)


if __name__ == "__main__":
    main()
