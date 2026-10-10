"use client";

import { useShowMore } from "@/components/layout/ShowMore";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn, formatCents } from "@porterchain/ui/utils";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { financeOpsApi, type CashBoard, type ReminderDraft } from "@/lib/finance-ops";
import { withStaffStepUp } from "@/lib/staff-step-up";
import {
  Empty,
  FinanceShell,
  Hero,
  PrimaryButton,
  QuietButton,
  Section,
  Stat,
} from "./FinanceShell";

const FinanceInteracPanel = dynamic(() => import("@/components/finance/FinanceInteracPanel"), {
  ssr: false,
  loading: () => <PageSkeleton rows={3} />,
});

const BUCKET_TONE = [
  "bg-secondary/25",
  "bg-secondary/55",
  "bg-amber-500",
  "bg-orange-600",
  "bg-red-700",
];

function AgingBar({ board }: { board: CashBoard }) {
  const total = Math.max(1, board.owed_cents);
  return (
    <div>
      <div
        className="flex h-3 w-full overflow-hidden rounded-full bg-primary/5"
        role="img"
        aria-label="AR by age"
      >
        {board.bucket_order.map((b, i) => (
          <div
            key={b}
            className={BUCKET_TONE[i]}
            style={{ width: `${(board.buckets[b] / total) * 100}%` }}
          />
        ))}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
        {board.bucket_order.map((b, i) => (
          <div key={b}>
            <dt className="flex items-center gap-1.5 text-xs font-semibold text-muted">
              <span className={cn("h-2 w-2 rounded-full", BUCKET_TONE[i])} aria-hidden />
              {b}
            </dt>
            <dd className="mt-0.5 text-lg font-bold tabular-nums text-primary">
              {formatCents(board.buckets[b])}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function daysTone(days: number) {
  if (days > 60) return "bg-red-50 text-red-800";
  if (days > 30) return "bg-orange-50 text-orange-800";
  if (days > 0) return "bg-amber-50 text-amber-900";
  return "bg-emerald-50 text-emerald-800";
}

function MerchantRows({ board, holds }: { board: CashBoard; holds: Set<string> }) {
  const [all, setAll] = useState(false);
  if (!board.merchants.length) return <Empty>Every merchant is paid up.</Empty>;
  const rows = all ? board.merchants : board.merchants.slice(0, 10);
  return (
    <>
      <ul className="divide-y divide-primary/10">
        {rows.map((m) => (
          <li key={m.merchant_id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
            <div className="min-w-0 flex-1">
              <Link
                href={`/merchants/${m.merchant_id}`}
                className="font-semibold text-primary hover:text-secondary hover:underline"
              >
                {m.merchant_name}
              </Link>
              <p className="truncate text-xs text-muted">
                {m.invoice_count} invoice{m.invoice_count === 1 ? "" : "s"}
                {m.references.length ? ` · ${m.references.slice(0, 3).join(", ")}` : ""}
                {m.ap_contact?.email ? ` · ${m.ap_contact.email}` : ""}
              </p>
            </div>
            {holds.has(m.merchant_id) ? (
              <span className="rounded-full bg-red-700 px-2.5 py-1 text-xs font-semibold text-white">
                On hold
              </span>
            ) : null}
            <span
              className={cn(
                "rounded-full px-2.5 py-1 text-xs font-semibold",
                daysTone(m.oldest_days)
              )}
            >
              {m.oldest_days > 0 ? `${m.oldest_days} days late` : "Not due"}
            </span>
            <span className="w-28 text-right text-lg font-bold tabular-nums text-primary">
              {formatCents(m.outstanding_cents)}
            </span>
          </li>
        ))}
      </ul>
      {board.merchants.length > 10 ? (
        <button
          type="button"
          onClick={() => setAll((v) => !v)}
          className="mt-2 min-h-10 text-sm font-semibold text-secondary hover:underline"
        >
          {all ? "Show the oldest 10" : `Show all ${board.merchants.length} merchants`}
        </button>
      ) : null}
    </>
  );
}

function Drafts({
  drafts,
  selected,
  toggle,
}: {
  drafts: ReminderDraft[];
  selected: Set<string>;
  toggle: (id: string) => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const [all, setAll] = useState(false);
  if (!drafts.length)
    return <Empty>No reminders waiting. Drafts are queued daily for late invoices.</Empty>;
  return (
    <>
      <ul className="divide-y divide-primary/10">
        {(all ? drafts : drafts.slice(0, 6)).map((d) => (
          <li key={d.id} className="py-3">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 h-5 w-5 accent-[var(--secondary)]"
                checked={selected.has(d.id)}
                onChange={() => toggle(d.id)}
                aria-label={`Select reminder for ${d.merchant_name ?? "merchant"}`}
              />
              <div className="min-w-0 flex-1">
                <p className="font-semibold text-primary">{d.merchant_name ?? "Merchant"}</p>
                <p className="truncate text-xs text-muted">
                  To {d.to_email ?? "no billing email"} · {d.invoice_count} invoice
                  {d.invoice_count === 1 ? "" : "s"} · {d.oldest_days} days late
                </p>
                <button
                  type="button"
                  className="mt-1 text-xs font-semibold text-secondary hover:underline"
                  onClick={() => setOpen(open === d.id ? null : d.id)}
                  aria-expanded={open === d.id}
                >
                  {open === d.id ? "Hide email" : "Preview email"}
                </button>
                {open === d.id ? (
                  <div className="mt-2 rounded-2xl bg-primary/[0.03] p-3 text-sm">
                    <p className="font-semibold text-primary">{d.subject}</p>
                    <pre className="mt-2 whitespace-pre-wrap font-sans text-xs leading-relaxed text-primary/80">
                      {d.body}
                    </pre>
                  </div>
                ) : null}
              </div>
              <span className="shrink-0 text-right font-bold tabular-nums text-primary">
                {formatCents(d.amount_cents)}
              </span>
            </div>
          </li>
        ))}
      </ul>
      {drafts.length > 6 ? (
        <button
          type="button"
          onClick={() => setAll((v) => !v)}
          className="mt-2 min-h-10 text-sm font-semibold text-secondary hover:underline"
        >
          {all ? "Show fewer" : `Show all ${drafts.length} drafts`}
        </button>
      ) : null}
    </>
  );
}

export default function CashClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);

  const board = useQuery({
    queryKey: ["finance-cash"],
    enabled,
    queryFn: async () => financeOpsApi.cash(await getApiToken()),
  });
  const drafts = useQuery({
    queryKey: ["finance-reminders"],
    enabled,
    queryFn: async () => (await financeOpsApi.reminders(await getApiToken())).items,
  });
  const draftRows = useMemo(() => drafts.data ?? [], [drafts.data]);
  const holdIds = useMemo(
    () =>
      new Set(
        (board.data?.credit_holds.items ?? []).filter((h) => h.blocked).map((h) => h.merchant_id)
      ),
    [board.data]
  );

  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["finance-cash"] });
    void qc.invalidateQueries({ queryKey: ["finance-reminders"] });
  };

  const queue = useMutation({
    mutationFn: async () => financeOpsApi.queueReminders(await getApiToken()),
    onSuccess: (r) => {
      setNotice(
        r.created || r.updated
          ? `${r.created} new, ${r.updated} refreshed. Nothing sent.`
          : "No late invoices need a reminder."
      );
      refresh();
    },
  });
  const approve = useMutation({
    mutationFn: async (ids: string[]) => {
      const token = await getApiToken();
      return withStaffStepUp(token, () => financeOpsApi.approveReminders(token, ids));
    },
    onSuccess: (r) => {
      setSelected(new Set());
      setNotice(
        `${r.emails_sent} email${r.emails_sent === 1 ? "" : "s"} sent.${r.errors.length ? ` ${r.errors.length} skipped.` : ""}`
      );
      refresh();
    },
  });
  const discard = useMutation({
    mutationFn: async (ids: string[]) => financeOpsApi.discardReminders(await getApiToken(), ids),
    onSuccess: () => {
      setSelected(new Set());
      refresh();
    },
  });

  const chosen = selected.size ? [...selected] : draftRows.map((d) => d.id);
  const primary = draftRows.length ? (
    <PrimaryButton
      disabled={approve.isPending}
      onClick={() => {
        if (
          window.confirm(
            `Send ${chosen.length} reminder email${chosen.length === 1 ? "" : "s"} now?`
          )
        )
          approve.mutate(chosen);
      }}
    >
      {approve.isPending
        ? "Sending…"
        : `Approve & send ${chosen.length} reminder${chosen.length === 1 ? "" : "s"}`}
    </PrimaryButton>
  ) : (
    <PrimaryButton disabled={queue.isPending} onClick={() => queue.mutate()}>
      {queue.isPending ? "Queuing…" : "Queue reminder drafts"}
    </PrimaryButton>
  );

  const b = board.data;
  const holdPage = useShowMore(b?.credit_holds.items ?? [], 10);
  return (
    <FinanceShell
      title="Cash"
      subtitle="Who owes us, how late, and what is waiting for you."
      primary={primary}
    >
      {notice ? (
        <p
          role="status"
          className="rounded-2xl bg-secondary/10 px-4 py-3 text-sm font-medium text-primary"
        >
          {notice}
        </p>
      ) : null}
      {!b ? (
        <PageSkeleton rows={4} />
      ) : (
        <>
          <Hero label="Merchants owe" value={formatCents(b.owed_cents)}>
            <div className="grid grid-cols-2 gap-6 border-t border-primary/10 pt-5 sm:grid-cols-4">
              <Stat
                label="Past due"
                value={formatCents(b.overdue_cents)}
                tone={b.overdue_cents ? "bad" : "good"}
              />
              <Stat label="Merchants" value={String(b.merchant_count)} />
              <Stat label="e-Transfers to match" value={String(b.interac_open_count)} />
              <Stat label="Credit we hold" value={formatCents(b.merchant_credit_cents)} />
            </div>
          </Hero>

          <Section title="AR by age">
            <AgingBar board={b} />
          </Section>

          <Section
            title="By merchant"
            aside={<span className="text-sm text-muted">Oldest first</span>}
          >
            <MerchantRows board={b} holds={holdIds} />
          </Section>
        </>
      )}

      <Section
        title={`Reminder drafts${draftRows.length ? ` · ${draftRows.length}` : ""}`}
        aside={
          draftRows.length ? (
            <div className="flex gap-1">
              <QuietButton
                onClick={() =>
                  setSelected(
                    selected.size === draftRows.length
                      ? new Set()
                      : new Set(draftRows.map((d) => d.id))
                  )
                }
              >
                {selected.size === draftRows.length ? "Clear" : "Select all"}
              </QuietButton>
              <QuietButton
                disabled={!selected.size || discard.isPending}
                onClick={() => discard.mutate([...selected])}
              >
                Discard
              </QuietButton>
              <QuietButton disabled={queue.isPending} onClick={() => queue.mutate()}>
                Refresh drafts
              </QuietButton>
            </div>
          ) : null
        }
      >
        <Drafts
          drafts={draftRows}
          selected={selected}
          toggle={(id) =>
            setSelected((s) => {
              const n = new Set(s);
              if (n.has(id)) n.delete(id);
              else n.add(id);
              return n;
            })
          }
        />
      </Section>

      <section className="space-y-3">
        <h2 className="text-lg font-bold text-primary">e-Transfers to match</h2>
        <FinanceInteracPanel />
      </section>

      <Section title="Credit holds">
        {!b ? null : !b.credit_holds.available ? (
          <Empty>
            Credit holds arrive with the merchant-admin release. This view reads them; it does not
            set them.
          </Empty>
        ) : b.credit_holds.items.length === 0 ? (
          <Empty>No merchant is on hold.</Empty>
        ) : (
          <ul className="divide-y divide-primary/10">
            {holdPage.visible.map((h) => (
              <li
                key={h.merchant_id}
                className="flex flex-wrap items-center justify-between gap-2 py-3"
              >
                <Link
                  href={`/merchants/${h.merchant_id}`}
                  className="font-semibold text-primary hover:underline"
                >
                  {h.merchant_name}
                </Link>
                <span className="text-sm text-muted">
                  {(h.reasons ?? []).join(" · ") || "Hold"}
                </span>
              </li>
            ))}
            {holdPage.more}
          </ul>
        )}
      </Section>
    </FinanceShell>
  );
}
