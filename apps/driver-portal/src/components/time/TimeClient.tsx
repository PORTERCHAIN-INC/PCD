"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import DriverShell from "@/components/DriverShell";
import {
  timeApi,
  workedLabel,
  type DayKey,
  type ScheduleResponse,
  type WeekSchedule,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const DAYS: Array<{ k: DayKey; label: string }> = [
  { k: "mon", label: "Mon" },
  { k: "tue", label: "Tue" },
  { k: "wed", label: "Wed" },
  { k: "thu", label: "Thu" },
  { k: "fri", label: "Fri" },
  { k: "sat", label: "Sat" },
  { k: "sun", label: "Sun" },
];
const tz = "America/Toronto";
const day = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
const time = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleTimeString("en-CA", {
        hour: "numeric",
        minute: "2-digit",
        timeZone: tz,
      })
    : "now";

export default function TimeClient() {
  const [tab, setTab] = useState<"sheets" | "availability">("sheets");
  return (
    <DriverShell>
      <div className="mx-auto w-full max-w-5xl">
        <header className="flex flex-wrap items-end justify-between gap-4 pb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-[var(--primary)]">Time</h1>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Timesheets and the hours dispatch can plan you · Toronto time
            </p>
          </div>
          <div className="flex rounded-xl bg-white p-1" role="tablist">
            {(["sheets", "availability"] as const).map((t) => (
              <button
                key={t}
                role="tab"
                aria-selected={tab === t}
                onClick={() => setTab(t)}
                className={cn(
                  "rounded-lg px-4 py-2 text-sm font-semibold",
                  tab === t ? "bg-[var(--primary)] text-white" : "text-[var(--primary)]"
                )}
              >
                {t === "sheets" ? "Timesheets" : "Availability"}
              </button>
            ))}
          </div>
        </header>
        {tab === "sheets" ? <Sheets /> : <Availability />}
      </div>
    </DriverShell>
  );
}

function Sheets() {
  const q = useQuery({ queryKey: ["driver-timesheets"], queryFn: () => timeApi.timesheets(8) });
  if (!q.data) return <div className="h-64 animate-pulse rounded-2xl bg-white" />;
  if (!q.data.weeks.length)
    return (
      <p className="rounded-2xl bg-white p-6 text-sm text-[var(--muted)]">
        No shifts in the last 8 weeks.
      </p>
    );
  return (
    <div className="space-y-5">
      <p className="text-4xl font-bold text-[var(--primary)]">
        {workedLabel(q.data.total_worked_minutes)}{" "}
        <span className="text-base font-semibold text-[var(--muted)]">worked · 8 weeks</span>
      </p>
      {q.data.weeks.map((w) => (
        <section
          key={w.week_start}
          className="rounded-2xl border border-[var(--primary)]/8 bg-white"
        >
          <div className="flex items-center justify-between border-b border-[var(--primary)]/8 px-6 py-4">
            <h2 className="font-bold text-[var(--primary)]">Week of {day(w.week_start)}</h2>
            <span className="text-sm font-semibold text-[var(--primary)]">
              {workedLabel(w.worked_minutes)} · {w.km} km
            </span>
          </div>
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="px-6 py-2">Day</th>
                <th>Start</th>
                <th>End</th>
                <th>Break</th>
                <th>Km</th>
                <th className="pr-6 text-right">Worked</th>
              </tr>
            </thead>
            <tbody>
              {w.shifts.map((s) => (
                <tr key={s.id} className="border-t border-[var(--primary)]/5">
                  <td className="px-6 py-3 font-semibold">{day(s.date)}</td>
                  <td>{time(s.started_at)}</td>
                  <td>{time(s.ended_at)}</td>
                  <td>{workedLabel(s.break_minutes)}</td>
                  <td>{s.km}</td>
                  <td className="pr-6 text-right font-bold">{workedLabel(s.worked_minutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

function Availability() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["driver-schedule"], queryFn: timeApi.schedule });
  const [msg, setMsg] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: timeApi.saveSchedule,
    onMutate: (s) => {
      const prev = qc.getQueryData<ScheduleResponse>(["driver-schedule"]);
      qc.setQueryData(["driver-schedule"], { ...(prev ?? { weekly_hours: 0 }), schedule: s });
      return { prev };
    },
    onError: (e, _s, ctx) => {
      if (ctx?.prev) qc.setQueryData(["driver-schedule"], ctx.prev);
      setMsg(e instanceof Error ? e.message : "Not saved");
    },
    onSuccess: (out) => {
      qc.setQueryData(["driver-schedule"], out);
      setMsg("Saved");
    },
  });
  if (!q.data) return <div className="h-64 animate-pulse rounded-2xl bg-white" />;
  const s = q.data.schedule;
  const put = (next: WeekSchedule) => save.mutate(next);
  return (
    <section className="rounded-2xl border border-[var(--primary)]/8 bg-white p-6">
      <p className="mb-5 text-4xl font-bold text-[var(--primary)]">
        {q.data.weekly_hours} h{" "}
        <span className="text-base font-semibold text-[var(--muted)]">available per week</span>
      </p>
      <ul className="divide-y divide-[var(--primary)]/8">
        {DAYS.map(({ k, label }) => {
          const block = s[k]?.[0];
          return (
            <li key={k} className="flex flex-wrap items-center gap-4 py-3">
              <label className="flex w-28 items-center gap-3 font-semibold text-[var(--primary)]">
                <input
                  type="checkbox"
                  checked={Boolean(block)}
                  onChange={(e) =>
                    put({ ...s, [k]: e.target.checked ? [{ start: "08:00", end: "16:00" }] : [] })
                  }
                />
                {label}
              </label>
              {block ? (
                <div className="flex items-center gap-2 text-sm">
                  <input
                    type="time"
                    value={block.start}
                    onChange={(e) => put({ ...s, [k]: [{ ...block, start: e.target.value }] })}
                    className="h-10 rounded-lg border border-[var(--primary)]/12 px-2"
                  />
                  <span>–</span>
                  <input
                    type="time"
                    value={block.end}
                    onChange={(e) => put({ ...s, [k]: [{ ...block, end: e.target.value }] })}
                    className="h-10 rounded-lg border border-[var(--primary)]/12 px-2"
                  />
                </div>
              ) : (
                <span className="text-sm text-[var(--muted)]">Off</span>
              )}
            </li>
          );
        })}
      </ul>
      {msg ? (
        <p role="status" className="mt-4 text-sm text-[var(--muted)]">
          {msg}
        </p>
      ) : null}
    </section>
  );
}
