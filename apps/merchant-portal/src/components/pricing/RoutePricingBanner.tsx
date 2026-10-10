"use client";

import { useEffect, useState } from "react";
import { getRoutePricing, setRoutePricing, type RoutePricingStatus } from "@/lib/api";

const money = (c: number) => `$${(c / 100).toFixed(2)}`;

/** In-app notice for the new route pricing: their old vs new examples and one Opt in button. */
export default function RoutePricingBanner({
  getToken,
  orgId,
  setting = false,
}: {
  getToken: () => Promise<string | null>;
  orgId?: string;
  /** Billing page: always show the current state with an on/off switch. */
  setting?: boolean;
}) {
  const [status, setStatus] = useState<RoutePricingStatus | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    void getToken().then((t) => {
      if (!t) return;
      getRoutePricing(t, orgId)
        .then((s) => live && setStatus(s))
        .catch(() => undefined); // no billing access: no banner
    });
    return () => {
      live = false;
    };
  }, [getToken, orgId]);

  async function act(action: "opt_in" | "opt_out" | "dismiss") {
    const t = await getToken();
    if (!t) return;
    setBusy(true);
    try {
      setStatus(await setRoutePricing(t, action, orgId));
    } finally {
      setBusy(false);
    }
  }

  if (!status) return null;
  if (setting) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/10 bg-white px-4 py-3 text-sm">
        <span>
          <strong>Route pricing:</strong> {status.opted_in ? "on" : "off (current prices)"}
        </span>
        <button
          type="button"
          disabled={busy}
          onClick={() => void act(status.opted_in ? "opt_out" : "opt_in")}
          className="min-h-10 rounded-xl border border-primary/15 px-3 py-1.5 font-semibold text-primary disabled:opacity-60"
        >
          {status.opted_in ? "Switch back to current prices" : "Opt in"}
        </button>
      </div>
    );
  }
  if (status.opted_in) {
    return status.opted_in_at && Date.now() - Date.parse(status.opted_in_at) < 7 * 86_400_000 ? (
      <p role="status" className="rounded-xl bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
        Route pricing is on for your account. New bookings, quotes and Shopify checkout rates use
        it.
      </p>
    ) : null;
  }
  if (!status.show_banner) return null;
  return (
    <section
      aria-labelledby="route-pricing-title"
      className="rounded-2xl border border-primary/10 bg-white p-5 shadow-sm"
    >
      <h2 id="route-pricing-title" className="text-lg font-bold text-primary">
        New: route pricing
      </h2>
      <p className="mt-1 text-sm text-primary/80">{status.summary}</p>
      {status.examples.length ? (
        <table className="mt-3 w-full text-left text-sm">
          <caption className="sr-only">Your price today vs route pricing</caption>
          <thead>
            <tr className="text-xs text-primary/70">
              <th scope="col" className="py-1">
                Example (1 parcel, cargo van)
              </th>
              <th scope="col" className="py-1 text-right">
                Today
              </th>
              <th scope="col" className="py-1 text-right">
                Route pricing
              </th>
            </tr>
          </thead>
          <tbody>
            {status.examples.map((e) => (
              <tr key={e.to_fsa} className="border-t border-primary/5">
                <td className="py-1">
                  {e.from_fsa} → {e.to_fsa}
                  {e.route_km != null ? ` · ${e.route_km} km` : ""}
                </td>
                <td className="py-1 text-right">{money(e.old_cents)}</td>
                <td className="py-1 text-right font-semibold">{money(e.new_cents)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <p className="mt-2 text-xs text-primary/70">
        Prices before HST. Liftgate, coverage and waiting charges are unchanged. You can switch back
        any time in Billing.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void act("opt_in")}
          className="min-h-11 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          Opt in
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void act("dismiss")}
          className="min-h-11 rounded-xl px-4 py-2 text-sm font-semibold text-primary/80"
        >
          Not now
        </button>
      </div>
    </section>
  );
}
