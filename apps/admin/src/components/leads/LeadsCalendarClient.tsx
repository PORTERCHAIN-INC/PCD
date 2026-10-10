"use client";

import Link from "next/link";
import { PageSkeleton } from "@porterchain/ui/loading";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button } from "@/components/crm/primitives";
import { leadsApi } from "@/lib/leads";
import type { Task } from "@/lib/crm";
import AdminPage from "@/components/layout/AdminPage";

function startOfWeek(d: Date): Date {
  const x = new Date(d);
  const day = (x.getDay() + 6) % 7; // Monday=0
  x.setHours(0, 0, 0, 0);
  x.setDate(x.getDate() - day);
  return x;
}

function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

function dayKey(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function formatDayHeader(d: Date): string {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(d);
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function LeadsCalendarClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [weekAnchor, setWeekAnchor] = useState(() => startOfWeek(new Date()));

  const range = useMemo(() => {
    const from = weekAnchor;
    const to = addDays(from, 7);
    return {
      due_after: from.toISOString(),
      due_before: to.toISOString(),
      days: Array.from({ length: 7 }, (_, i) => addDays(from, i)),
    };
  }, [weekAnchor]);

  const { data, isLoading } = useQuery({
    queryKey: ["lead-calendar", range.due_after, range.due_before],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () =>
      leadsApi.calendar(await getApiToken(), {
        due_after: range.due_after,
        due_before: range.due_before,
      }),
  });

  const tasks = Array.isArray(data) ? data : [];
  const byDay = useMemo(() => {
    const map = new Map<string, Task[]>();
    for (const day of range.days) map.set(dayKey(day), []);
    for (const task of tasks) {
      if (!task.due_at) continue;
      const key = dayKey(new Date(task.due_at));
      const list = map.get(key);
      if (list) list.push(task);
    }
    return map;
  }, [tasks, range.days]);

  return (
    <AdminPage>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/leads"
            className="mb-2 inline-flex items-center gap-2 text-sm text-secondary"
          >
            <ArrowLeft className="h-4 w-4" /> Back to leads
          </Link>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-secondary">
            Sales
          </p>
          <h1 className="text-3xl font-extrabold tracking-tight text-primary">Calendar</h1>
          <p className="text-sm text-slate-600">
            Calls and meetings — each item opens Lead 360 for that lead.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => setWeekAnchor((w) => addDays(w, -7))}
            aria-label="Previous week"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="secondary" onClick={() => setWeekAnchor(startOfWeek(new Date()))}>
            This week
          </Button>
          <Button
            variant="secondary"
            onClick={() => setWeekAnchor((w) => addDays(w, 7))}
            aria-label="Next week"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <PageSkeleton rows={3} />
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-7">
          {range.days.map((day) => {
            const key = dayKey(day);
            const items = byDay.get(key) ?? [];
            return (
              <div key={key} className="min-h-48 rounded-2xl border border-primary/10 bg-white p-3">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
                  {formatDayHeader(day)}
                </p>
                <div className="space-y-2">
                  {items.length === 0 ? (
                    <p className="text-xs text-muted">No appointments</p>
                  ) : (
                    items.map((task) => (
                      <Link
                        key={task.id}
                        href={task.entity_id ? `/leads/${task.entity_id}` : "/leads"}
                        className="block rounded-xl border border-primary/10 bg-slate-50 px-2.5 py-2 transition-colors hover:border-secondary/40 hover:bg-white"
                      >
                        <p className="text-xs font-semibold text-primary">
                          {formatTime(task.due_at)}
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-secondary">{task.title}</p>
                        <div className="mt-1">
                          <Badge tone="slate">{task.task_type}</Badge>
                        </div>
                      </Link>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </AdminPage>
  );
}
