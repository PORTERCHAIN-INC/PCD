import { getPorterchainApiBase } from "@/lib/api-base";
import {
  adminSignInUrl,
  customerPortalBookUrl,
  customerPortalDashboardUrl,
  driverSignInUrl,
  merchantPortalUrl,
} from "@/data/portal-links";
import {
  canAccessPortal,
  fetchSessionContext as fetchSharedSessionContext,
  type PorterchainPortal,
  type SessionContext,
} from "@porterchain/auth";
import { readQuoteIntent, withVisitorHandoff } from "@/lib/visitor-tracking";

export type { SessionContext };

/** Website Platform Clerk only routes retail personas. */
const RETAIL_PORTALS = ["merchant", "customer"] as const satisfies readonly PorterchainPortal[];

const PORTAL_HOME: Record<(typeof RETAIL_PORTALS)[number], string> = {
  merchant: merchantPortalUrl,
  // Mobile welcome home — primary CTA is quote/book.
  customer: customerPortalDashboardUrl,
};

function customerHomeUrl(): string {
  const intent = readQuoteIntent();
  if (intent.intent === "quote") {
    return withVisitorHandoff(customerPortalBookUrl, {
      intent: "quote",
      from: intent.from,
      vehicle: intent.vehicle,
    });
  }
  return withVisitorHandoff(customerPortalDashboardUrl);
}

const PORTAL_LABEL: Record<(typeof RETAIL_PORTALS)[number], string> = {
  merchant: "Merchant",
  customer: "Customer",
};

export async function fetchSessionContext(token: string): Promise<SessionContext> {
  return fetchSharedSessionContext(getPorterchainApiBase(), token);
}

/**
 * Ensure a customers row + SpiceDB owner exist for a Platform retail session.
 * Call before routing when session-context has no portal permissions yet.
 */
export async function ensureCustomerPersona(token: string): Promise<void> {
  const base = getPorterchainApiBase().replace(/\/$/, "");
  const res = await fetch(`${base}/v1/auth/customer/onboarding`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      "X-Porterchain-Portal": "customer",
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(detail || `customer_onboarding_${res.status}`);
  }
}

/** Retail portals this Platform session may open (customer / merchant only). */
export function retailPortalChoicesFromSession(
  ctx: Pick<SessionContext, "permissions">
): Array<{ portal: (typeof RETAIL_PORTALS)[number]; url: string; label: string }> {
  return RETAIL_PORTALS.filter((portal) => canAccessPortal(ctx.permissions, portal)).map(
    (portal) => ({
      portal,
      url: portal === "customer" ? customerHomeUrl() : PORTAL_HOME[portal],
      label: PORTAL_LABEL[portal],
    })
  );
}

/** @deprecated Use retailPortalChoicesFromSession — website is retail-only. */
export function portalChoicesFromSession(
  ctx: Pick<SessionContext, "permissions">
): Array<{ portal: PorterchainPortal; url: string; label: string }> {
  return retailPortalChoicesFromSession(ctx);
}

export function portalHomeUrlFromSession(ctx: SessionContext): string | null {
  const choices = retailPortalChoicesFromSession(ctx);
  return choices[0]?.url ?? null;
}

/** Non-retail access detected after Platform login — point to the correct IdP. */
export function nonRetailSignInHints(
  ctx: Pick<SessionContext, "permissions">
): Array<{ kind: "admin" | "driver"; url: string }> {
  const hints: Array<{ kind: "admin" | "driver"; url: string }> = [];
  if (canAccessPortal(ctx.permissions, "admin")) {
    hints.push({ kind: "admin", url: adminSignInUrl });
  }
  if (canAccessPortal(ctx.permissions, "driver")) {
    hints.push({ kind: "driver", url: driverSignInUrl });
  }
  return hints;
}
