"""Shopify Billing API for stores installed through the PorterChain Shopify app.

App Store review 139170 (1.2.1 / 1.2.2): charges for deliveries booked from a Shopify
store go through Shopify, not Interac. One usage-based app subscription (no base fee,
capped) is approved by the merchant inside Shopify admin; each completed delivery is
an ``appUsageRecordCreate`` at the PorterChain price (pre-tax, same pricing engine:
$6 small / $9 van + surcharges, merchant vehicle hourly, or the admin custom price).

* Approve: the embedded app asks on first open (and again after a reinstall, because
  Shopify cancels the subscription on uninstall).
* Decline / not approved: bookings are blocked with a clear "approve charges" message.
* Direct (non-Shopify) merchants and merchant-made custom-app tokens are untouched and
  keep Interac e-Transfer invoices.
* ``test: true`` everywhere except APP_ENV=production (or SHOPIFY_BILLING_TEST).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.merchant_models import ShopifyShop

logger = logging.getLogger("porterchain.shopify_billing")

PLAN_NAME = "PorterChain Delivery (pay per delivery)"
TERMS = (
    "Charged per completed delivery at your PorterChain rate: small parcel CA$6, cargo van CA$9, "
    "plus any distance, weight or after-hours surcharge (or your agreed custom price). "
    "No monthly fee. If your Shopify bill is not in CAD, each charge is converted at the "
    "Bank of Canada daily rate."
)
PRICE_CURRENCY = "CAD"
# Monthly spending limits a merchant can pick (CAD). Changing it is the 1.2.3 "plan change".
CAP_CHOICES_CAD = (250, 500, 1000, 2500, 5000)
CAP_CODE = "shopify_billing_cap_reached"
CAP_MESSAGE = (
    "Your monthly PorterChain spending limit in Shopify is used up. Open Apps > PorterChain "
    "in your Shopify admin and raise the limit to keep booking."
)
BLOCK_CODE = "shopify_billing_not_approved"
BLOCK_MESSAGE = (
    "Approve PorterChain charges in Shopify before booking. Open Apps > PorterChain in your "
    "Shopify admin and choose Approve. Deliveries are billed through your Shopify invoice."
)


def test_mode(settings: Settings) -> bool:
    explicit = getattr(settings, "shopify_billing_test", None)
    if explicit is not None:
        return bool(explicit)
    return str(getattr(settings, "app_env", "local") or "local").lower() not in {"production", "prod"}


def billing_applies(shop: ShopifyShop | None, settings: Settings) -> bool:
    """Only stores installed through the Shopify app (token exchange). A store connected
    with a merchant-made custom app token cannot use the Billing API (Shopify refuses)."""
    if not shop or not getattr(settings, "shopify_billing_enabled", True):
        return False
    if getattr(shop, "uninstalled_at", None) is not None or not getattr(shop, "encrypted_access_token", None):
        return False
    # Only app installs (token exchange -> expiring offline token). Pasted custom-app tokens
    # and legacy rows cannot use the Billing API.
    return getattr(shop, "token_status", None) in ("expiring", "token_reauth_required")


def shopify_billed_shop(db: Session, settings: Settings, merchant_id: str) -> ShopifyShop | None:
    rows = (
        db.query(ShopifyShop)
        .filter(ShopifyShop.merchant_id == merchant_id, ShopifyShop.uninstalled_at.is_(None))
        .all()
    )
    return next((r for r in rows if billing_applies(r, settings)), None)


def is_shopify_billed(db: Session, settings: Settings, merchant_id: str) -> bool:
    return shopify_billed_shop(db, settings, merchant_id) is not None


def booking_block(db: Session, settings: Settings, merchant_id: str) -> str | None:
    shop = shopify_billed_shop(db, settings, merchant_id)
    if shop is not None and shop.billing_status == "cap_reached":
        return CAP_CODE
    if shop is not None and shop.billing_status != "active":
        return BLOCK_CODE
    return None


def block_message(code: str | None) -> str:
    return CAP_MESSAGE if code == CAP_CODE else BLOCK_MESSAGE


# ---------- currency (prices are set in CAD) ----------

# Used only when the Bank of Canada feed cannot be reached (CAD per 1 unit). Conservative.
_FX_FALLBACK = {"USD": 1.40, "EUR": 1.50, "GBP": 1.75, "AUD": 0.90, "NZD": 0.82, "JPY": 0.0093,
                "CHF": 1.60, "SEK": 0.13, "NOK": 0.13, "DKK": 0.20, "INR": 0.016, "MXN": 0.075,
                "BRL": 0.25, "HKD": 0.18, "SGD": 1.04, "CNY": 0.19, "ZAR": 0.076}
_fx_cache: dict[str, tuple[str, float]] = {}


def cad_per_unit(currency: str) -> float:
    """CAD value of 1 unit of `currency` (Bank of Canada Valet, free, cached per day)."""
    cur = (currency or "").upper()
    if cur == "CAD":
        return 1.0
    today = datetime.now(UTC).date().isoformat()
    hit = _fx_cache.get(cur)
    if hit and hit[0] == today:
        return hit[1]
    try:
        import httpx

        r = httpx.get(f"https://www.bankofcanada.ca/valet/observations/FX{cur}CAD/json?recent=1", timeout=5)
        obs = (r.json().get("observations") or [])[-1]
        rate = float(obs[f"FX{cur}CAD"]["v"])
        if rate <= 0:
            raise ValueError("bad_rate")
    except Exception:  # noqa: BLE001
        rate = _FX_FALLBACK.get(cur, 0.0)
        if rate <= 0:
            raise RuntimeError(f"shopify_billing_fx_unavailable:{cur}") from None
        logger.warning("shopify_billing_fx_fallback currency=%s", cur)
    _fx_cache[cur] = (today, rate)
    return rate


def to_billing_currency(amount_cad: float, currency: str) -> float:
    return round(float(amount_cad) / cad_per_unit(currency), 2)


def _gql(shop: ShopifyShop, settings: Settings, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    from porterchain_api.merchant_engine.shopify_admin_graphql import ShopifyAdminError, admin_graphql
    from porterchain_api.merchant_engine.shopify_tokens import access_token_for

    token = access_token_for(shop, settings)
    if not token:
        raise ShopifyAdminError("missing_access_token")
    return admin_graphql(shop.shop_domain, token, settings, query, variables)


_ACTIVE_Q = """
query { currentAppInstallation { activeSubscriptions { id name status test
  lineItems { id plan { pricingDetails { __typename
    ... on AppUsagePricing { cappedAmount { amount currencyCode } balanceUsed { amount currencyCode } } } } } } } }
"""
_last_usage: dict[str, dict[str, Any]] = {}


def _set(shop: ShopifyShop, status: str | None, **extra: Any) -> None:
    shop.billing_status = status
    for k, v in extra.items():
        setattr(shop, k, v)
    shop.billing_updated_at = datetime.now(UTC)


def refresh_status(db: Session, settings: Settings, shop: ShopifyShop) -> str | None:
    """Ask Shopify which subscription is active; Shopify is the source of truth."""
    data = _gql(shop, settings, _ACTIVE_Q)
    subs = ((data.get("currentAppInstallation") or {}).get("activeSubscriptions")) or []
    active = next((s for s in subs if str(s.get("status")) == "ACTIVE"), None)
    if active:
        usage_li = next(
            (
                li
                for li in active.get("lineItems") or []
                if ((li.get("plan") or {}).get("pricingDetails") or {}).get("__typename") == "AppUsagePricing"
            ),
            None,
        )
        usage = (usage_li or {}).get("id")
        pd = ((usage_li or {}).get("plan") or {}).get("pricingDetails") or {}
        cap = float(((pd.get("cappedAmount") or {}).get("amount")) or 0)
        used = float(((pd.get("balanceUsed") or {}).get("amount")) or 0)
        cur = ((pd.get("cappedAmount") or {}).get("currencyCode")) or None
        _last_usage[shop.shop_domain] = {"capped_amount": cap, "balance_used": used, "currency": cur}
        _set(
            shop,
            "cap_reached" if cap > 0 and used >= cap else "active",
            billing_subscription_gid=active.get("id"),
            billing_usage_line_item_gid=usage,
            billing_test=bool(active.get("test")),
        )
    elif shop.billing_status in {"pending", "active", "cap_reached"}:
        # Asked but nothing active: the merchant declined (or Shopify cancelled it).
        _set(shop, "declined" if shop.billing_status == "pending" else "cancelled",
             billing_usage_line_item_gid=None)
    db.commit()
    return shop.billing_status


def return_url(settings: Settings, shop: ShopifyShop) -> str:
    base = str(settings.porterchain_api_url).rstrip("/")
    return f"{base}/v1/integrations/shopify/billing/return?" + urlencode({"shop": shop.shop_domain})


_CREATE_M = """
mutation Sub($name: String!, $returnUrl: URL!, $test: Boolean, $lineItems: [AppSubscriptionLineItemInput!]!) {
  appSubscriptionCreate(name: $name, returnUrl: $returnUrl, test: $test, lineItems: $lineItems) {
    confirmationUrl appSubscription { id status } userErrors { field message } } }
"""

_CURRENCY_Q = "query { shopBillingPreferences { currency } }"


def _billing_currency(shop: ShopifyShop, settings: Settings) -> str:
    """The currency Shopify bills this merchant in. Raises if unknown: never guess."""
    data = _gql(shop, settings, _CURRENCY_Q)
    cur = str(((data.get("shopBillingPreferences") or {}).get("currency")) or "").upper()
    if not cur:
        raise RuntimeError("shopify_billing_currency_unknown")
    return cur


def request_approval(db: Session, settings: Settings, shop: ShopifyShop) -> str:
    """Create the usage subscription and return Shopify's approval page URL."""
    from porterchain_api.merchant_engine.shopify_admin_graphql import _payload

    currency = _billing_currency(shop, settings)
    variables = {
        "name": PLAN_NAME,
        "returnUrl": return_url(settings, shop),
        "test": test_mode(settings),
        "lineItems": [
            {
                "plan": {
                    "appUsagePricingDetails": {
                        "terms": TERMS,
                        "cappedAmount": {
                            "amount": to_billing_currency(float(settings.shopify_billing_capped_amount), currency),
                            "currencyCode": currency,
                        },
                    }
                }
            }
        ],
    }
    block = _payload(_gql(shop, settings, _CREATE_M, variables), "appSubscriptionCreate")
    url = str(block.get("confirmationUrl") or "")
    if not url:
        raise RuntimeError("shopify_billing_no_confirmation_url")
    sub = block.get("appSubscription") or {}
    _set(shop, "pending", billing_subscription_gid=sub.get("id"), billing_test=test_mode(settings))
    db.commit()
    return url


def status_payload(db: Session, settings: Settings, shop: ShopifyShop | None, *, create: bool = True) -> dict[str, Any]:
    """What the embedded app shows. Never raises: billing trouble must not hide the app."""
    if not billing_applies(shop, settings):
        return {"required": False, "status": "not_required"}
    assert shop is not None
    try:
        status = refresh_status(db, settings, shop)
    except Exception as exc:  # noqa: BLE001
        logger.warning("shopify_billing_refresh_failed shop=%s err=%s", shop.shop_domain, exc)
        status = shop.billing_status
    out: dict[str, Any] = {
        "required": True,
        "status": status or "not_requested",
        "plan": PLAN_NAME,
        "terms": TERMS,
        "test": test_mode(settings),
        "capped_amount": float(settings.shopify_billing_capped_amount),
    }
    out["cap_choices_cad"] = list(CAP_CHOICES_CAD)
    if shop.shop_domain in _last_usage:
        out["usage"] = _last_usage[shop.shop_domain]
    if status == "active":
        return out
    if status == "cap_reached":
        out["message"] = CAP_MESSAGE
        return out
    if create:
        try:
            out["confirmation_url"] = request_approval(db, settings, shop)
            # keep showing "declined" so the page can explain why booking is blocked
            out["status"] = status if status in {"declined", "cancelled"} else "pending"
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.warning("shopify_billing_create_failed shop=%s err=%s", shop.shop_domain, exc)
            out["error"] = "billing_request_failed"
    return out


_USAGE_M = """
mutation Use($id: ID!, $price: MoneyInput!, $description: String!, $key: String) {
  appUsageRecordCreate(subscriptionLineItemId: $id, price: $price, description: $description, idempotencyKey: $key) {
    appUsageRecord { id } userErrors { field message } } }
"""


def record_usage(db: Session, settings: Settings, order: Any) -> dict[str, Any]:
    """Charge one completed delivery through Shopify. Idempotent per order."""
    from porterchain_api.merchant_engine.shopify_admin_graphql import _payload

    shop = shopify_billed_shop(db, settings, order.merchant_id)
    if shop is None:
        return {"skipped": "not_shopify_billed"}
    if getattr(order, "is_sandbox", False) and not test_mode(settings):
        return {"skipped": "sandbox_order"}
    extra = dict(order.compliance_metadata or {})
    meta = dict(extra.get("shopify_billing") or {})
    if meta.get("usage_record_id"):
        return {"skipped": "already_charged", "usage_record_id": meta["usage_record_id"]}
    cents = int(order.amount_cents or 0)
    if cents <= 0:
        return {"skipped": "zero_amount"}
    if shop.billing_status != "active" or not shop.billing_usage_line_item_gid:
        try:
            refresh_status(db, settings, shop)
        except Exception:  # noqa: BLE001
            pass
    if shop.billing_status != "active" or not shop.billing_usage_line_item_gid:
        meta.update({"status": "pending_approval", "at": datetime.now(UTC).isoformat()})
        extra["shopify_billing"] = meta
        order.compliance_metadata = extra
        db.commit()
        return {"skipped": BLOCK_CODE}
    try:
        currency = _billing_currency(shop, settings)
        amount = to_billing_currency(cents / 100, currency)
    except Exception as exc:  # noqa: BLE001
        meta.update({"status": "error", "error": str(exc)[:200], "at": datetime.now(UTC).isoformat()})
        extra["shopify_billing"] = meta
        order.compliance_metadata = extra
        db.commit()
        return {"error": str(exc)[:200]}
    variables = {
        "id": shop.billing_usage_line_item_gid,
        "price": {"amount": amount, "currencyCode": currency},
        "description": f"PorterChain delivery {order.tracking_number or order.id}",
        "key": f"pc-order-{order.id}",
    }
    try:
        block = _payload(_gql(shop, settings, _USAGE_M, variables), "appUsageRecordCreate")
    except Exception as exc:  # noqa: BLE001
        meta.update({"status": "error", "error": str(exc)[:200], "at": datetime.now(UTC).isoformat()})
        extra["shopify_billing"] = meta
        order.compliance_metadata = extra
        db.commit()
        logger.warning("shopify_usage_failed order=%s err=%s", order.id, exc)
        return {"error": str(exc)[:200]}
    rec = (block.get("appUsageRecord") or {}).get("id")
    meta.update({
        "status": "charged", "usage_record_id": rec, "amount_cents": cents, "price_currency": PRICE_CURRENCY,
        "charged_amount": amount, "currency": currency,
        "test": bool(shop.billing_test), "shop_domain": shop.shop_domain,
        "at": datetime.now(UTC).isoformat(),
    })
    extra["shopify_billing"] = meta
    order.compliance_metadata = extra
    db.commit()
    return {"ok": True, "usage_record_id": rec}


def on_uninstall(shop: ShopifyShop) -> None:
    """Shopify cancels app subscriptions on uninstall; a reinstall must ask again."""
    _set(shop, None, billing_subscription_gid=None, billing_usage_line_item_gid=None)


_CAP_M = """
mutation Cap($id: ID!, $cap: MoneyInput!) {
  appSubscriptionLineItemUpdate(id: $id, cappedAmount: $cap) { confirmationUrl userErrors { field message } } }
"""


def change_cap(db: Session, settings: Settings, shop: ShopifyShop, amount_cad: float) -> str:
    """1.2.3: the merchant raises or lowers the monthly limit from inside the app.
    Shopify shows its own approval page; returns that URL."""
    from porterchain_api.merchant_engine.shopify_admin_graphql import _payload

    if float(amount_cad) not in {float(x) for x in CAP_CHOICES_CAD}:
        raise ValueError("cap_not_allowed")
    if not billing_applies(shop, settings):
        raise ValueError("billing_not_required")
    refresh_status(db, settings, shop)
    if shop.billing_status not in {"active", "cap_reached"} or not shop.billing_usage_line_item_gid:
        raise ValueError("billing_not_active")
    currency = _billing_currency(shop, settings)
    variables = {"id": shop.billing_usage_line_item_gid,
                 "cap": {"amount": to_billing_currency(float(amount_cad), currency), "currencyCode": currency}}
    block = _payload(_gql(shop, settings, _CAP_M, variables), "appSubscriptionLineItemUpdate")
    url = str(block.get("confirmationUrl") or "")
    if not url:
        raise RuntimeError("shopify_billing_no_confirmation_url")
    return url
