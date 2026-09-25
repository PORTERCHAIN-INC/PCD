"use client";

import { QuoteLines } from "@/components/billing/QuoteLines";
import { packageLabel, vehicleLabel } from "@/lib/catalog";
import type { OrderDetail } from "@/lib/orders";
import { formatCents } from "@/lib/utils";
import { Card } from "./shared";

export function PricingTab({ detail }: { detail: OrderDetail }) {
  const currency = detail.currency.toUpperCase();
  return (
    <Card title="Pricing">
      <p className="text-muted">Vehicle: {vehicleLabel(detail.vehicle_class)}</p>
      <p className="mt-1 text-muted">Package: {packageLabel(detail.package_type)}</p>
      <div className="mt-3">
        <QuoteLines
          breakdown={detail.pricing_breakdown}
          quotedCents={detail.quote_amount_cents}
          chargedCents={detail.amount_cents}
          currency={currency}
        />
      </div>
      {detail.quote_amount_cents == null && !detail.pricing_breakdown ? (
        <p className="mt-2 text-muted">
          Charged: {formatCents(detail.amount_cents, currency)} · no stored quote on this order
        </p>
      ) : null}
    </Card>
  );
}
