"""HS-22 — Mobile driver handshake types talk to :8001 only (no :8000 / SocketCluster)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DRIVER = REPO_ROOT / "apps" / "mobile-driver"


def test_hs22_handshake_types_and_api_base() -> None:
    types = (DRIVER / "src" / "types.ts").read_text(encoding="utf-8")
    assert "export type Handshake" in types
    assert "api: LinkState" in types
    assert "auth: LinkState" in types

    handshake = (DRIVER / "src" / "handshake.ts").read_text(encoding="utf-8")
    assert "export async function runHandshake" in handshake
    assert ":8001" in handshake

    config = (DRIVER / "src" / "config.ts").read_text(encoding="utf-8")
    assert ":8001" in config
    assert ":8000" not in config

    api = (DRIVER / "src" / "api.ts").read_text(encoding="utf-8")
    assert "/driver-api/v1" in api


def test_hs22_no_fleetbase_port_or_socketcluster_in_driver_src() -> None:
    for path in DRIVER.joinpath("src").rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert ":8000" not in text, path
        assert "socketcluster" not in text.lower(), path


def test_hs22_validate_mobile_smoke() -> None:
    script = REPO_ROOT / "scripts" / "verify_mobile_smoke.py"
    proc = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert ":8001" in proc.stdout or "HS-22" in proc.stdout or "PASS" in proc.stdout
