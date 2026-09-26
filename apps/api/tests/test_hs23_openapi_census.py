"""HS-23 — OpenAPI census: every operation classified; no new untagged business paths."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CENSUS = REPO_ROOT / "scripts" / "openapi_census.py"
SNAPSHOT = REPO_ROOT / "docs" / "api" / "openapi.json"

# DEVELOPMENT_TEST_CASES HS-23 baseline — bump only when intentional surface growth is classified.
EXPECTED_KEEP = 757


def test_hs23_openapi_census_pass_and_keep_count() -> None:
    assert CENSUS.is_file()
    assert SNAPSHOT.is_file()
    src = CENSUS.read_text(encoding="utf-8")
    assert "_UNTAGGED_OK_PREFIXES" in src
    assert "_BANNED" in src
    assert "/v1/merchant-api" in src or '"/v1/merchant-api"' in src

    proc = subprocess.run([sys.executable, str(CENSUS)], cwd=REPO_ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "PASS:" in out
    assert f"keep: {EXPECTED_KEEP}" in out
    assert "untagged path" not in out.lower()


def test_hs23_banned_aliases_absent_from_snapshot() -> None:
    """Cut routes must stay gone (DEVELOPMENT_TEST_CASES § cut list / openapi_census._BANNED)."""
    data = __import__("json").loads(SNAPSHOT.read_text(encoding="utf-8"))
    paths = data.get("paths") or {}
    banned = (
        ("post", "/driver/location"),
        ("get", "/v1/merchant/tracking/orders/{order_id}"),
        ("post", "/v1/merchant/billing/invoices/{invoice_id}/resend"),
    )
    for method, path in banned:
        item = paths.get(path)
        assert item is None or method not in item, f"banned still published: {method.upper()} {path}"
