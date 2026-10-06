"use client";

import MagicCard from "@/components/magic/MagicCard";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import {
  createStandingOrder,
  listBookingTemplates,
  listStandingOrders,
  turnOffStandingOrder,
  type BookingTemplate,
  type StandingOrder,
} from "@/lib/booking";
import { formatDate } from "@/lib/utils";
import { DateTimePickerSeparateField } from "@porterchain/ui/datetime-picker-separate";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

const RULES = [
  { id: "daily", label: "Every day" },
  { id: "weekly", label: "Every week" },
  { id: "biweekly", label: "Every two weeks" },
  { id: "monthly", label: "Every month" },
] as const;

function ruleLabel(rule: string): string {
  return RULES.find((row) => row.id === rule)?.label ?? rule;
}

function defaultFirstRun(): string {
  const next = new Date();
  next.setDate(next.getDate() + 1);
  next.setSeconds(0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${next.getFullYear()}-${pad(next.getMonth() + 1)}-${pad(next.getDate())}T${pad(next.getHours())}:${pad(next.getMinutes())}`;
}

function localToIso(local: string): string {
  const date = new Date(local);
  if (Number.isNaN(date.getTime())) {
    throw new Error("Choose when the first booking should run.");
  }
  return date.toISOString();
}

export default function StandingOrdersClient() {
  const { getApiToken, orgId } = useMerchantAuth();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState("");
  const [rule, setRule] = useState<(typeof RULES)[number]["id"]>("weekly");
  const [firstRun, setFirstRun] = useState(defaultFirstRun);

  const query = useQuery({
    queryKey: ["merchant-standing-orders", orgId ?? null],
    queryFn: async () => {
      const token = await getApiToken();
      const [schedules, saved] = await Promise.all([
        listStandingOrders(token, orgId),
        listBookingTemplates(token, orgId),
      ]);
      return { schedules, saved };
    },
  });
  const rows: StandingOrder[] = query.data?.schedules ?? [];
  const templates: BookingTemplate[] = query.data?.saved ?? [];
  const error =
    actionError ||
    (query.error instanceof Error ? query.error.message : query.error ? String(query.error) : null);

  useEffect(() => {
    setTemplateId((current) => current || templates[0]?.id || "");
  }, [templates]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    if (!templateId) {
      setActionError("Save a booking from Single first, then schedule it here.");
      return;
    }
    setBusy(true);
    setActionError(null);
    try {
      const token = await getApiToken();
      await createStandingOrder(
        token,
        {
          booking_template_id: templateId,
          recurrence_rule: rule,
          next_run_at: localToIso(firstRun),
        },
        orgId
      );
      await qc.invalidateQueries({ queryKey: ["merchant-standing-orders", orgId ?? null] });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not create this schedule");
    } finally {
      setBusy(false);
    }
  }

  async function onTurnOff(id: string) {
    if (!window.confirm("Turn this schedule off? Existing bookings stay as they are.")) return;
    setBusy(true);
    setActionError(null);
    try {
      const token = await getApiToken();
      await turnOffStandingOrder(token, id, orgId);
      await qc.invalidateQueries({ queryKey: ["merchant-standing-orders", orgId ?? null] });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not turn off this schedule");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4">
      <MagicCard className="space-y-4 p-4 sm:p-6" clip={false}>
        <div>
          <h2 className="text-sm font-semibold text-primary">New schedule</h2>
          <p className="mt-1 text-sm text-muted">
            PorterChain books from a saved Single booking on the days you pick. The worker already
            running this app creates the order — this page only starts or stops the schedule.
          </p>
        </div>
        {query.isLoading && !query.data ? (
          <PageSkeleton rows={3} />
        ) : templates.length === 0 ? (
          <p className="rounded-xl border border-primary/10 bg-gray-bg/60 px-4 py-3 text-sm text-muted">
            No saved bookings yet. Open the Single tab, fill a delivery, save it, then come back
            here.
          </p>
        ) : (
          <form className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" onSubmit={onCreate}>
            <label className="text-sm font-medium text-primary sm:col-span-2">
              Saved booking
              <select
                className="mt-1 w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm"
                value={templateId}
                onChange={(event) => setTemplateId(event.target.value)}
                required
              >
                {templates.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-medium text-primary">
              Repeat
              <select
                className="mt-1 w-full rounded-xl border border-primary/15 bg-white px-3 py-2.5 text-sm"
                value={rule}
                onChange={(event) => setRule(event.target.value as (typeof RULES)[number]["id"])}
              >
                {RULES.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.label}
                  </option>
                ))}
              </select>
            </label>
            <div className="text-sm font-medium text-primary sm:col-span-2 lg:col-span-4">
              First run
              <div className="mt-1">
                <DateTimePickerSeparateField
                  value={firstRun}
                  onChange={setFirstRun}
                  timezone="America/Toronto"
                  showTimezone={false}
                  hourFormat={12}
                  timeInterval={15}
                  dateLabel="Date"
                  timeLabel="Time"
                  datePlaceholder="First run date"
                  timePlaceholder="First run time"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={busy}
              className="min-h-10 rounded-full bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60 sm:col-span-2 lg:col-span-1"
            >
              {busy ? "Saving…" : "Turn on"}
            </button>
          </form>
        )}
      </MagicCard>

      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      <MagicCard className="min-w-0 p-0" clip={false}>
        <div className="border-b border-primary/10 px-4 py-3 sm:px-5">
          <h2 className="text-sm font-semibold text-primary">Schedules</h2>
          <p className="mt-1 text-xs text-muted">
            Last run, next run, and any failure in plain language.
          </p>
        </div>
        {rows.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-muted">No recurring schedules yet.</p>
        ) : (
          <ul className="divide-y divide-primary/10">
            {rows.map((row) => (
              <li key={row.id} className="space-y-2 px-4 py-4 sm:px-5">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <p className="font-medium text-primary">
                      {row.template_name || "Saved booking"}
                    </p>
                    <p className="mt-0.5 text-sm text-muted">
                      {ruleLabel(row.recurrence_rule)}
                      {row.is_active ? "" : " · Off"}
                    </p>
                  </div>
                  {row.is_active ? (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void onTurnOff(row.id)}
                      className="min-h-10 shrink-0 rounded-full border border-primary/15 px-4 py-2 text-sm font-medium text-primary hover:bg-gray-bg disabled:opacity-60"
                    >
                      Turn off
                    </button>
                  ) : null}
                </div>
                <dl className="grid gap-2 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-xs text-muted">Last run</dt>
                    <dd className="text-primary">
                      {row.last_run_at ? formatDate(row.last_run_at) : "Not yet"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Next run</dt>
                    <dd className="text-primary">{formatDate(row.next_run_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted">Last order</dt>
                    <dd>
                      {row.last_order_id ? (
                        <Link
                          className="text-secondary hover:underline"
                          href={`/orders/${row.last_order_id}`}
                        >
                          Open order
                        </Link>
                      ) : (
                        <span className="text-muted">None yet</span>
                      )}
                    </dd>
                  </div>
                </dl>
                {row.last_error ? (
                  <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    {row.last_error}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </MagicCard>
    </section>
  );
}
