"use client";

import Button from "@/components/ui/Button";
import { OrderStateBadge } from "@/components/orders/OrderStateBadge";
import { ordersApi, RETURNABLE_STATES, type OrderReturn } from "@/lib/orders";
import { formatCents } from "@/lib/utils";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

type Props = {
  orderId: string;
  state: string;
  canWrite: boolean;
  getApiToken?: () => Promise<string>;
  orgId?: string;
};

const NOTE_COPY: Record<string, string> = {
  contract_return_rules_not_modelled:
    "Priced at your standard rate. Contract return terms are applied on the invoice by PorterChain.",
};

/** Return pickups for this order: book one, see each return's status. */
export function ReturnsCard({ orderId, state, canWrite, getApiToken, orgId }: Props) {
  const [rows, setRows] = useState<OrderReturn[]>([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getApiToken) return;
    const token = await getApiToken();
    const out = await ordersApi.returns(token, orderId, orgId);
    setRows(out.returns ?? []);
  }, [getApiToken, orderId, orgId]);

  useEffect(() => {
    void load().catch(() => setRows([]));
  }, [load]);

  const returnable = RETURNABLE_STATES.includes(state);
  if (!returnable && rows.length === 0) return null;

  async function bookReturn() {
    if (!getApiToken) return;
    if (
      !window.confirm(
        "Book a return pickup? A driver collects from the delivery address and brings it back to your pickup address."
      )
    )
      return;
    setBusy(true);
    setNote(null);
    try {
      const token = await getApiToken();
      await ordersApi.createReturn(token, orderId, orgId);
      setNote("Return pickup booked.");
      await load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not book this return.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-2xl border border-primary/10 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-primary">Returns</h3>
        {canWrite && returnable ? (
          <Button size="sm" variant="outline" onClick={() => void bookReturn()} disabled={busy}>
            {busy ? "Booking…" : "Book return pickup"}
          </Button>
        ) : null}
      </div>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-muted">
          No returns yet. A return is a pickup from the customer back to you, priced like a normal
          delivery.
        </p>
      ) : (
        <ul className="mt-3 space-y-2 text-sm">
          {rows.map((row) => (
            <li
              key={row.order_id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-primary/10 px-3 py-2"
            >
              <Link href={`/orders/${row.order_id}`} className="font-medium text-secondary">
                {row.tracking_number ?? row.order_id}
              </Link>
              <span className="text-muted">
                {row.source === "shopify" ? "From Shopify" : "Booked here"}
                {row.price_cents != null ? ` · ${formatCents(row.price_cents)}` : ""}
              </span>
              <OrderStateBadge state={row.state} />
              {row.pricing_note && NOTE_COPY[row.pricing_note] ? (
                <p className="w-full text-xs text-muted">{NOTE_COPY[row.pricing_note]}</p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
      {note ? <p className="mt-2 text-sm text-muted">{note}</p> : null}
    </section>
  );
}
