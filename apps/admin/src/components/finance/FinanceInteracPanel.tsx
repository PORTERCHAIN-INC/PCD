"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Inbox, RefreshCw, ShieldAlert } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { TableSkeleton } from "@porterchain/ui/loading";
import { Button, EmptyState } from "@/components/crm/primitives";
import { financeApi, type InteracTransfer } from "@/lib/finance";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { withStaffStepUp } from "@/lib/staff-step-up";

const VIEWS = [
  { id: "open", label: "To review" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
] as const;

const NOTE_LABEL: Record<string, string> = {
  exact: "Exact amount",
  partial: "Short-paid",
  over: "Overpaid → credit",
  unmatched: "No invoice found",
  ambiguous: "Several invoices match",
  ambiguous_sender: "Several merchants match",
  merchant_only: "Merchant known, amount differs",
  settled: "Invoice already paid",
};

/**
 * Interac e-Transfers read from the billing inbox. Nothing is applied until a person
 * presses Approve; every decision is audited. One screen, one action per row.
 */
export default function FinanceInteracPanel() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const isReady = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const qc = useQueryClient();
  const [view, setView] = useState<(typeof VIEWS)[number]["id"]>("open");
  const [pick, setPick] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["finance-interac", view],
    enabled: isReady,
    queryFn: async () => financeApi.interacQueue(await getApiToken(), view),
  });

  const invalidate = async () => {
    await qc.invalidateQueries({ queryKey: ["finance-interac"] });
    await qc.invalidateQueries({ queryKey: ["finance-invoices"] });
    await qc.invalidateQueries({ queryKey: ["finance-collections"] });
    await qc.invalidateQueries({ queryKey: ["finance-dashboard"] });
  };

  const approve = useMutation({
    mutationFn: async (t: InteracTransfer) => {
      const token = await getApiToken();
      const invoiceId = pick[t.id]?.trim() || undefined;
      return withStaffStepUp(token, () =>
        financeApi.interacApprove(token, t.id, invoiceId ? { invoice_id: invoiceId } : {})
      );
    },
    onSuccess: async (row) => {
      setMsg(`Applied ${formatCents(row.amount_cents)} to ${row.invoice_number ?? "invoice"}.`);
      await invalidate();
    },
    onError: (e: Error) => setMsg(e.message || "Approve failed"),
  });

  const reject = useMutation({
    mutationFn: async (t: InteracTransfer) => {
      const token = await getApiToken();
      return withStaffStepUp(token, () =>
        financeApi.interacReject(token, t.id, "Not ours / not a payment")
      );
    },
    onSuccess: async () => {
      setMsg("Dismissed.");
      await invalidate();
    },
    onError: (e: Error) => setMsg(e.message || "Reject failed"),
  });

  const sync = useMutation({
    mutationFn: async () => financeApi.interacSync(await getApiToken()),
    onSuccess: async (r) => {
      setMsg(
        r.enabled
          ? `Inbox checked: ${r.queued} new.`
          : "Inbox reader is off (INTERAC_IMAP_ENABLED)."
      );
      await invalidate();
    },
    onError: (e: Error) => setMsg(e.message || "Inbox check failed"),
  });

  const items = data?.items ?? [];
  const waitingCents =
    view === "open"
      ? items.reduce((s, t) => s + (t.status === "suspicious" ? 0 : t.amount_cents), 0)
      : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 rounded-2xl bg-primary p-5 text-white sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-white/80">
            Interac waiting for you
          </p>
          <p className="mt-1 text-4xl font-bold tabular-nums">{formatCents(waitingCents)}</p>
          <p className="mt-1 text-sm text-white/85">
            {view === "open"
              ? `${items.length} e-Transfer${items.length === 1 ? "" : "s"} to review`
              : " "}
            {data && !data.inbox_enabled ? " · inbox reader off" : ""}
          </p>
        </div>
        <button
          type="button"
          onClick={() => sync.mutate()}
          disabled={sync.isPending}
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-white px-4 text-sm font-semibold text-primary disabled:opacity-60"
        >
          <RefreshCw className={cn("h-4 w-4", (sync.isPending || isFetching) && "animate-spin")} />
          Check inbox
        </button>
      </div>

      <div role="tablist" aria-label="e-Transfer views" className="flex gap-1.5">
        {VIEWS.map((v) => (
          <button
            key={v.id}
            role="tab"
            aria-selected={view === v.id}
            type="button"
            onClick={() => setView(v.id)}
            className={cn(
              "min-h-10 flex-1 rounded-xl px-3 text-sm font-medium sm:flex-none",
              view === v.id
                ? "bg-secondary text-white"
                : "bg-white text-primary ring-1 ring-primary/15"
            )}
          >
            {v.label}
          </button>
        ))}
      </div>

      {msg ? (
        <p role="status" className="rounded-xl bg-secondary/10 px-3 py-2 text-sm text-secondary">
          {msg}
        </p>
      ) : null}

      {isLoading ? (
        <TableSkeleton rows={4} />
      ) : items.length === 0 ? (
        <EmptyState
          title={view === "open" ? "Nothing to review" : "Nothing here yet"}
          hint="Merchants put the invoice code (PC-XXXXX) in the e-Transfer message. Matches show up here."
        />
      ) : (
        <ul className="space-y-3">
          {items.map((t) => {
            const suspicious = !t.auth_ok || t.status === "suspicious";
            const open = ["proposed", "needs_review", "suspicious"].includes(t.status);
            const target = pick[t.id]?.trim() || t.invoice_id;
            return (
              <li
                key={t.id}
                className={cn(
                  "rounded-2xl border bg-white p-4 shadow-sm",
                  suspicious
                    ? "border-red-300"
                    : t.status === "proposed"
                      ? "border-emerald-300"
                      : "border-primary/10"
                )}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-base font-semibold text-primary">
                      {t.sender_name || "Unknown sender"}
                    </p>
                    <p className="text-xs text-gray-700">
                      {t.received_at ? String(t.received_at).slice(0, 16).replace("T", " ") : "—"} ·{" "}
                      {t.kind === "autodeposit"
                        ? "Auto-deposited"
                        : t.kind === "deposited"
                          ? "Deposited"
                          : "Notification"}
                    </p>
                  </div>
                  <p className="text-2xl font-bold tabular-nums text-primary">
                    {formatCents(t.amount_cents)}
                  </p>
                </div>

                <dl className="mt-3 grid grid-cols-1 gap-x-4 gap-y-1 text-sm sm:grid-cols-2">
                  <div className="flex justify-between gap-2 sm:block">
                    <dt className="text-gray-700">Message</dt>
                    <dd className="truncate font-mono text-xs text-primary">{t.memo || "—"}</dd>
                  </div>
                  <div className="flex justify-between gap-2 sm:block">
                    <dt className="text-gray-700">Match</dt>
                    <dd className="text-primary">
                      {t.invoice_id ? (
                        <Link
                          href={`/finance/invoices/${t.invoice_id}`}
                          className="font-mono text-xs text-secondary underline"
                        >
                          {t.invoice_number}
                        </Link>
                      ) : (
                        "—"
                      )}{" "}
                      {t.match_note ? (
                        <span className="text-xs text-gray-700">
                          · {NOTE_LABEL[t.match_note] ?? t.match_note}
                        </span>
                      ) : null}
                    </dd>
                  </div>
                  {t.invoice_outstanding_cents != null ? (
                    <div className="flex justify-between gap-2 sm:block">
                      <dt className="text-gray-700">Invoice owes</dt>
                      <dd className="tabular-nums text-primary">
                        {formatCents(t.invoice_outstanding_cents)}
                      </dd>
                    </div>
                  ) : null}
                  {t.merchant_name ? (
                    <div className="flex justify-between gap-2 sm:block">
                      <dt className="text-gray-700">Merchant</dt>
                      <dd className="text-primary">{t.merchant_name}</dd>
                    </div>
                  ) : null}
                </dl>

                {suspicious ? (
                  <p className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">
                    <ShieldAlert className="h-4 w-4 shrink-0" />
                    Not verified as Interac{t.auth_detail ? ` (${t.auth_detail})` : ""}. Check your
                    bank before doing anything.
                  </p>
                ) : null}

                {open ? (
                  <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center">
                    {!suspicious && !t.invoice_id ? (
                      <input
                        aria-label="Invoice id to apply this payment to"
                        className="min-h-11 flex-1 rounded-xl border border-primary/20 px-3 text-sm"
                        placeholder="Paste invoice id to apply"
                        value={pick[t.id] ?? ""}
                        onChange={(e) => setPick((p) => ({ ...p, [t.id]: e.target.value }))}
                      />
                    ) : null}
                    {!suspicious ? (
                      <Button
                        className="min-h-11 bg-emerald-700 text-white hover:bg-emerald-800 sm:min-w-44"
                        disabled={!target || approve.isPending}
                        onClick={() => approve.mutate(t)}
                      >
                        <CheckCircle2 className="h-4 w-4" />
                        Approve {formatCents(t.amount_cents)}
                      </Button>
                    ) : null}
                    <Button
                      variant="outline"
                      className="min-h-11"
                      disabled={reject.isPending}
                      onClick={() => reject.mutate(t)}
                    >
                      Dismiss
                    </Button>
                  </div>
                ) : (
                  <p className="mt-3 flex items-center gap-2 text-sm text-gray-700">
                    <Inbox className="h-4 w-4" />
                    {t.status === "approved" ? "Applied" : t.status}{" "}
                    {t.reviewed_at ? `· ${String(t.reviewed_at).slice(0, 10)}` : ""}
                    {t.review_note ? ` · ${t.review_note}` : ""}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
      <div className="sr-only" aria-live="polite">
        {isFetching ? "Refreshing" : ""}
      </div>
    </div>
  );
}
