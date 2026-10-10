"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { Badge, Button, SectionCard } from "@/components/crm/primitives";
import { money, shortDate } from "@/lib/crmFormat";
import {
  customer360Api,
  type BookingLinkDraft,
  type Customer360,
  type PrivacyJob,
} from "@/lib/customers";

const input =
  "w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm text-primary outline-none focus:border-primary";

export function use360(id: string, version: number) {
  return useApiData((t) => customer360Api.overview(t, id), [id, version], {
    key: `customer-360-${id}-${version}`,
  });
}

/** Numbers first: five figures that answer "who is this customer to us?" */
export function KpiStrip({ c }: { c: Customer360 }) {
  const n = c.numbers;
  const cells: Array<[string, string, string?]> = [
    ["Lifetime value", money(n.lifetime_value_cents)],
    ["Orders", String(n.orders), n.orders ? `avg ${money(n.avg_order_cents)}` : undefined],
    [
      "Rating",
      n.avg_rating != null ? `${n.avg_rating.toFixed(1)}★` : "—",
      n.low_ratings ? `${n.low_ratings} low` : undefined,
    ],
    ["Credit", money(n.credit_balance_cents)],
    [
      "Last order",
      c.churn.days_since_last != null ? `${Math.round(c.churn.days_since_last)}d` : "—",
      c.churn.usual_interval_days ? `usual ${Math.round(c.churn.usual_interval_days)}d` : undefined,
    ],
  ];
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="customer-kpis">
      {cells.map(([k, v, sub]) => (
        <div key={k} className="rounded-2xl border border-primary/10 bg-white p-4">
          <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/65">
            {k}
          </dt>
          <dd className="mt-1 text-2xl font-extrabold tabular-nums text-primary">{v}</dd>
          {sub ? <dd className="text-xs text-primary/65">{sub}</dd> : null}
        </div>
      ))}
    </dl>
  );
}

export function SignalBadges({ c }: { c: Customer360 }) {
  return (
    <>
      {c.churn.flag ? <Badge tone="amber">Churn risk</Badge> : null}
      {c.risk.length ? <Badge tone="red">Risk review</Badge> : null}
      {c.consent.bounced ? <Badge tone="red">Email bounced</Badge> : null}
      {c.consent.suppressed ? <Badge tone="slate">Do not contact</Badge> : null}
      <Badge tone="slate">{c.account}</Badge>
    </>
  );
}

export function SignalsCard({ c }: { c: Customer360 }) {
  return (
    <SectionCard title="Signals (rules)">
      <ul className="divide-y divide-primary/5 text-sm">
        <li className="flex justify-between gap-4 px-5 py-3">
          <span className="text-primary/75">Churn</span>
          <span className="text-right font-semibold text-primary">
            {c.churn.flag ? "At risk" : c.churn.status === "no_orders" ? "No orders" : "Active"}
            {c.churn.rule ? (
              <span className="block text-xs font-normal text-primary/65">{c.churn.rule}</span>
            ) : null}
          </span>
        </li>
        <li className="flex justify-between gap-4 px-5 py-3">
          <span className="text-primary/75">Risk</span>
          <span className="text-right font-semibold text-primary">
            {c.risk.length
              ? c.risk
                  .map((r) => `${r.tracking_number}: ${r.reasons.join(", ").replace(/_/g, " ")}`)
                  .join(" · ")
              : "None"}
          </span>
        </li>
        <li className="flex justify-between gap-4 px-5 py-3">
          <span className="text-primary/75">Email</span>
          <span className="text-right font-semibold text-primary">
            {c.consent.deliverable ? "Deliverable" : c.consent.bounced ? "Bounced" : "Suppressed"}
          </span>
        </li>
      </ul>
    </SectionCard>
  );
}

/** Drafted, never sent: staff copy it into their own mail. */
export function BookingLinkButton({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [draft, setDraft] = useState<BookingLinkDraft | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function open() {
    setError(null);
    try {
      setDraft(await customer360Api.bookingLinkDraft(await getApiToken(), id));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <>
      <Button variant="outline" onClick={() => void open()}>
        Booking link
      </Button>
      {error ? <span className="text-sm text-red-700">{error}</span> : null}
      {draft ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Booking link draft"
          className="fixed inset-0 z-50 flex items-end justify-center bg-primary/40 p-4 sm:items-center"
        >
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/65">
              Draft · not sent
            </p>
            <p className="mt-2 text-sm text-primary/75">To {draft.to}</p>
            <p className="mt-1 font-bold text-primary">{draft.subject}</p>
            <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-2xl bg-gray-bg p-4 text-sm text-primary">
              {draft.body}
            </pre>
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <Button variant="outline" onClick={() => setDraft(null)}>
                Close
              </Button>
              <Button
                onClick={() => {
                  void navigator.clipboard?.writeText(`${draft.subject}\n\n${draft.body}`);
                  setCopied(true);
                }}
              >
                {copied ? "Copied" : "Copy email"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export function MoneyActions({ id, onDone }: { id: string; onDone: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [credit, setCredit] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [tracking, setTracking] = useState("");
  const [refund, setRefund] = useState("");
  const [refundReason, setRefundReason] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(fn: (t: string) => Promise<string>) {
    setBusy(true);
    setMsg(null);
    try {
      setMsg(await fn(await getApiToken()));
      onDone();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <SectionCard title="Account credit">
        <form
          className="space-y-2 p-5"
          onSubmit={(e) => {
            e.preventDefault();
            void run(async (t) => {
              const r = await customer360Api.credit(
                t,
                id,
                Math.round(Number(credit) * 100),
                creditReason
              );
              setCredit("");
              setCreditReason("");
              return `Credit balance ${money(r.balance_cents)}.`;
            });
          }}
        >
          <input
            className={input}
            inputMode="decimal"
            placeholder="Amount in $ (negative to use credit)"
            value={credit}
            onChange={(e) => setCredit(e.target.value)}
            aria-label="Credit amount"
          />
          <input
            className={input}
            placeholder="Reason (shown in timeline)"
            value={creditReason}
            onChange={(e) => setCreditReason(e.target.value)}
            aria-label="Credit reason"
          />
          <Button type="submit" disabled={busy || !Number(credit) || creditReason.length < 3}>
            Add credit
          </Button>
        </form>
      </SectionCard>
      <SectionCard title="Refund an order">
        <form
          className="space-y-2 p-5"
          onSubmit={(e) => {
            e.preventDefault();
            void run(async (t) => {
              const r = await customer360Api.refund(
                t,
                id,
                tracking.trim(),
                refund ? Math.round(Number(refund) * 100) : null,
                refundReason
              );
              return `Refund ${r.refund.status.replace("_", " ")} · ${money(r.refund.amount_cents)}.`;
            });
          }}
        >
          <input
            className={input}
            placeholder="Tracking number"
            value={tracking}
            onChange={(e) => setTracking(e.target.value)}
            aria-label="Tracking number"
          />
          <input
            className={input}
            inputMode="decimal"
            placeholder="Amount in $ (blank = rest of order)"
            value={refund}
            onChange={(e) => setRefund(e.target.value)}
            aria-label="Refund amount"
          />
          <input
            className={input}
            placeholder="Reason"
            value={refundReason}
            onChange={(e) => setRefundReason(e.target.value)}
            aria-label="Refund reason"
          />
          <Button type="submit" disabled={busy || tracking.length < 3 || refundReason.length < 3}>
            Refund
          </Button>
        </form>
      </SectionCard>
      {msg ? (
        <p role="status" className="text-sm font-medium text-primary lg:col-span-2">
          {msg}
        </p>
      ) : null}
    </div>
  );
}

export function NotesAndTimeline({ id }: { id: string }) {
  const { getApiToken } = useAdminAuth();
  const [v, setV] = useState(0);
  const [note, setNote] = useState("");
  const { data } = useApiData((t) => customer360Api.timeline(t, id), [id, v], {
    key: `customer-timeline-${id}-${v}`,
  });
  return (
    <SectionCard title="Notes & timeline">
      <form
        className="flex gap-2 border-b border-primary/5 p-5"
        onSubmit={(e) => {
          e.preventDefault();
          void (async () => {
            await customer360Api.addNote(await getApiToken(), id, note);
            setNote("");
            setV((x) => x + 1);
          })();
        }}
      >
        <input
          className={input}
          placeholder="Add a note for the team"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          aria-label="Note"
        />
        <Button type="submit" disabled={note.trim().length < 2}>
          Add
        </Button>
      </form>
      <ol className="divide-y divide-primary/5" data-testid="customer-timeline">
        {(data ?? []).map((i) => (
          <li key={`${i.kind}-${i.ref}-${i.at}`} className="flex gap-4 px-5 py-3">
            <span className="w-20 shrink-0 text-xs text-primary/65">
              {i.at ? shortDate(i.at) : ""}
            </span>
            <span className="min-w-0">
              <span className="text-sm font-semibold text-primary">{i.title}</span>
              {i.detail ? (
                <span className="block truncate text-xs text-primary/70">{i.detail}</span>
              ) : null}
            </span>
            <span className="ml-auto shrink-0 text-[11px] font-semibold uppercase tracking-wide text-primary/55">
              {i.kind}
            </span>
          </li>
        ))}
        {data && data.length === 0 ? (
          <li className="px-5 py-3 text-sm text-primary/70">Nothing yet.</li>
        ) : null}
      </ol>
    </SectionCard>
  );
}

export function PrivacyPanel({ c, onDone }: { c: Customer360; onDone: () => void }) {
  return (
    <div className="space-y-4">
      <SectionCard title="Consent & deliverability">
        <ul className="divide-y divide-primary/5 text-sm">
          {(["marketing", "reorder"] as const).map((k) => (
            <li key={k} className="flex justify-between gap-4 px-5 py-3">
              <span className="font-semibold capitalize text-primary">
                {k === "reorder" ? "Send-again emails" : "Marketing"}
              </span>
              <span className="text-right text-primary">
                {c.consent[k].granted ? "On" : "Off"} · {c.consent[k].basis}
                {c.consent[k].at ? (
                  <span className="block text-xs text-primary/65">
                    {shortDate(c.consent[k].at!)} · {c.consent[k].source}
                  </span>
                ) : null}
              </span>
            </li>
          ))}
          <li className="flex justify-between gap-4 px-5 py-3">
            <span className="font-semibold text-primary">Bounce</span>
            <span className="text-primary">{c.consent.bounced ? "Bounced" : "No bounces"}</span>
          </li>
          <li className="flex justify-between gap-4 px-5 py-3">
            <span className="font-semibold text-primary">Do-not-contact list</span>
            <span className="text-primary">{c.consent.suppressed ? "Listed" : "Not listed"}</span>
          </li>
        </ul>
      </SectionCard>
      {c.privacy.jobs.length === 0 ? (
        <SectionCard title="Deletion requests">
          <p className="p-5 text-sm text-primary/70">
            None. Requests from the customer appear here with an automatic plan.
          </p>
        </SectionCard>
      ) : (
        c.privacy.jobs.map((j) => <DeletionJobCard key={j.id} job={j} onDone={onDone} />)
      )}
    </div>
  );
}

export function DeletionJobCard({ job, onDone }: { job: PrivacyJob; onDone: () => void }) {
  const { getApiToken } = useAdminAuth();
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const blockers = job.plan.blockers?.active_deliveries ?? [];
  async function decide(approve: boolean) {
    setBusy(true);
    setError(null);
    try {
      const t = await getApiToken();
      await (approve
        ? customer360Api.approveJob(t, job.id, note)
        : customer360Api.rejectJob(t, job.id, note));
      onDone();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <SectionCard title={`Deletion ${job.reference}`}>
      <div className="space-y-3 p-5 text-sm text-primary" data-testid="deletion-job">
        <p>
          <Badge
            tone={
              job.status === "executed" ? "green" : job.status === "rejected" ? "slate" : "amber"
            }
          >
            {job.status.replace("_", " ")}
          </Badge>{" "}
          {job.due_at ? <span className="text-primary/70">Due {shortDate(job.due_at)}</span> : null}
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/65">
              Erase
            </p>
            <ul className="mt-1 space-y-0.5">
              {Object.entries(job.plan.erase).map(([k, v]) => (
                <li key={k}>
                  {k.replace(/_/g, " ")}: <b>{Array.isArray(v) ? v.join(", ") : String(v)}</b>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary/65">
              Keep
            </p>
            <p className="mt-1 text-primary/80">{String(job.plan.keep.why ?? "")}</p>
          </div>
        </div>
        {blockers.length ? (
          <p className="font-semibold text-amber-800">
            Waits for active deliveries: {blockers.join(", ")}
          </p>
        ) : null}
        {job.status === "pending_review" ? (
          <>
            <input
              className={input}
              placeholder="Review note (required to reject)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              aria-label="Review note"
            />
            <div className="flex gap-2">
              <Button onClick={() => void decide(true)} disabled={busy || blockers.length > 0}>
                Approve & erase
              </Button>
              <Button
                variant="outline"
                onClick={() => void decide(false)}
                disabled={busy || note.trim().length < 5}
              >
                Reject
              </Button>
            </div>
          </>
        ) : (
          <p className="text-primary/75">
            {job.reviewer ? `Reviewed by ${job.reviewer}` : ""}
            {job.result
              ? ` · ${Object.entries(job.result)
                  .map(([k, v]) => `${k.replace(/_/g, " ")} ${v}`)
                  .join(" · ")}`
              : ""}
          </p>
        )}
        {error ? (
          <p role="alert" className="text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </SectionCard>
  );
}
