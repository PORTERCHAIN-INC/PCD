"""FSA admin GTA150 gate + bulk upsert (Phase 2c)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from porterchain_api.admin_engine.fsa_admin_service import FsaAdminService
from porterchain_api.schemas_pricing import FsaRateBody


def test_rejects_out_of_tile_dest() -> None:
    svc = FsaAdminService()
    with pytest.raises(ValueError, match="out_of_gta150_tile"):
        svc.validated_fsa("K1A", field="dest_fsa", required=True)


def test_accepts_in_tile_dest() -> None:
    svc = FsaAdminService()
    assert svc.validated_fsa("M5V", field="dest_fsa", required=True) == "M5V"


def test_bulk_skips_out_of_tile_rows() -> None:
    svc = FsaAdminService()
    db = MagicMock()
    # No existing rows
    db.query.return_value.filter.return_value.filter.return_value.filter.return_value.first.return_value = (
        None
    )
    # Simpler: make chained filter return self-ish
    q = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.first.return_value = None

    result = svc.bulk_upsert(
        db,
        [
            FsaRateBody(dest_fsa="M5V", flat_cents=4500),
            FsaRateBody(dest_fsa="K1A", flat_cents=9900),
        ],
        merchant_id=None,
    )
    assert result["created"] == 1
    assert result["error_count"] == 1
    assert "out_of_gta150_tile" in result["errors"][0]["error"]
    db.add.assert_called_once()
    db.commit.assert_called_once()
