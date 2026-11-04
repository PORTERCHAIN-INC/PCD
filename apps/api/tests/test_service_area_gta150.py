"""Service area uses the pricing GTA ±150 km tile (moved from services/pricing-engine/tests/test_gta150_fsa.py:
the pricing package must not import porterchain_api, so this API-level check lives with the API tests)."""

from __future__ import annotations


def test_service_area_rejects_ottawa() -> None:
    from porterchain_api.merchant_engine.service_area import service_area_error
    from porterchain_api.schemas_merchant import AddressInput

    err = service_area_error("dropoff", AddressInput(formatted="Ottawa", postal="K1A 0B1"))
    assert err is not None
    assert "GTA" in err or "tile" in err.lower()
    ok = service_area_error("dropoff", AddressInput(formatted="Toronto", postal="M5V 2T6"))
    assert ok is None
