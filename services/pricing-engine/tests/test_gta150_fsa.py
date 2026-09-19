"""GTA150 FSA registry — tile ∩ StatsCan boundaries (not all Ontario)."""

from __future__ import annotations

from porterchain_pricing.gta150_fsa import (
    gta150_fsa_codes,
    gta150_registry_meta,
    is_gta150_fsa,
)
from porterchain_pricing.components.fsa import is_ontario_fsa


def test_registry_count_band() -> None:
    meta = gta150_registry_meta()
    assert meta["count"] == len(gta150_fsa_codes())
    # Hundreds of FSAs, not full Canada / not full Ontario alone as “coverage”.
    assert 200 <= int(meta["count"] or 0) <= 500
    assert int(meta["ontario_fsa_count"] or 0) > int(meta["count"] or 0)


def test_in_tile_examples() -> None:
    assert is_gta150_fsa("M5V")
    assert is_gta150_fsa("L4W")
    assert is_gta150_fsa("m5v 2t6")  # normalize via normalize_fsa path
    # Non-geographic downtown large-receiver codes (hub overrides).
    assert is_gta150_fsa("M5X")
    assert is_gta150_fsa("M5X 1A1")


def test_out_of_tile_but_ontario() -> None:
    # Ottawa / Sudbury are Ontario districts but outside the GTA ±150 km tile.
    assert is_ontario_fsa("K1A")
    assert is_ontario_fsa("P3E")
    assert not is_gta150_fsa("K1A")
    assert not is_gta150_fsa("P3E")
    assert not is_gta150_fsa("V6B")
    assert not is_gta150_fsa("")


def test_service_area_rejects_ottawa() -> None:
    from porterchain_api.merchant_engine.service_area import service_area_error
    from porterchain_api.schemas_merchant import AddressInput

    err = service_area_error("dropoff", AddressInput(formatted="Ottawa", postal="K1A 0B1"))
    assert err is not None
    assert "GTA" in err or "tile" in err.lower()
    ok = service_area_error("dropoff", AddressInput(formatted="Toronto", postal="M5V 2T6"))
    assert ok is None
