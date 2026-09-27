"use client";

import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import {
  orderSourceLabel,
  orderStateLabel,
  packageLabel,
  slaStatusLabel,
  vehicleLabel,
} from "@/lib/catalog";
import type { OrderDetail } from "@/lib/orders";
import { formatCents, formatDate } from "@/lib/utils";
import Link from "next/link";
import { Card, pickupWindowFromStops } from "./shared";

function shopifyEventLabel(status: string | null | undefined): string {
  if (!status) return "Not sent yet";
  return status
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function OverviewTab({ detail }: { detail: OrderDetail }) {
  const pickupWindow = pickupWindowFromStops(detail.stops);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Pickup">
        <p>{String(detail.pickup_detail?.formatted ?? detail.pickup)}</p>
      </Card>
      <Card title="Delivery">
        <p>{String(detail.dropoff_detail?.formatted ?? detail.destination)}</p>
      </Card>
      <Card title="References">
        <p>Source: {detail.order_source_label || orderSourceLabel(detail.order_source)}</p>
        {detail.shopify ? (
          <>
            <p className="mt-1">
              Shopify order: {detail.shopify.order_name || detail.shopify.order_id || "—"}
            </p>
            {detail.shopify.shop_domain ? (
              <p className="mt-1">Shop: {detail.shopify.shop_domain}</p>
            ) : null}
            <p className="mt-1">
              Fulfillment: {detail.shopify.fulfillment_id || "Not created yet"}
            </p>
            <p className="mt-1">
              Last tracking event: {shopifyEventLabel(detail.shopify.last_event_status)}
              {detail.shopify.last_event_at ? ` · ${formatDate(detail.shopify.last_event_at)}` : ""}
            </p>
            {detail.shopify.order_admin_url ? (
              <a
                className="mt-1 inline-block text-secondary hover:underline"
                href={detail.shopify.order_admin_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open in Shopify
              </a>
            ) : null}
          </>
        ) : (
          <>
            <p className="mt-1">PO: {detail.purchase_order_number ?? "—"}</p>
            <p className="mt-1">Internal: {detail.internal_reference ?? "—"}</p>
          </>
        )}
        <p className="mt-1">Cost centre: {detail.cost_centre ?? "—"}</p>
      </Card>
      <Card title="Operations">
        <p>Driver: {detail.driver_name ?? "—"}</p>
        <p className="mt-1">
          Vehicle: {detail.vehicle_label ?? vehicleLabel(detail.vehicle_class)}
        </p>
        <p className="mt-1">SLA: {slaStatusLabel(detail.sla_status)}</p>
        {pickupWindow ? <p className="mt-1">Pickup window: {pickupWindow}</p> : null}
      </Card>
      {detail.stops?.length || detail.packages?.length ? (
        <Card title="Stops and parcels">
          {detail.stops?.length
            ? detail.stops.map((stop, i) => (
                <div key={i} className="mb-3 last:mb-0">
                  <p className="font-medium">
                    {String(stop.stop_type || stop.type || `Stop ${i + 1}`)} ·{" "}
                    {String(stop.formatted || stop.address || "—")}
                  </p>
                  {stop.time_window_start || stop.time_window_end ? (
                    <p className="text-xs text-muted">
                      Window:{" "}
                      {stop.time_window_start ? formatDate(String(stop.time_window_start)) : "?"} –{" "}
                      {stop.time_window_end ? formatDate(String(stop.time_window_end)) : "?"}
                    </p>
                  ) : null}
                  {Array.isArray(stop.packages) && stop.packages.length > 0 ? (
                    <ul className="mt-1 list-disc pl-5 text-muted">
                      {(stop.packages as Array<Record<string, unknown>>).map((pkg, j) => (
                        <li key={j}>
                          {String(pkg.name || pkg.sku || `Parcel ${j + 1}`)}
                          {pkg.weight_kg != null ? ` · ${String(pkg.weight_kg)} kg` : ""}
                          {pkg.notes ? ` · ${String(pkg.notes)}` : ""}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ))
            : detail.packages.map((pkg, i) => (
                <p key={i} className="mt-1">
                  {String(pkg.name || pkg.package_type || `Parcel ${i + 1}`)}
                  {pkg.weight_kg != null ? ` · ${String(pkg.weight_kg)} kg` : ""}
                </p>
              ))}
          {detail.route_import_job_id ? (
            <Link
              className="mt-2 inline-block text-secondary hover:underline"
              href={`/routes/${detail.route_import_job_id}`}
            >
              Open route job
            </Link>
          ) : null}
        </Card>
      ) : null}
    </div>
  );
}
