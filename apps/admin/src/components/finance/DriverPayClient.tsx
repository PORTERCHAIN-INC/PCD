"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn, formatCents } from "@porterchain/ui/utils";
import { PageSkeleton, TableSkeleton } from "@porterchain/ui/loading";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { financeApi } from "@/lib/finance";
import { financeOpsApi, type PayoutRun } from "@/lib/finance-ops";
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

const iso = (d: Date) => d.toISOString().slice(0, 10);

/** Default pay period: last Monday–Sunday (pay day Friday, per the driver schedule). */
function lastWeek(now = new Date()) {
  const day = (now.getDay() + 6) % 7; // Monday = 0
  const end = new Date(now);
  end.setDate(now.getDate() - day - 1);
  const start = new Date(end);
  start.setDate(end.getDate() - 6);
  return { start: iso(start), end: iso(end) };
}

const STEP: Record<PayoutRun["status"], string> = {
  draft: "Review",
  approved: "Send the bank file",
  paid: "Paid",
  discarded: "Discarded",
};

export default function DriverPayClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const qc = useQueryClient();
  const [range, setRange] = useState(lastWeek);
  const [error, setError] = useState<string | null>(null);

  const runs = useQuery({
    queryKey: ["finance-payout-runs"],
    enabled,
    queryFn: async () => (await financeOpsApi.payoutRuns(await getApiToken())).items,
  });
  const payouts = useQuery({
    queryKey: ["finance-payouts"],
    enabled,
    queryFn: async () => financeApi.payouts(await getApiToken()),
  });
  const current = useMemo(
    () => (runs.data ?? []).find((r) => r.status === "draft" || r.status === "approved") ?? null,
    [runs.data]
  );
  const history = (runs.data ?? []).filter((r) => r.id !== current?.id);

  const done = () => {
    setError(null);
    void qc.invalidateQueries({ queryKey: ["finance-payout-runs"] });
    void qc.invalidateQueries({ queryKey: ["finance-payouts"] });
  };
  const onError = (e: unknown) => setError(e instanceof Error ? e.message : "Something went wrong");

  const create = useMutation({
    mutationFn: async () =>
      financeOpsApi.createPayoutRun(
        await getApiToken(),
        `${range.start}T00:00:00Z`,
        new Date(new Date(`${range.end}T00:00:00Z`).getTime() + 86400000).toISOString()
      ),
    onSuccess: done,
    onError,
  });
  const act = useMutation({
    mutationFn: async (action: "approve" | "mark-paid" | "discard") => {
      const token = await getApiToken();
      const run = () => financeOpsApi.payoutRunAction(token, current!.id, action);
      return action === "discard" ? run() : withStaffStepUp(token, run);
    },
    onSuccess: done,
    onError,
  });

  async function bankFile() {
    if (current) await financeOpsApi.downloadBankCsv(await getApiToken(), current.id);
  }

  let primary = (
    <PrimaryButton disabled={create.isPending} onClick={() => create.mutate()}>
      {create.isPending ? "Building…" : "Build pay run"}
    </PrimaryButton>
  );
  if (current?.status === "draft") {
    primary = (
      <PrimaryButton
        disabled={act.isPending || !current.driver_count}
        onClick={() => act.mutate("approve")}
      >
        Approve {formatCents(current.total_cents)}
      </PrimaryButton>
    );
  } else if (current?.status === "approved") {
    primary = (
      <PrimaryButton disabled={act.isPending} onClick={() => act.mutate("mark-paid")}>
        Mark {current.driver_count} paid
      </PrimaryButton>
    );
  }

  return (
    <FinanceShell
      title="Driver Pay"
      subtitle="Pick a period, check each driver, approve, send the bank file, mark paid."
      primary={primary}
    >
      {error ? (
        <p
          role="alert"
          className="rounded-2xl bg-red-50 px-4 py-3 text-sm font-medium text-red-800"
        >
          {error.startsWith("draft_run_exists")
            ? "Finish or discard the open draft first."
            : error === "nothing_to_pay"
              ? "No driver has unpaid earnings in that period."
              : error}
        </p>
      ) : null}

      {runs.isLoading ? (
        <PageSkeleton rows={3} />
      ) : current ? (
        <Hero
          label={`${STEP[current.status]} · ${current.period_start.slice(0, 10)} → ${current.period_end.slice(0, 10)}`}
          value={formatCents(current.total_cents)}
        >
          <div className="flex flex-wrap items-end justify-between gap-4 border-t border-primary/10 pt-5">
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
              <Stat label="Drivers" value={String(current.driver_count)} />
              <Stat
                label="Deliveries"
                value={String(current.lines.reduce((n, l) => n + (l.deliveries || 0), 0))}
              />
              <Stat label="Status" value={current.status === "draft" ? "Draft" : "Approved"} />
            </div>
            <div className="flex gap-1">
              {current.status !== "draft" ? (
                <QuietButton onClick={() => void bankFile()}>Bank file (CSV)</QuietButton>
              ) : null}
              {current.status === "draft" ? (
                <QuietButton disabled={act.isPending} onClick={() => act.mutate("discard")}>
                  Discard
                </QuietButton>
              ) : null}
            </div>
          </div>
        </Hero>
      ) : (
        <section className="rounded-3xl border border-primary/10 bg-white p-6 sm:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">Pay period</p>
          <div className="mt-3 flex flex-wrap items-end gap-3">
            <label className="text-sm text-primary">
              <span className="block text-xs font-semibold text-muted">From</span>
              <input
                type="date"
                value={range.start}
                onChange={(e) => setRange((r) => ({ ...r, start: e.target.value }))}
                className="mt-1 min-h-11 rounded-xl border border-primary/15 px-3"
              />
            </label>
            <label className="text-sm text-primary">
              <span className="block text-xs font-semibold text-muted">To (inclusive)</span>
              <input
                type="date"
                value={range.end}
                onChange={(e) => setRange((r) => ({ ...r, end: e.target.value }))}
                className="mt-1 min-h-11 rounded-xl border border-primary/15 px-3"
              />
            </label>
          </div>
          <p className="mt-3 text-sm text-muted">
            Each driver gets what they earned in the period, never more than their wallet balance.
          </p>
        </section>
      )}

      {current ? (
        <Section title="Per driver">
          {!current.lines.length ? (
            <Empty>No driver earned anything in this period.</Empty>
          ) : (
            <ul className="divide-y divide-primary/10">
              {current.lines.map((l) => (
                <li key={l.driver_id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-primary">{l.name}</p>
                    <p className="truncate text-xs text-muted">
                      {l.email} · {l.deliveries} deliveries
                      {l.earned_cents > l.amount_cents
                        ? ` · capped at wallet ${formatCents(l.wallet_cents)}`
                        : ""}
                    </p>
                  </div>
                  {l.error ? (
                    <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-800">
                      {l.error}
                    </span>
                  ) : l.payout_id ? (
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                      Reserved
                    </span>
                  ) : null}
                  <span className="w-28 text-right text-lg font-bold tabular-nums text-primary">
                    {formatCents(l.amount_cents)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Section>
      ) : null}

      <Section title="Past runs">
        {!history.length ? (
          <Empty>No pay runs yet.</Empty>
        ) : (
          <ul className="divide-y divide-primary/10">
            {history.map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <span className="text-primary">
                  {r.period_start.slice(0, 10)} → {r.period_end.slice(0, 10)} · {r.driver_count}{" "}
                  drivers
                </span>
                <span className="flex items-center gap-3">
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-1 text-xs font-semibold capitalize",
                      r.status === "paid"
                        ? "bg-emerald-50 text-emerald-800"
                        : "bg-primary/5 text-primary"
                    )}
                  >
                    {r.status}
                  </span>
                  <span className="w-24 text-right font-bold tabular-nums text-primary">
                    {formatCents(r.total_cents)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Every payout">
        {payouts.isLoading ? (
          <TableSkeleton rows={4} />
        ) : !(payouts.data ?? []).length ? (
          <Empty>No payouts yet.</Empty>
        ) : (
          <ul className="divide-y divide-primary/10">
            {(payouts.data ?? []).slice(0, 50).map((p) => (
              <li
                key={p.payout_id}
                className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm"
              >
                <span className="min-w-0 flex-1 truncate text-primary">
                  {p.driver_name || p.driver_id}
                </span>
                <span className="text-xs capitalize text-muted">
                  {p.status} · {String(p.created_at).slice(0, 10)}
                </span>
                <span className="w-24 text-right font-semibold tabular-nums text-primary">
                  {formatCents(p.amount_cents)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </FinanceShell>
  );
}
