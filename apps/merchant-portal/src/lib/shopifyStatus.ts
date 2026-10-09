/** Plain-English copy for Shopify install errors and checkout-rate status (API codes). */

export const SHOPIFY_SUPPORT_EMAIL = "support@porterchain.com";

const INSTALL_ERRORS: Record<string, string> = {
  shop_already_connected:
    "This Shopify store is already linked to another PorterChain account. Sign in with the account that installed it, or email support@porterchain.com and we will move it to this account.",
  shopify_email_already_bound:
    "This store's email is already used by a PorterChain account that has another store. Sign in to that account, or email support@porterchain.com.",
  oauth_state_expired: "The Shopify install link expired. Start the connection again.",
  oauth_state_invalid: "The Shopify install link was not valid. Start the connection again.",
  oauth_hmac_invalid:
    "Shopify could not verify this request. Open PorterChain Delivery from your Shopify admin again.",
  oauth_code_missing:
    "Shopify did not finish the authorization. Open PorterChain Delivery from your Shopify admin again.",
  oauth_token_missing: "Shopify did not return an access token. Try connecting again.",
  shop_domain_invalid: "That does not look like a Shopify store address (store.myshopify.com).",
  shopify_oauth_not_configured:
    "Shopify connections are temporarily unavailable. Try again shortly.",
  merchant_not_found: "Your PorterChain account was not found. Sign in again and retry.",
  merchant_suspended: "This PorterChain account is suspended. Email support@porterchain.com.",
  install_failed: "Shopify did not respond while connecting. Try again in a minute.",
};

const RATE_STATUS: Record<string, string> = {
  carrier_plan_unsupported:
    "Shopify did not enable PorterChain checkout rates because this store's plan does not include third-party carrier-calculated shipping. Ask Shopify to enable carrier-calculated shipping for the store, then retry rate setup.",
  carrier_scope_missing:
    "PorterChain does not have Shopify's shipping permission yet. Re-open the app from Shopify admin and approve the requested access, then retry.",
  carrier_no_token: "PorterChain is not authorized on this store yet. Connect the store first.",
  token_reauth_required:
    "Shopify no longer accepts PorterChain's saved access for this store. Open PorterChain Delivery from your Shopify admin and approve access again; checkout rates switch on right after.",
  carrier_register_failed:
    "Shopify did not accept PorterChain's checkout rates yet. Retry rate setup; if it keeps failing, email support@porterchain.com.",
};

export function shopifyInstallError(code: string | null | undefined): string | null {
  const key = (code ?? "").trim();
  if (!key) return null;
  return INSTALL_ERRORS[key] ?? "The Shopify connection could not be completed. Try again.";
}

/** null when rates are live in Shopify; otherwise what is missing. */
export function shopifyRatesProblem(status: string | null | undefined): string | null {
  const key = (status ?? "").trim();
  if (key === "ready") return null;
  return RATE_STATUS[key] ?? RATE_STATUS.carrier_register_failed;
}

const BLOCKING: Record<string, string> = {
  carrier_not_registered: "checkout rates are not registered in Shopify",
  token_reauth_required: "reopen the app from Shopify admin to approve access again",
  pickup_required: "add a pickup address",
  merchant_not_active: "your PorterChain account is awaiting activation",
  rate_card_required: "a rate card is needed before checkout can show prices",
  shop_not_connected: "connect the store",
  oauth_not_configured: "Shopify connections are temporarily unavailable",
};

const ADVISORIES: Record<string, string> = {
  carrier_rates_enable_in_shipping:
    "In Shopify admin, open Settings → Shipping and delivery, and make sure PorterChain rates are switched on for your Canada shipping zone (or Canada market). New Shopify versions no longer turn new carriers on automatically.",
  returns_scope_reapprove:
    "To sync Shopify returns, reopen PorterChain Delivery from your Shopify admin and approve the new returns permission.",
};

/** Non-blocking setup reminders (never mean "not live"). Unknown codes are skipped. */
export function shopifyAdvisoryTexts(advisories: string[] | undefined): string[] {
  return (advisories ?? [])
    .map((code) => ADVISORIES[code])
    .filter((text): text is string => !!text);
}

export function shopifyBlockingText(blocking: string[] | undefined): string | null {
  const parts = (blocking ?? []).map((code) => BLOCKING[code]).filter(Boolean);
  return parts.length ? `Not live yet: ${parts.join("; ")}.` : null;
}
