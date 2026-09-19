"""English copy for merchant integrations (keys, webhooks, Shopify)."""

from __future__ import annotations

_ERRORS = {
    "api_key_not_found": "That API key was not found.",
    "webhook_not_found": "That webhook was not found.",
    "delivery_not_found": "That webhook delivery was not found.",
    "rate_limits_admin_owned": "Rate limits are set by PorterChain.",
    "sandbox_mode_blocks_production_writes": "Sandbox is on. Use a sandbox key or turn sandbox off.",
    "shop_domain_invalid": "Use a shop domain like store.myshopify.com.",
    "admin_access_token_required": "Paste the Shopify Admin API token.",
    "pickup_address_required": "Choose a default pickup location before connecting Shopify.",
    "pickup_address_not_found": "That pickup location was not found.",
    "shop_already_connected": "That Shopify store is already connected to another company.",
    "shopify_email_already_bound": "That Shopify email is already linked to a company with another store. Sign in to that company or use a different shop.",
    "shop_not_found": "That Shopify store was not found.",
    "shop_not_connected": "That Shopify store is not connected.",
    "shopify_oauth_not_configured": "Shopify install is not configured on this server.",
    "oauth_state_invalid": "That Shopify install link is not valid.",
    "oauth_state_expired": "That Shopify install link expired. Try again.",
    "oauth_hmac_invalid": "Shopify could not verify this install.",
    "oauth_token_missing": "Shopify did not return an access token.",
    "payload_invalid": "That Shopify payload could not be read.",
    "geocode_failed": "That pickup or dropoff address could not be located.",
    "merchant_not_found": "That company was not found.",
    "template_not_found": "That CSV template was not found.",
}


def integration_error_message(code: str) -> str:
    key = (code or "").strip()
    if key in _ERRORS:
        return _ERRORS[key]
    if " " in key:
        return key
    return "That request could not be completed."
