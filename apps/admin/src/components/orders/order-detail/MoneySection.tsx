"use client";

import Link from "next/link";
import { QuoteLines } from "@porterchain/ui/quote-lines";
import { cn, formatCents } from "@porterchain/ui/utils";
import { PAYMENT_STYLES, type OrderDetail } from "@/lib/orders";
import { SectionBlock } from "@/components/orders/sections";
import { OrderMoneyDownloads } from "@/components/orders/sections/OrderMoneyDownloads";
import { Row } from "./shared";

export function PaymentsTab({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-3">
      {detail.payments.map((p) => (
        <div key={p.payment_id} className="rounded-xl border border-primary/10 p-3 text-sm">
          <div className="mb-1 flex justify-between">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold",
                PAYMENT_STYLES[p.status] ?? "bg-gray-100"
              )}
            >
              {p.status}
            </span>
            <span className="font-semibold">{formatCents(p.amount_cents)}</span>
          </div>
          {p.stripe_payment_intent_id && (
            <Row label="Payment intent" value={p.stripe_payment_intent_id} mono />
          )}
          {p.stripe_checkout_session_id && (
            <Row label="Checkout session" value={p.stripe_checkout_session_id} mono />
          )}
          {p.receipt_url && (
            <a
              href={p.receipt_url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-secondary hover:underline"
            >
              Receipt
            </a>
          )}
        </div>
      ))}
      {!detail.payments.length && <p className="text-sm text-muted">No payments recorded</p>}
    </div>
  );
}

export function InvoicesTab({ detail }: { detail: OrderDetail }) {
  if (!detail.invoice_number) return <p className="text-sm text-muted">No invoice generated</p>;
  return (
    <>
      <Row label="Invoice #" value={detail.invoice_number} mono />
      <Row
        label="Amount"
        value={detail.invoice_amount_cents ? formatCents(detail.invoice_amount_cents) : "—"}
      />
      <div className="mt-3">
        <OrderMoneyDownloads detail={detail} />
      </div>
    </>
  );
}

export function MoneySection({ detail }: { detail: OrderDetail }) {
  return (
    <div className="space-y-8">
      <SectionBlock title="Pricing">
        <QuoteLines
          breakdown={detail.pricing_breakdown}
          quotedCents={detail.quote_amount_cents}
          chargedCents={detail.amount_cents}
          currency={(detail.currency || "cad").toUpperCase()}
        />
      </SectionBlock>
      <SectionBlock title="Payments">
        <PaymentsTab detail={detail} />
      </SectionBlock>
      <SectionBlock title="Invoices">
        <InvoicesTab detail={detail} />
      </SectionBlock>
    </div>
  );
}
