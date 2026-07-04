"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { crm, type CrmCalendarEvent } from "@/lib/crm";
import { SectionCard, Spinner } from "@/components/crm/primitives";
import { titleCase } from "@/lib/crmFormat";

const TONE_BG: Record<string, string> = {
  call: "bg-blue-100 text-blue-700",
  email: "bg-sky-100 text-sky-700",
  meeting: "bg-violet-100 text-violet-700",
  demo: "bg-violet-100 text-violet-700",
  merchant_visit: "bg-teal-100 text-teal-700",
  follow_up: "bg-amber-100 text-amber-700",
  document: "bg-slate-100 text-slate-700",
  contract_review: "bg-teal-100 text-teal-700",
  todo: "bg-slate-100 text-slate-700",
  zoho: "bg-indigo-100 text-indigo-800",
};

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function monthRange(cursor: Date) {
  const start = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
  const gridStart = new Date(start);
  gridStart.setDate(1 - gridStart.getDay());
  const gridEnd = new Date(gridStart);
  gridEnd.setDate(gridStart.getDate() + 41);
  gridEnd.setHours(23, 59, 59, 999);
  return { start: gridStart, end: gridEnd };
}

export default function CalendarPage() {
  const [cursor, setCursor] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  const range = useMemo(() => monthRange(cursor), [cursor]);
  const rangeKey = `${range.start.toISOString()}_${range.end.toISOString()}`;

  const { data, error } = useApiData(
    (t) =>
      crm.calendarEvents(t, {
        start: range.start.toISOString(),
        end: range.end.toISOString(),
      }),
    [rangeKey]
  );

  const byDay = useMemo(() => {
    const map = new Map<string, CrmCalendarEvent[]>();
    const all = [...(data?.crm_events ?? []), ...(data?.zoho_events ?? [])];
    all.forEach((event) => {
      if (!event.start) return;
      const key = new Date(event.start).toDateString();
      const list = map.get(key) ?? [];
      list.push(event);
      map.set(key, list);
    });
    return map;
  }, [data]);

  const cells = useMemo(() => {
    const start = new Date(cursor);
    start.setDate(1 - start.getDay());
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [cursor]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <Spinner label="Loading calendar…" />;

  const today = new Date().toDateString();
  const monthLabel = cursor.toLocaleDateString("en-CA", { month: "long", year: "numeric" });
  const zohoConnected = data.integration.configured;

  return (
    <div className="space-y-4">
      <div
        className={
          "rounded-xl border px-4 py-3 text-sm " +
          (zohoConnected
            ? "border-emerald-200 bg-emerald-50 text-emerald-900"
            : "border-amber-200 bg-amber-50 text-amber-900")
        }
      >
        {zohoConnected ? (
          <p>
            <span className="font-semibold">Zoho Calendar connected.</span> CRM meetings sync to Zoho;
            external Zoho events appear below in indigo.
          </p>
        ) : (
          <p>
            <span className="font-semibold">Zoho Calendar not configured.</span> Showing CRM tasks only.
            {data.integration.missing.length > 0 && (
              <span className="ml-1">Missing: {data.integration.missing.join(", ")}</span>
            )}
          </p>
        )}
        {data.zoho_error && (
          <p className="mt-1 text-xs text-red-700">Zoho fetch error: {data.zoho_error}</p>
        )}
      </div>

      <SectionCard
        title={monthLabel}
        action={
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
              className="rounded-lg border border-primary/15 p-1.5 hover:bg-gray-bg"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setCursor(new Date(new Date().getFullYear(), new Date().getMonth(), 1))}
              className="rounded-lg border border-primary/15 px-3 py-1.5 text-xs font-medium hover:bg-gray-bg"
            >
              Today
            </button>
            <button
              onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
              className="rounded-lg border border-primary/15 p-1.5 hover:bg-gray-bg"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        }
      >
        <div className="grid grid-cols-7 border-b border-primary/10 text-xs font-semibold uppercase text-muted">
          {WEEKDAYS.map((d) => (
            <div key={d} className="px-2 py-2 text-center">
              {d}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7">
          {cells.map((d, i) => {
            const inMonth = d.getMonth() === cursor.getMonth();
            const events = byDay.get(d.toDateString()) ?? [];
            const isToday = d.toDateString() === today;
            return (
              <div
                key={i}
                className={
                  "min-h-[104px] border-b border-r border-primary/5 p-1.5 " +
                  (inMonth ? "bg-white" : "bg-gray-bg/30")
                }
              >
                <div
                  className={
                    "mb-1 flex h-6 w-6 items-center justify-center rounded-full text-xs " +
                    (isToday
                      ? "bg-secondary font-bold text-white"
                      : inMonth
                        ? "text-primary"
                        : "text-muted")
                  }
                >
                  {d.getDate()}
                </div>
                <div className="space-y-1">
                  {events.slice(0, 3).map((event) => (
                    <div
                      key={`${event.source}-${event.id}`}
                      title={event.title}
                      className={
                        "truncate rounded px-1.5 py-0.5 text-[11px] font-medium " +
                        (event.source === "zoho"
                          ? TONE_BG.zoho
                          : TONE_BG[event.task_type ?? "todo"] ?? "bg-slate-100 text-slate-700") +
                        (event.status === "done" ? " line-through opacity-60" : "")
                      }
                    >
                      {event.source === "zoho" ? "◆ " : ""}
                      {event.title}
                    </div>
                  ))}
                  {events.length > 3 && (
                    <p className="px-1 text-[11px] text-muted">+{events.length - 3} more</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap gap-3 px-4 py-3 text-xs text-muted">
          {["meeting", "follow_up", "call", "demo", "merchant_visit"].map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5">
              <span className={"h-2.5 w-2.5 rounded-full " + (TONE_BG[t] ?? "bg-slate-100")} />
              {titleCase(t)}
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5">
            <span className={"h-2.5 w-2.5 rounded-full " + TONE_BG.zoho} />
            Zoho Calendar
          </span>
        </div>
      </SectionCard>
    </div>
  );
}
