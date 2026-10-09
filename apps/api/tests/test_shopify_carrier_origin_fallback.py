"""Shopify carrier rates: ship-from fallback to the PorterChain pickup + empty-rate logs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.integrations.shopify_carrier_rates import carrier_service_rates

_MOD = "porterchain_api.integrations.shopify_carrier_rates"
_SECRET = "shpss_test"
_SHOP = "pcdc-test.myshopify.com"
_PICKUP = SimpleNamespace(
    formatted="100 King St W, Toronto, ON M5X 1A9", postal="M5X1A9", lat=43.648, lng=-79.381
)
_DEST = {
    "postal_code": "M5V 1A1",
    "country": "CA",
    "province": "ON",
    "city": "Toronto",
    "address1": "100 Queen St W",
}


def _call(
    *,
    origin: dict[str, Any] | None,
    destination: dict[str, Any] | None = None,
    pickup: Any = _PICKUP,
    quote_result: tuple[int, dict[str, Any]] = (5200, {"final_cents": 5200}),
    status: str = MerchantStatus.ACTIVE.value,
) -> tuple[dict[str, Any], MagicMock]:
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id="m1", status=status)
    shop = SimpleNamespace(
        id="s1", merchant_id="m1", shop_domain=_SHOP, encrypted_webhook_secret=None
    )
    rate: dict[str, Any] = {
        "currency": "USD",
        "destination": destination or dict(_DEST),
        "items": [{"grams": 1000, "quantity": 1}],
    }
    if origin is not None:
        rate["origin"] = origin
    payload = {"rate": rate}
    body = json.dumps(payload).encode()
    sig = base64.b64encode(hmac.new(_SECRET.encode(), body, hashlib.sha256).digest()).decode()
    quote = MagicMock(return_value=quote_result)
    with (
        patch(f"{_MOD}._active_shop", return_value=shop),
        patch(f"{_MOD}.default_pickup_address", return_value=pickup),
        patch(f"{_MOD}.address_from_saved", side_effect=lambda row: row),
        patch(f"{_MOD}.ensure_shop_pickup_bound", side_effect=lambda db, s, address: s),
        patch(f"{_MOD}._ensure_geo", side_effect=lambda a: a),
        patch(f"{_MOD}.quote_merchant_rate", quote),
        patch(f"{_MOD}.persist_rate_quote", return_value=SimpleNamespace(id="q1")),
    ):
        out = carrier_service_rates(
            db,
            SimpleNamespace(shopify_api_secret=_SECRET, jwt_secret="x" * 32),
            raw_body=body,
            hmac_header=sig,
            shop_domain=_SHOP,
            payload=payload,
        )
    return out, quote


def _lines(caplog: pytest.LogCaptureFixture, prefix: str) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.getMessage().startswith(prefix)]


@pytest.mark.parametrize(
    ("origin", "reason"),
    [
        ({"country": "US", "province": "NY", "postal_code": "10001"}, "origin_non_canada"),
        ({"country": "US"}, "origin_non_canada"),
        ({"country": "CA", "postal_code": "A1A 1A1", "city": "St. John's"}, "origin_out_of_area"),
        ({"country": "CA", "postal_code": "K1A 0A6", "city": "Ottawa"}, "origin_out_of_area"),
        (None, "origin_missing"),
        ({"country": "CA"}, "origin_missing"),
    ],
)
def test_unusable_origin_falls_back_to_pickup(caplog, origin, reason):
    caplog.set_level(logging.INFO, logger=_MOD)
    out, quote = _call(origin=origin)
    assert out["rates"][0]["service_code"] == "porterchain_same_day"
    assert out["rates"][0]["total_price"] == "5200"
    assert quote.call_args.kwargs["pickup"] is _PICKUP
    lines = _lines(caplog, "shopify_carrier_origin_fallback")
    assert len(lines) == 1
    assert f"shop={_SHOP}" in lines[0]
    assert f"reason={reason}" in lines[0]
    assert "pickup_fsa=M5X" in lines[0]
    assert not _lines(caplog, "shopify_carrier_empty")


def test_in_area_origin_used_as_is(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    origin = {"country": "CA", "postal_code": "L4W 1S9", "city": "Mississauga"}
    out, quote = _call(origin=origin)
    assert out["rates"]
    assert quote.call_args.kwargs["pickup"].postal == "L4W 1S9"
    assert not _lines(caplog, "shopify_carrier_origin_fallback")


def test_non_canada_destination_empty_with_reason(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    dest = {"country": "US", "postal_code": "10001", "city": "New York", "address1": "1 Main"}
    out, quote = _call(origin=None, destination=dest)
    assert out == {"rates": []}
    quote.assert_not_called()
    lines = _lines(caplog, "shopify_carrier_empty")
    assert len(lines) == 1
    assert "reason=dest_non_canada" in lines[0]
    assert "dest_country=US" in lines[0]
    assert "New York" not in lines[0] and "1 Main" not in lines[0]


def test_destination_out_of_area_logs_fsa_only(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    dest = {"country": "CA", "postal_code": "K1A 0A6", "city": "Ottawa", "address1": "1 Wellington"}
    out, _ = _call(origin=None, destination=dest)
    assert out == {"rates": []}
    (line,) = _lines(caplog, "shopify_carrier_empty")
    assert "reason=dest_out_of_area" in line
    assert "dest_fsa=K1A" in line
    assert "Wellington" not in line and "0A6" not in line


def test_no_pickup_empty_with_reason(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    out, quote = _call(origin={"country": "US"}, pickup=None)
    assert out == {"rates": []}
    quote.assert_not_called()
    (line,) = _lines(caplog, "shopify_carrier_empty")
    assert f"shop={_SHOP}" in line
    assert "reason=no_pickup" in line


def test_fallback_pickup_must_be_in_area(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    ottawa = SimpleNamespace(formatted="Ottawa ON K1A 0A6", postal="K1A0A6", lat=45.42, lng=-75.7)
    out, quote = _call(origin={"country": "US"}, pickup=ottawa)
    assert out == {"rates": []}
    quote.assert_not_called()
    (line,) = _lines(caplog, "shopify_carrier_empty")
    assert "reason=pickup_out_of_area" in line
    assert "origin=origin_non_canada" in line
    assert "pickup_fsa=K1A" in line


@pytest.mark.parametrize(
    ("result", "reason"),
    [
        ((0, {"metadata": {"fsa_refused": True}}), "fsa_refused"),
        ((0, {"metadata": {}}), "zero_price"),
    ],
)
def test_refused_or_zero_quote_logs_reason(caplog, result, reason):
    caplog.set_level(logging.INFO, logger=_MOD)
    out, _ = _call(origin=None, quote_result=result)
    assert out == {"rates": []}
    (line,) = _lines(caplog, "shopify_carrier_empty")
    assert f"reason={reason}" in line
    assert "dest_fsa=M5V" in line


def test_pricing_exception_logs_reason(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    with patch(f"{_MOD}.quote_merchant_rate", side_effect=RuntimeError("boom")):
        db = MagicMock()
        db.get.return_value = SimpleNamespace(id="m1", status=MerchantStatus.ACTIVE.value)
        shop = SimpleNamespace(
            id="s1", merchant_id="m1", shop_domain=_SHOP, encrypted_webhook_secret=None
        )
        payload = {"rate": {"destination": dict(_DEST)}}
        body = json.dumps(payload).encode()
        sig = base64.b64encode(hmac.new(_SECRET.encode(), body, hashlib.sha256).digest()).decode()
        with (
            patch(f"{_MOD}._active_shop", return_value=shop),
            patch(f"{_MOD}.default_pickup_address", return_value=_PICKUP),
            patch(f"{_MOD}.address_from_saved", side_effect=lambda row: row),
            patch(f"{_MOD}.ensure_shop_pickup_bound", side_effect=lambda db, s, address: s),
            patch(f"{_MOD}._ensure_geo", side_effect=lambda a: a),
        ):
            out = carrier_service_rates(
                db,
                SimpleNamespace(shopify_api_secret=_SECRET, jwt_secret="x" * 32),
                raw_body=body,
                hmac_header=sig,
                shop_domain=_SHOP,
                payload=payload,
            )
    assert out == {"rates": []}
    (line,) = _lines(caplog, "shopify_carrier_empty")
    assert "reason=pricing_error" in line


def test_inactive_merchant_logs_status(caplog):
    caplog.set_level(logging.INFO, logger=_MOD)
    out, quote = _call(origin=None, status="ONBOARDING")
    assert out == {"rates": []}
    quote.assert_not_called()
    (line,) = _lines(caplog, "shopify_carrier_empty")
    assert "reason=merchant_inactive" in line
    assert "status=ONBOARDING" in line
