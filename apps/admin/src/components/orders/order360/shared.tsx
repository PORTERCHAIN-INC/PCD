"use client";

import { type ReactNode } from "react";
import {
  CheckCircle2,
  Circle,
  CircleDot,
  ClipboardList,
  FileCheck2,
  History,
  LifeBuoy,
  Sparkles,
  Wallet,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { SLA_TONE } from "@/lib/operations";
import { type OrderDetail } from "@/lib/orders";
import { dateTime, titleCase } from "@/lib/crmFormat";
import { Badge } from "@/components/crm/primitives";
import type { ExceptionColumn } from "@/components/orders/ExceptionReasonModal";

export const STATE_RANK: Record<string, number> = {
  BOOKED: 0,
  DISPATCH_READY: 1,
  DRIVER_ASSIGNED: 2,
  DRIVER_ACCEPTED: 3,
  DRIVER_EN_ROUTE: 4,
  AT_PICKUP: 5,
  PICKED_UP: 6,
  IN_TRANSIT: 7,
  AT_DESTINATION: 8,
  DELIVERED: 9,
  POD_COMPLETED: 10,
  INVOICED: 11,
  CLOSED: 12,
  CANCELLED: 0,
  REFUNDED: 0,
  FAILED: 6,
  RETURN_TO_SENDER: 6,
  DAMAGED: 6,
  LOST: 6,
  CLAIM_OPEN: 6,
};

export const WAYPOINT_DONE = new Set(["completed", "delivered", "picked_up", "done"]);

export const str = (v: unknown): string | null => (typeof v === "string" && v.trim() ? v : null);

export function addressOf(rec: Record<string, unknown> | null | undefined): string {
  if (!rec) return "—";
  for (const k of ["formatted_address", "formatted", "address", "street1", "city", "name"]) {
    const v = str(rec[k]);
    if (v) return v;
  }
  return "—";
}

export function trackingWaypointStatuses(
  tracking: Record<string, unknown> | null | undefined
): string[] {
  if (!tracking) return [];
  const direct = tracking["waypoints"];
  const nested = (tracking["payload"] as Record<string, unknown> | undefined)?.["waypoints"];
  const wp = Array.isArray(direct) ? direct : Array.isArray(nested) ? nested : [];
  return wp.map((w) => {
    const r = (w ?? {}) as Record<string, unknown>;
    return (str(r["status"]) ?? str(r["status_code"]) ?? "").toLowerCase();
  });
}

export type StopView = {
  key: string;
  label: string;
  address: string;
  state: "done" | "current" | "pending";
};

export function buildStops(detail: OrderDetail): StopView[] {
  const rank = STATE_RANK[detail.state] ?? 0;
  const mids = (detail.additional_stops ?? []).map((s) => (s ?? {}) as Record<string, unknown>);
  const wp = trackingWaypointStatuses(detail.tracking);
  const stops: StopView[] = [
    {
      key: "pickup",
      label: "Pickup",
      address: addressOf(detail.pickup_detail),
      state: rank >= 6 ? "done" : rank >= 4 ? "current" : "pending",
    },
    ...mids.map((m, i): StopView => ({
      key: `stop-${i}`,
      label: `Stop ${i + 1}`,
      address: addressOf(m),
      state: rank >= 9 || WAYPOINT_DONE.has(wp[i] ?? "") ? "done" : "pending",
    })),
    {
      key: "dropoff",
      label: "Delivery",
      address: addressOf(detail.dropoff_detail),
      state: rank >= 9 ? "done" : rank === 8 ? "current" : "pending",
    },
  ];
  // IN_TRANSIT and similar states don't pin a leg — flag the first pending stop.
  if (rank >= 6 && rank < 9 && !stops.some((s) => s.state === "current")) {
    const next = stops.find((s) => s.state === "pending");
    if (next) next.state = "current";
  }
  return stops;
}

export function paymentTone(s: string | null | undefined): string {
  if (s === "SUCCEEDED") return "green";
  if (s === "FAILED") return "red";
  return s ? "amber" : "slate";
}

export function SlaBadge({ sla }: { sla: string }) {
  return (
    <Badge tone={SLA_TONE[sla] ?? "slate"}>{sla === "at_risk" ? "At risk" : titleCase(sla)}</Badge>
  );
}

export function Strip({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="rounded-xl border border-primary/10 bg-white p-3">
      <p className="text-[11px] font-medium text-muted">{label}</p>
      <div className="mt-1 text-sm font-semibold text-primary">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-muted">{sub}</div>}
    </div>
  );
}

export function RouteTimeline({ detail }: { detail: OrderDetail }) {
  const stops = buildStops(detail);
  return (
    <div className="rounded-2xl border border-primary/10 bg-white">
      <div className="flex items-center justify-between border-b border-primary/10 px-4 py-3">
        <p className="text-sm font-semibold text-primary">
          Route · {stops.length} stop{stops.length === 1 ? "" : "s"}
        </p>
        <span className="text-[11px] text-muted">Per-stop status syncs from Fleetbase</span>
      </div>
      <div className="px-4 py-4">
        {stops.map((s, i) => (
          <div key={s.key} className="relative flex gap-3 pb-4 last:pb-0">
            {i < stops.length - 1 && (
              <span className="absolute left-[9px] top-6 h-[calc(100%-1.25rem)] w-0.5 bg-primary/10" />
            )}
            <span className="z-10 mt-0.5 shrink-0 bg-white">
              {s.state === "done" ? (
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              ) : s.state === "current" ? (
                <CircleDot className="h-5 w-5 text-secondary" />
              ) : (
                <Circle className="h-5 w-5 text-primary/25" />
              )}
            </span>
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
                {s.label}
                {s.state === "current" && <Badge tone="blue">In progress</Badge>}
              </p>
              <p
                className={cn(
                  "truncate text-sm",
                  s.state === "pending" ? "text-muted" : "text-primary"
                )}
              >
                {s.address}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export type DrawerTab = "overview" | "assist" | "journey" | "evidence" | "money" | "care";
export const DRAWER_TABS: {
  id: DrawerTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  { id: "overview", label: "Overview", icon: ClipboardList },
  { id: "journey", label: "Journey", icon: History },
  { id: "assist", label: "Assist", icon: Sparkles },
  { id: "evidence", label: "Evidence", icon: FileCheck2 },
  { id: "money", label: "Money", icon: Wallet },
  { id: "care", label: "Care", icon: LifeBuoy },
];

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
  return `${start ? dateTime(String(start)) : "?"} – ${end ? dateTime(String(end)) : "?"}`;
}

export function exceptionColumnFromState(state?: string): ExceptionColumn | "" {
  const s = (state || "").toUpperCase();
  if (s === "FAILED") return "failed";
  if (s === "RETURN_TO_SENDER") return "returned";
  if (s === "LOST") return "lost";
  if (s === "DAMAGED") return "damaged";
  return "";
}

export type NextAction = {
  key: string;
  label: string;
  hint: string;
  kind: "assign" | "exception" | "operations" | "money" | "none";
};

export function nextActionFor(detail: OrderDetail): NextAction {
  const state = detail.state;
  if (["DISPATCH_READY", "BOOKED", "DRIVER_REJECTED"].includes(state)) {
    return {
      key: "assign",
      label: "Assign driver",
      hint: "PC-owned · syncs via permanent bond",
      kind: "assign",
    };
  }
  if (state === "DRIVER_ASSIGNED") {
    return {
      key: "operations",
      label: "Watch on Operations",
      hint: "Accept → pickup → deliver mirrors via Fleetbase bond",
      kind: "operations",
    };
  }
  if (
    [
      "DRIVER_ACCEPTED",
      "DRIVER_EN_ROUTE",
      "AT_PICKUP",
      "PICKED_UP",
      "IN_TRANSIT",
      "AT_DESTINATION",
    ].includes(state)
  ) {
    return {
      key: "operations",
      label: "Open Operations",
      hint: "Live progress mirrors via permanent bond",
      kind: "operations",
    };
  }
  if (state === "POD_COMPLETED" && !detail.invoice_number) {
    return {
      key: "money",
      label: "Generate invoice",
      hint: "POD complete — create invoice + receipt email",
      kind: "money",
    };
  }
  if (["DELIVERED", "POD_COMPLETED", "INVOICED"].includes(state) && detail.invoice_number) {
    return {
      key: "money",
      label: "View money",
      hint: "Invoice on file — resend receipt from full Order 360",
      kind: "money",
    };
  }
  if (["FAILED", "RETURN_TO_SENDER", "LOST", "DAMAGED"].includes(state)) {
    return {
      key: "exception",
      label: "Review exception",
      hint: "Update exception or retry from Exceptions tab",
      kind: "exception",
    };
  }
  return {
    key: "none",
    label: "No action needed",
    hint: titleCase(detail.display_state || detail.state),
    kind: "none",
  };
}
