"use client";

import type { ReactNode } from "react";
import { formatDate } from "@/lib/utils";

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="font-semibold text-primary">{title}</h2>
      <div className="mt-3 text-sm">{children}</div>
    </section>
  );
}

export function pickupWindowFromStops(
  stops?: Array<Record<string, unknown>> | null
): string | null {
  const pickup = (stops || []).find((stop) => {
    const kind = String(stop.stop_type || stop.type || "").toLowerCase();
    return kind === "pickup" || kind === "pick";
  });
  if (!pickup) return null;
  const start = pickup.time_window_start;
  const end = pickup.time_window_end;
  if (!start && !end) return null;
  return `${start ? formatDate(String(start)) : "?"} – ${end ? formatDate(String(end)) : "?"}`;
}
