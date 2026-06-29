"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { Task } from "@/lib/crm";

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

const DOT: Record<string, string> = {
  meeting: "bg-violet-500",
  demo: "bg-violet-500",
  merchant_visit: "bg-teal-500",
  call: "bg-blue-500",
  email: "bg-sky-500",
  follow_up: "bg-amber-500",
};

export function MiniCalendar({ tasks }: { tasks: Task[] }) {
  const [cursor, setCursor] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  const byDay = useMemo(() => {
    const map = new Map<string, Task[]>();
    tasks.forEach((task) => {
      if (!task.due_at) return;
      const key = new Date(task.due_at).toDateString();
      map.set(key, [...(map.get(key) ?? []), task]);
    });
    return map;
  }, [tasks]);

  const cells = useMemo(() => {
    const start = new Date(cursor);
    start.setDate(1 - start.getDay());
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [cursor]);

  const today = new Date().toDateString();
  const upcoming = [...tasks]
    .filter((t) => t.due_at)
    .sort((a, b) => new Date(a.due_at!).getTime() - new Date(b.due_at!).getTime())
    .slice(0, 5);

  return (
    <div className="grid gap-5 md:grid-cols-2">
      <div className="rounded-xl border border-primary/10 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-semibold text-primary">
            {cursor.toLocaleDateString("en-CA", { month: "long", year: "numeric" })}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
              className="rounded-lg border border-primary/15 p-1 hover:bg-gray-bg"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
              className="rounded-lg border border-primary/15 p-1 hover:bg-gray-bg"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <div className="grid grid-cols-7 text-center text-[10px] font-semibold uppercase text-muted">
          {WEEKDAYS.map((d, i) => (
            <div key={i} className="py-1">
              {d}
            </div>
          ))}
        </div>
        <div className="grid grid-cols-7 gap-0.5">
          {cells.map((d, i) => {
            const inMonth = d.getMonth() === cursor.getMonth();
            const dayTasks = byDay.get(d.toDateString()) ?? [];
            const isToday = d.toDateString() === today;
            return (
              <div
                key={i}
                className={
                  "flex aspect-square flex-col items-center justify-center rounded-lg text-xs " +
                  (isToday
                    ? "bg-secondary font-bold text-white"
                    : inMonth
                      ? "text-primary"
                      : "text-muted/50")
                }
              >
                {d.getDate()}
                <div className="mt-0.5 flex gap-0.5">
                  {dayTasks.slice(0, 3).map((t) => (
                    <span
                      key={t.id}
                      className={"h-1 w-1 rounded-full " + (DOT[t.task_type] ?? "bg-slate-400")}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">Upcoming</p>
        <div className="space-y-2">
          {upcoming.map((t) => (
            <div
              key={t.id}
              className="flex items-center gap-2 rounded-xl border border-primary/10 p-2.5"
            >
              <span
                className={"h-2 w-2 shrink-0 rounded-full " + (DOT[t.task_type] ?? "bg-slate-400")}
              />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-primary">{t.title}</p>
                <p className="text-xs text-muted">
                  {new Date(t.due_at!).toLocaleString("en-CA", {
                    dateStyle: "medium",
                    timeStyle: "short",
                  })}
                </p>
              </div>
            </div>
          ))}
          {upcoming.length === 0 && (
            <p className="py-6 text-center text-sm text-muted">Nothing scheduled.</p>
          )}
        </div>
      </div>
    </div>
  );
}
