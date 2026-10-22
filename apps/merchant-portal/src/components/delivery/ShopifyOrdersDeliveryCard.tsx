"use client";

import { useEffect, useState } from "react";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { listShopifyOrdersForDelivery, type MerchantShopifyOrderRow } from "@/lib/api";
import OrderDeliveryOptionsEditor from "./OrderDeliveryOptionsEditor";

/** Shopify page → recent Shopify orders with per-order delivery options. */
export default function ShopifyOrdersDeliveryCard() {
  const { getApiToken, orgId } = useMerchantAuth();
  const [rows, setRows] = useState<MerchantShopifyOrderRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const token = await getApiToken();
        if (!token) return;
        const next = await listShopifyOrdersForDelivery(token, orgId ?? undefined);
        if (live) setRows(next);
      } catch (err) {
        if (live) setError(err instanceof Error ? err.message : "Could not load Shopify orders");
      }
    })();
    return () => {
      live = false;
    };
  }, [getApiToken, orgId]);

  return (
    <section
      className="space-y-3 rounded-2xl border border-primary/10 bg-white p-6"
      data-testid="shopify-orders-delivery"
    >
      <div>
        <h2 className="text-base font-semibold text-primary">Shopify orders</h2>
        <p className="text-sm text-muted">
          Set leave at door, concierge, buzzer or call on arrival per order. Orders without options
          use your default from Settings.
        </p>
      </div>
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
      {rows === null && !error && <p className="text-sm text-muted">Loading…</p>}
      {rows?.length === 0 && <p className="text-sm text-muted">No Shopify orders yet.</p>}
      <ul className="divide-y divide-primary/10">
        {rows?.map((row) => (
          <li key={row.order_id} className="space-y-1 py-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <p className="text-sm font-medium text-primary">
                {row.shopify_order_name || row.order_number || row.tracking_number || row.order_id}
              </p>
              <span className="text-xs text-muted">
                {row.state.replaceAll("_", " ").toLowerCase()}
              </span>
            </div>
            {row.dropoff && <p className="text-xs text-muted">{row.dropoff}</p>}
            <OrderDeliveryOptionsEditor
              orderId={row.order_id}
              value={row.delivery_options}
              editable={row.editable}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}
