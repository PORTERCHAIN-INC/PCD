"use client";

import { publicEnv } from "@/lib/env";
import {
  shopifyAdminShippingUrl,
  shopifyInstallError,
  shopifyRatesProblem,
} from "@/lib/shopifyStatus";
import { useEffect, useState } from "react";

type EmbeddedSession = {
  shop_domain: string;
  rates: string;
  linked: boolean;
  company_name: string | null;
  link_token: string | null;
};

type AppBridge = { idToken(): Promise<string> };

/** App Bridge sets window.shopify once its CDN script has run. */
async function appBridge(): Promise<AppBridge> {
  for (let i = 0; i < 50; i++) {
    const bridge = (window as unknown as { shopify?: AppBridge }).shopify;
    if (bridge?.idToken) return bridge;
    await new Promise((r) => setTimeout(r, 100));
  }
  throw new Error("session_token_missing");
}

async function openSession(): Promise<EmbeddedSession> {
  const token = await (await appBridge()).idToken();
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/integrations/shopify/session`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(String(body.detail ?? "install_failed"));
  return body as EmbeddedSession;
}

/** Embedded app inside Shopify admin: one status, one next step. */
export default function EmbeddedShopifyApp() {
  const [session, setSession] = useState<EmbeddedSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    openSession()
      .then((s) => alive && setSession(s))
      .catch((e: unknown) => alive && setError(e instanceof Error ? e.message : "install_failed"));
    return () => {
      alive = false;
    };
  }, []);

  const portal = publicEnv.siteUrl;
  const ratesProblem = session ? shopifyRatesProblem(session.rates) : null;

  return (
    <main className="mx-auto max-w-xl space-y-5 px-4 py-8">
      <h1 className="text-2xl font-bold text-primary">PorterChain Delivery</h1>
      {error ? (
        <p
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          {shopifyInstallError(error)}
        </p>
      ) : !session ? (
        <p className="text-sm text-muted">Connecting your store…</p>
      ) : (
        <>
          {ratesProblem ? (
            <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {ratesProblem}
            </p>
          ) : (
            <div className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              <p>
                PorterChain is registered as a carrier on {session.shop_domain}. Shopify does not
                switch new carriers on by itself, so add PorterChain to your Canada shipping zone:
              </p>
              <ol className="list-decimal space-y-1 pl-5">
                <li>Open Settings → Shipping and delivery.</li>
                <li>
                  Open the shipping profile and the shipping zone that includes Canada (Ontario).
                </li>
                <li>Click Add rate, then choose “Use carrier or app to calculate rates”.</li>
                <li>Pick PorterChain, select its services, and click Done, then Save.</li>
              </ol>
              <a
                href={shopifyAdminShippingUrl(session.shop_domain)}
                target="_top"
                className="inline-flex min-h-11 items-center rounded-xl border border-emerald-300 bg-white px-4 font-semibold"
              >
                Open Shipping and delivery
              </a>
            </div>
          )}
          <p className="rounded-xl border border-primary/10 bg-white px-4 py-3 text-sm text-primary">
            PorterChain delivers in the Greater Toronto Area only. Orders shipping anywhere else
            (other provinces or countries) simply don&apos;t see a PorterChain rate at checkout;
            your other rates keep working.
          </p>
          {session.linked ? (
            <>
              <p className="text-sm text-primary">
                Linked to <strong>{session.company_name}</strong>. Pickups, orders and invoices live
                in the PorterChain portal.
              </p>
              <a
                href={`${portal}/shopify`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-white"
              >
                Open PorterChain portal
              </a>
            </>
          ) : (
            <>
              <p className="text-sm text-primary">
                Last step: link this store to your PorterChain account so its orders, pickup address
                and invoices are yours. New to PorterChain? You can create an account on the next
                screen.
              </p>
              <a
                href={`${portal}/shopify?link=${encodeURIComponent(session.link_token ?? "")}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-semibold text-white"
              >
                Link to my PorterChain account
              </a>
            </>
          )}
          <p className="text-xs text-muted">
            The app is free. Deliveries are invoiced monthly and paid by Interac e-Transfer.
          </p>
        </>
      )}
    </main>
  );
}
