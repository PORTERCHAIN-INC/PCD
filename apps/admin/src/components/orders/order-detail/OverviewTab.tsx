"use client";

import { useState } from "react";
import Link from "next/link";
import { QuoteLines } from "@porterchain/ui/quote-lines";
import { formatCents } from "@porterchain/ui/utils";
import {
  formatState,
  orderSourceLabel,
  ordersApi,
  shopifyAdminUrl,
  PAYMENT_STYLES,
  SLA_STYLES,
  STATE_STYLES,
  type OrderDetail,
} from "@/lib/orders";
import { relativeTime, titleCase } from "@/lib/crmFormat";
import { Badge, Button } from "@/components/crm/primitives";
import { OrderMoneyDownloads } from "@/components/orders/sections/OrderMoneyDownloads";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Row } from "./shared";

export function OverviewTab({
  detail,
  live,
  onRefresh,
}: {
  detail: OrderDetail;
  live?: Record<string, unknown> | null;
  onRefresh?: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [shopifyBusy, setShopifyBusy] = useState<string | null>(null);
  const [shopifyErr, setShopifyErr] = useState<string | null>(null);

  async function releaseShopify() {
    setShopifyBusy("release");
    setShopifyErr(null);
    try {
      const token = await getApiToken();
      await ordersApi.shopifyRelease(token, detail.order_id);
      onRefresh?.();
    } catch (e) {
      setShopifyErr(e instanceof Error ? e.message : "Release failed");
    } finally {
      setShopifyBusy(null);
    }
  }

  async function repushShopify() {
    setShopifyBusy("repush");
    setShopifyErr(null);
    try {
      const token = await getApiToken();
      await ordersApi.shopifyRepushFulfillment(token, detail.order_id);
      onRefresh?.();
    } catch (e) {
      setShopifyErr(e instanceof Error ? e.message : "Re-push failed");
    } finally {
      setShopifyBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <h3 className="mb-3 font-semibold text-primary">Shipment</h3>
          <Row label="Service" value={detail.service_type || detail.vehicle_class || "—"} />
          <Row
            label="Goods"
            value={
              detail.booking_mode === "vehicle"
                ? "Whole vehicle"
                : (detail.parcels ?? [])
                    .map((parcel) => String(parcel.preset_label || parcel.name || "Parcel"))
                    .join(", ") || "—"
            }
          />
          <Row label="Pickup" value={detail.pickup} />
          <Row label="Destination" value={detail.destination} />
          <Row label="Special instructions" value={detail.special_instructions || "—"} />
        </div>
        <div>
          <h3 className="mb-3 font-semibold text-primary">Financial</h3>
          <Row
            label="Quote"
            value={detail.quote_amount_cents ? formatCents(detail.quote_amount_cents) : "—"}
          />
          <Row label="Order amount" value={formatCents(detail.amount_cents)} />
          <Row label="Payment" value={detail.payment_status || "—"} />
          <Row label="Invoice" value={detail.invoice_number || "Not generated"} mono />
        </div>
      </div>
      <div>
        <h3 className="mb-3 font-semibold text-primary">Source &amp; references</h3>
        <Row
          label="Source"
          value={detail.order_source_label || orderSourceLabel(detail.order_source)}
        />
        {detail.shopify ? (
          <>
            <Row
              label="Shopify order"
              value={detail.shopify.order_name || detail.shopify.order_id || "—"}
            />
            <Row label="Shop" value={detail.shopify.shop_domain || "—"} />
            <Row label="Fulfillment id" value={detail.shopify.fulfillment_id || "—"} mono />
            <Row
              label="Last tracking push"
              value={
                detail.shopify.last_tracking_push_at
                  ? relativeTime(detail.shopify.last_tracking_push_at)
                  : "—"
              }
            />
            <Row label="Tracking state" value={detail.shopify.last_tracking_state || "—"} />
            <Row
              label="Last tracking event"
              value={
                detail.shopify.last_event_status
                  ? titleCase(detail.shopify.last_event_status)
                  : "Not sent yet"
              }
            />
            <Row
              label="Event sent"
              value={
                detail.shopify.last_event_at ? relativeTime(detail.shopify.last_event_at) : "—"
              }
            />
            {detail.shopify.last_fulfillment_error ? (
              <p className="mt-1 text-xs text-red-700">{detail.shopify.last_fulfillment_error}</p>
            ) : null}
            {detail.shopify.held_for_ops || detail.state === "BOOKED" ? (
              <p className="mt-2 text-xs text-amber-700">
                Held for ops — release to Fleetbase when ready.
              </p>
            ) : null}
            <div className="mt-2 flex flex-wrap gap-2">
              {(detail.shopify.held_for_ops || detail.state === "BOOKED") &&
              detail.order_source === "SHOPIFY" ? (
                <Button
                  variant="primary"
                  className="text-xs"
                  disabled={shopifyBusy === "release"}
                  onClick={() => void releaseShopify()}
                >
                  {shopifyBusy === "release" ? "…" : "Release to Fleetbase"}
                </Button>
              ) : null}
              <Button
                variant="outline"
                className="text-xs"
                disabled={shopifyBusy === "repush"}
                onClick={() => void repushShopify()}
              >
                {shopifyBusy === "repush" ? "…" : "Re-push fulfillment"}
              </Button>
            </div>
            {shopifyErr ? <p className="mt-1 text-xs text-red-700">{shopifyErr}</p> : null}
            {detail.shopify.order_admin_url || shopifyAdminUrl(detail.shopify) ? (
              <p className="mt-2 text-sm">
                <a
                  className="text-secondary hover:underline"
                  href={
                    detail.shopify.order_admin_url || shopifyAdminUrl(detail.shopify) || undefined
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Open in Shopify
                </a>
              </p>
            ) : null}
          </>
        ) : (
          <>
            <Row label="PO" value={detail.purchase_order_number || "—"} />
            <Row label="Internal" value={detail.internal_reference || "—"} />
          </>
        )}
        <Row label="Cost centre" value={detail.cost_centre || "—"} />
      </div>
      {live && Object.keys(live).length > 0 && (
        <div>
          <h3 className="mb-3 font-semibold text-primary">Live execution</h3>
          <div className="rounded-xl bg-gray-bg p-3 text-xs">
            {live.driver_location ? (
              <Row label="Driver GPS" value={JSON.stringify(live.driver_location)} mono />
            ) : null}
            {live.eta ? (
              <Row
                label="Road / scheduled ETA"
                value={
                  typeof live.eta === "object" && live.eta !== null
                    ? [
                        (live.eta as { label?: string }).label,
                        (live.eta as { source?: string }).source
                          ? `(${(live.eta as { source?: string }).source})`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" ") || JSON.stringify(live.eta)
                    : String(live.eta)
                }
              />
            ) : null}
            {live.speed_kmh != null ? <Row label="Speed" value={`${live.speed_kmh} km/h`} /> : null}
          </div>
        </div>
      )}
      {(detail.duplicates as unknown[]).length > 0 && (
        <p className="text-sm text-amber-700">
          {(detail.duplicates as unknown[]).length} possible duplicate order(s) detected.
        </p>
      )}
    </div>
  );
}
