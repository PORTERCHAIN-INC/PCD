"use client";

import { PageSkeleton } from "@porterchain/ui/loading";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { formatPrice } from "@porterchain/types/booking";
import CustomerShell from "@/components/CustomerShell";
import PortalAuth, { type PortalAuthValue } from "@/components/auth/PortalAuth";
import {
  PROBLEM_LABELS,
  STATE_LABEL,
  accountApi,
  type MyDeliveries,
  type MyDelivery,
  type ProblemKind,
} from "@/lib/account";

export default function OrdersClient() {
  return (
    <CustomerShell>{<PortalAuth>{(auth) => <OrdersBody auth={auth} />}</PortalAuth>}</CustomerShell>
  );
}

/** Orders: numbers first, then one card per delivery with one primary action each. */
function OrdersBody({ auth }: { auth: PortalAuthValue }) {
  const booked = useSearchParams().get("booked");
  const [data, setData] = useState<MyDeliveries | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.ready) return;
    void (async () => {
      const token = await auth.getToken();
      if (!token) return;
      accountApi
        .deliveries(token)
        .then(setData)
        .catch((e: Error) => setError(e.message));
    })();
  }, [auth]);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[13px] font-semibold uppercase tracking-[0.18em] text-primary/65">
            Orders
          </p>
          <h1 className="mt-2 text-4xl font-extrabold tracking-tight text-primary">
            Your deliveries
          </h1>
        </div>
        <Link
          href="/send"
          className="hidden rounded-2xl bg-primary px-5 py-3 text-sm font-bold text-white md:inline-flex"
        >
          Send
        </Link>
      </div>

      {booked ? (
        <p
          role="status"
          className="mt-6 rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-900"
        >
          Booked {booked}. Tracking link and receipt are in your email.
        </p>
      ) : null}
      {error ? (
        <p
          role="alert"
          className="mt-6 rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800"
        >
          {error}
        </p>
      ) : null}

      {data ? (
        <>
          <dl className="mt-8 grid grid-cols-3 gap-3" data-testid="orders-numbers">
            {[
              ["Active", String(data.summary.active)],
              ["Deliveries", String(data.summary.orders)],
              ["Spent", formatPrice(data.summary.spent_cents)],
            ].map(([k, v]) => (
              <div key={k} className="rounded-3xl border border-primary/10 bg-white p-4">
                <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/65">
                  {k}
                </dt>
                <dd className="mt-1 text-2xl font-extrabold tabular-nums text-primary sm:text-3xl">
                  {v}
                </dd>
              </div>
            ))}
          </dl>
          {data.orders.length === 0 ? (
            <div className="mt-10 rounded-3xl border border-primary/10 bg-white p-8 text-center">
              <p className="text-lg font-bold text-primary">No deliveries yet.</p>
              <Link
                href="/send"
                className="mt-4 inline-flex rounded-2xl bg-primary px-6 py-3 font-bold text-white"
              >
                Send something
              </Link>
            </div>
          ) : (
            <ul className="mt-6 space-y-3">
              {data.orders.map((o) => (
                <OrderCard key={o.tracking_number} order={o} auth={auth} />
              ))}
            </ul>
          )}
        </>
      ) : !error ? (
        <div className="mt-8">
          <PageSkeleton rows={3} />
        </div>
      ) : null}
    </div>
  );
}

function OrderCard({ order, auth }: { order: MyDelivery; auth: PortalAuthValue }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<ProblemKind | null>(null);
  const [details, setDetails] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const label = STATE_LABEL[order.state] ?? order.state.replace(/_/g, " ").toLowerCase();
  const date = order.created_at
    ? new Date(order.created_at).toLocaleDateString("en-CA", { month: "short", day: "numeric" })
    : "";

  async function send() {
    if (!kind) return;
    setBusy(true);
    try {
      const token = await auth.getToken();
      const r = await accountApi.reportProblem(token ?? "", order.tracking_number, kind, details);
      setSent(`Sent. A person replies by email within ${r.reply_within_hours} hours.`);
      setOpen(false);
    } catch (e) {
      setSent((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="rounded-3xl border border-primary/10 bg-white p-5" data-testid="order-card">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p
            className={`text-xs font-bold uppercase tracking-[0.14em] ${order.active ? "text-secondary" : "text-primary/65"}`}
          >
            {label} · {date}
          </p>
          <p className="mt-1 truncate text-base font-bold text-primary">
            {order.dropoff ?? order.tracking_number}
          </p>
          <p className="truncate text-sm text-primary/70">
            from {order.pickup ?? "—"}
            {order.extra_drops ? ` · +${order.extra_drops} drops` : ""}
          </p>
        </div>
        <p className="shrink-0 text-xl font-extrabold tabular-nums text-primary">
          {formatPrice(order.amount_cents)}
        </p>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {order.active ? (
          <a
            href={order.track_url}
            className="rounded-2xl bg-primary px-5 py-2.5 text-sm font-bold text-white"
          >
            Track
          </a>
        ) : order.send_again_url ? (
          <a
            href={order.send_again_url}
            className="rounded-2xl bg-primary px-5 py-2.5 text-sm font-bold text-white"
          >
            Send again
          </a>
        ) : null}
        {!order.active ? (
          <a
            href={order.track_url}
            className="rounded-2xl border border-primary/15 px-4 py-2.5 text-sm font-semibold text-primary"
          >
            Details
          </a>
        ) : null}
        {order.receipt_url ? (
          <a
            href={order.receipt_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-2xl border border-primary/15 px-4 py-2.5 text-sm font-semibold text-primary"
          >
            Receipt
          </a>
        ) : null}
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="ml-auto text-sm font-semibold text-primary/75 underline underline-offset-4"
        >
          Report a problem
        </button>
      </div>
      {sent ? <p className="mt-3 text-sm font-medium text-primary">{sent}</p> : null}
      {open ? (
        <div className="mt-4 border-t border-primary/10 pt-4">
          <div className="flex flex-wrap gap-2">
            {(Object.keys(PROBLEM_LABELS) as ProblemKind[]).map((k) => (
              <button
                key={k}
                type="button"
                aria-pressed={kind === k}
                onClick={() => setKind(k)}
                className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${
                  kind === k
                    ? "border-primary bg-primary text-white"
                    : "border-primary/15 text-primary"
                }`}
              >
                {PROBLEM_LABELS[k]}
              </button>
            ))}
          </div>
          <textarea
            value={details}
            onChange={(e) => setDetails(e.target.value)}
            rows={2}
            maxLength={2000}
            placeholder="Details (optional)"
            className="mt-3 block w-full rounded-2xl border border-primary/15 px-4 py-3 text-sm text-primary outline-none focus:border-primary"
          />
          <button
            type="button"
            disabled={!kind || busy}
            onClick={() => void send()}
            className="mt-3 rounded-2xl bg-primary px-5 py-2.5 text-sm font-bold text-white disabled:opacity-50"
          >
            Send to support
          </button>
        </div>
      ) : null}
    </li>
  );
}
