"""Route-import error codes and classic bulk {row, error, message} shape."""

from __future__ import annotations

from typing import Any

_ROUTE_IMPORT_ERRORS = {
    "route_import_empty_file": "That spreadsheet has no rows.",
    "route_import_needs_two_stops": "This file needs at least a pickup and a drop.",
    "route_import_no_mapping_to_save": "Map the columns first, then save that mapping.",
    "route_import_no_raw_rows": "Upload the spreadsheet again, then load a mapping.",
    "mapping_profile_not_found": "That saved mapping was not found.",
    "route_import_not_found": "That import was not found.",
    "route_import_already_confirmed": (
        "This route is already booked. Change parcels on the order before a driver is assigned."
    ),
    "stop.geocode_failed": "Could not find this address.",
    "route_import_geocode_incomplete": "Addresses are still being located. Try again in a moment.",
    "route_import_optimize_pending": "Drop order is still updating. Try confirming in a moment.",
    "route_import_quote_missing": "Quote is not ready yet.",
    "stop.out_of_service_area": (
        "This stop is outside Ontario. Use a postal code starting with K, L, M, N, or P."
    ),
    "address.incomplete": "This address is incomplete.",
    "address.postal_invalid": "This postal code is not valid.",
    "address.approximate": "This address is only approximate — confirm it before booking.",
    "mapping.address_low_confidence": "Could not confidently map an address column — review the mapping.",
}


def route_import_error_message(code: str) -> str:
    key = (code or "").strip()
    if key in _ROUTE_IMPORT_ERRORS:
        return _ROUTE_IMPORT_ERRORS[key]
    if " " in key:
        return key
    return "That import could not be completed."


def route_row_error(*, row: int | None, code: str, field: str | None = "address") -> dict[str, Any]:
    """Classic bulk shape: row, error, message — plus optional field."""
    payload: dict[str, Any] = {
        "row": row,
        "error": code,
        "message": route_import_error_message(code),
    }
    if field:
        payload["field"] = field
    return payload


def stop_sheet_row(stop: dict[str, Any], index: int) -> int:
    raw = stop.get("row")
    if raw not in (None, ""):
        try:
            value = int(raw)
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    seq = stop.get("sequence")
    if seq not in (None, ""):
        try:
            return int(seq)
        except (TypeError, ValueError):
            pass
    return index + 1


def normalize_route_errors(raw: list[Any] | None) -> list[dict[str, Any]]:
    """Turn {index, codes} (and mapping codes) into classic bulk {row, error, message}."""
    out: list[dict[str, Any]] = []
    for err in raw or []:
        if not isinstance(err, dict):
            continue
        if err.get("error") and "codes" not in err:
            code = str(err.get("error") or err.get("code") or "")
            row = err.get("row")
            if row not in (None, ""):
                try:
                    row = int(row)
                except (TypeError, ValueError):
                    pass
            payload = route_row_error(
                row=row if isinstance(row, int) else None, code=code, field=err.get("field") or "address"
            )
            if err.get("message"):
                payload["message"] = str(err["message"])
            out.append(payload)
            continue
        if err.get("code") and "codes" not in err and "index" not in err:
            row = err.get("row")
            try:
                row_n = int(row) if row not in (None, "") else None
            except (TypeError, ValueError):
                row_n = None
            out.append(route_row_error(row=row_n, code=str(err["code"]), field=err.get("field") or "address"))
            continue
        index = 0
        try:
            index = int(err.get("index") or 0)
        except (TypeError, ValueError):
            index = 0
        row = err.get("row")
        try:
            row_n = int(row) if row not in (None, "") else index + 1
        except (TypeError, ValueError):
            row_n = index + 1
        codes = err.get("codes") or [err.get("code") or err.get("error") or "stop.geocode_failed"]
        for code in codes:
            out.append(route_row_error(row=row_n, code=str(code)))
    return out
