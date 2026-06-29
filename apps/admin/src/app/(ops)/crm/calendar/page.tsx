"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { crm, type Task } from "@/lib/crm";
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
};

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function CalendarPage() {
  const { data, error } = useApiData((t) => crm.tasks(t), []);
  const [cursor, setCursor] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  const byDay = useMemo(() => {
    const map = new Map<string, Task[]>();
    (data ?? []).forEach((task) => {
      if (!task.due_at) return;
      const key = new Date(task.due_at).toDateString();
      const list = map.get(key) ?? [];
      list.push(task);
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

  return (
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
          const tasks = byDay.get(d.toDateString()) ?? [];
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
                {tasks.slice(0, 3).map((task) => (
                  <div
                    key={task.id}
                    title={task.title}
                    className={
                      "truncate rounded px-1.5 py-0.5 text-[11px] font-medium " +
                      (TONE_BG[task.task_type] ?? "bg-slate-100 text-slate-700") +
                      (task.status === "done" ? " line-through opacity-60" : "")
                    }
                  >
                    {task.title}
                  </div>
                ))}
                {tasks.length > 3 && (
                  <p className="px-1 text-[11px] text-muted">+{tasks.length - 3} more</p>
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
      </div>
    </SectionCard>
  );
}
