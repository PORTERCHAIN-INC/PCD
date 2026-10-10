"""Read SystemConfig policy/wired rows for runtime — no writes.

Mirrors merchant_engine.config_read for platform settings_* keys.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_engine.config_read import config_dict

_DRIVER_KEY = "settings_driver"
_CUSTOMER_KEY = "settings_customer"
_FINANCE_KEY = "settings_finance"
_COVERAGE_KEY = "settings_coverage"
_DOCUMENTS_KEY = "settings_documents"
_CLAIMS_KEY = "settings_claims"
_AUTOMATION_KEY = "settings_automation"
_GENERAL_KEY = "settings_general"


def driver_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _DRIVER_KEY)


def customer_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _CUSTOMER_KEY)


def finance_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _FINANCE_KEY)


def coverage_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _COVERAGE_KEY)


def document_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _DOCUMENTS_KEY)


def claims_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _CLAIMS_KEY)


def automation_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _AUTOMATION_KEY)


def general_settings(db: Session) -> dict[str, Any]:
    return config_dict(db, _GENERAL_KEY)


def document_expiry_alert_days(db: Session) -> int:
    raw = driver_settings(db).get("document_expiry_alert_days", 30)
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return 30
    return max(1, min(days, 365))


def background_check_required(db: Session) -> bool:
    return bool(driver_settings(db).get("background_check_required", True))


def portal_enabled(db: Session) -> bool:
    return bool(customer_settings(db).get("portal_enabled", True))


def booking_self_service(db: Session) -> bool:
    return bool(customer_settings(db).get("booking_self_service", True))


def invoice_number_prefix(db: Session) -> str:
    raw = finance_settings(db).get("invoice_number_prefix", "INV")
    text = str(raw or "INV").strip().upper() or "INV"
    return text[:12]


def receipt_number_prefix(db: Session) -> str:
    raw = finance_settings(db).get("receipt_number_prefix", "RCP")
    text = str(raw or "RCP").strip().upper() or "RCP"
    return text[:12]


def default_tax_percent(db: Session) -> float:
    raw = finance_settings(db).get("default_tax_percent", 13.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 13.0


def tax_cents_for_amount(db: Session, amount_cents: int) -> int:
    """Apply platform default tax percent to a pre-tax amount."""
    cents = max(0, int(amount_cents or 0))
    if cents <= 0:
        return 0
    return int(round(cents * default_tax_percent(db) / 100.0))


def document_max_file_size_mb(db: Session) -> int:
    raw = document_settings(db).get("max_file_size_mb", 25)
    try:
        mb = int(raw)
    except (TypeError, ValueError):
        return 25
    return max(1, min(mb, 100))


def document_max_bytes(db: Session) -> int:
    return document_max_file_size_mb(db) * 1024 * 1024


def document_allowed_types(db: Session) -> set[str]:
    raw = document_settings(db).get("allowed_types", ["pdf", "jpg", "png", "jpeg"])
    if not isinstance(raw, list):
        return {"pdf", "jpg", "png", "jpeg"}
    out = {str(item).strip().lower().lstrip(".") for item in raw if str(item).strip()}
    return out or {"pdf", "jpg", "png", "jpeg"}


def investigation_sla_hours(db: Session) -> int:
    raw = claims_settings(db).get("investigation_sla_hours", 72)
    try:
        hours = int(raw)
    except (TypeError, ValueError):
        return 72
    return max(1, min(hours, 24 * 30))


def max_compensation_cents(db: Session) -> int:
    raw = claims_settings(db).get("max_compensation_cents", 500_000)
    try:
        cents = int(raw)
    except (TypeError, ValueError):
        return 500_000
    return max(0, cents)


def queue_retry_max(db: Session) -> int:
    raw = automation_settings(db).get("queue_retry_max", 5)
    try:
        attempts = int(raw)
    except (TypeError, ValueError):
        return 5
    return max(1, min(attempts, 20))


def dispatch_retry_seconds(db: Session) -> int:
    raw = automation_settings(db).get("dispatch_retry_seconds", 60)
    try:
        seconds = int(raw)
    except (TypeError, ValueError):
        return 60
    return max(5, min(seconds, 3600))


def platform_company_name(db: Session) -> str:
    raw = general_settings(db).get("company_name", "Porterchain")
    text = str(raw or "Porterchain").strip()
    return text or "Porterchain"


def platform_support_email(db: Session) -> str | None:
    raw = general_settings(db).get("support_email")
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    return text or None


def active_coverage_cities(db: Session) -> set[str]:
    """Lowercased city names from coverage areas with active != False.

    Empty set means no restriction configured (fail open).
    """
    areas = coverage_settings(db).get("areas")
    if not isinstance(areas, list) or not areas:
        return set()
    out: set[str] = set()
    for row in areas:
        if not isinstance(row, dict):
            continue
        if row.get("active") is False:
            continue
        city = row.get("city")
        if isinstance(city, str) and city.strip():
            out.add(city.strip().lower())
    return out


def address_in_coverage(
    db: Session,
    *,
    formatted: str | None = None,
    city: str | None = None,
    postal: str | None = None,
) -> bool:
    """True when unrestricted, FSA is in GTA150 tile, or an active coverage city matches.

    Prefer FSA ∩ tile (Phase 1). City substring remains a soft assist when postal
    is missing (Places formatted text without extractable FSA).
    """
    from porterchain_pricing.components.fsa import normalize_fsa
    from porterchain_pricing.gta150_fsa import is_gta150_fsa

    fsa = normalize_fsa(postal or "")
    if not fsa and isinstance(formatted, str):
        fsa = normalize_fsa(formatted)
    if fsa:
        return is_gta150_fsa(fsa)

    allowed = active_coverage_cities(db)
    if not allowed:
        return True
    hay = " ".join(part for part in (city, formatted) if isinstance(part, str) and part.strip()).lower()
    if not hay.strip():
        return False
    return any(name in hay for name in allowed)


# --- Invoicing / Interac (CRA + e-Transfer) -------------------------------------------

def supplier_gst_hst_number(db: Session) -> str:
    """PorterChain's own GST/HST registration (BN + RT0001), the single source for every
    document. CRA requires it on invoices of $100+. Empty when unset: documents omit the
    line (never a placeholder) and admin shows a warning (see platform.tax_registration)."""
    from porterchain_api.platform.tax_registration import safe_gst_hst

    return safe_gst_hst(finance_settings(db).get("gst_hst_number"))


def tax_label(db: Session) -> str:
    pct = default_tax_percent(db)
    name = str(finance_settings(db).get("tax_name") or "HST").strip() or "HST"
    return f"{name} {pct:g}%"


def etransfer_recipient_email(db: Session) -> str:
    raw = str(finance_settings(db).get("etransfer_email") or "").strip()
    return raw or "billing@porterchain.com"


def etransfer_autodeposit(db: Session) -> bool:
    return bool(finance_settings(db).get("etransfer_autodeposit", True))


def tax_mode(db: Session) -> str:
    """"exclusive" (default, B2B norm): rates are pre-tax, tax added on top.
    "inclusive": prices already include tax; tax is extracted."""
    raw = str(finance_settings(db).get("tax_mode") or "exclusive").strip().lower()
    return raw if raw in ("exclusive", "inclusive") else "exclusive"


def default_tax_province(db: Session) -> str:
    return (str(finance_settings(db).get("default_tax_province") or "ON").strip().upper() or "ON")[:2]


def collect_qst(db: Session) -> bool:
    return bool(finance_settings(db).get("collect_qst", False))


def finance_number(db: Session, key: str, default: float) -> float:
    try:
        return float(finance_settings(db).get(key, default))
    except (TypeError, ValueError):
        return default


def merchant_cycle_invoicing_enabled(db: Session) -> bool:
    return bool(finance_settings(db).get("merchant_cycle_invoicing", True))
