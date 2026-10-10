"use client";

import { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { ops, type OpsSearchResult } from "@/lib/operations";
import { titleCase } from "@/lib/crmFormat";

/** Dispatch sections reachable from the palette (⌘K). */
const VIEW_JUMPS: { id: string; label: string; href: string }[] = [
  { id: "today", label: "Today", href: "/dispatch/today" },
  { id: "queue", label: "Unassigned queue", href: "/dispatch/today" },
  { id: "board", label: "Board", href: "/dispatch/today" },
  { id: "plan", label: "Plan the day", href: "/dispatch/plan" },
  { id: "optimize", label: "Optimize route", href: "/dispatch/plan" },
  { id: "scheduled", label: "Scheduled batches", href: "/dispatch/plan" },
  { id: "copilot", label: "Copilot", href: "/dispatch/plan" },
  { id: "live", label: "Live map + ETA", href: "/dispatch/live" },
  { id: "map", label: "Live map", href: "/dispatch/live" },
  { id: "exceptions", label: "Exceptions", href: "/dispatch/exceptions" },
  { id: "sla", label: "Late / at risk", href: "/dispatch/exceptions" },
  { id: "orders", label: "Orders", href: "/orders" },
  { id: "fleet", label: "Fleet + capacity", href: "/dispatch/fleet" },
  { id: "drivers", label: "Drivers", href: "/dispatch/fleet" },
  { id: "metrics", label: "Metrics", href: "/dispatch/metrics" },
];

export function OpsCommandPalette({
  onOpenOrder,
  onJumpView,
}: {
  onOpenOrder: (id: string) => void;
  onJumpView?: (href: string) => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<OpsSearchResult | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open || q.trim().length < 1) {
      setResults(null);
      return;
    }
    const handle = window.setTimeout(() => {
      void (async () => {
        setBusy(true);
        try {
          const token = await getApiToken();
          setResults(await ops.search(token, q.trim()));
        } catch {
          setResults({ q, orders: [], drivers: [] });
        } finally {
          setBusy(false);
        }
      })();
    }, 180);
    return () => window.clearTimeout(handle);
  }, [q, open, getApiToken]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-primary/30 px-4 pt-[12vh] backdrop-blur-sm">
      <div className="absolute inset-0" onClick={() => setOpen(false)} aria-hidden />
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center gap-2 border-b border-primary/10 px-4 py-3">
          <Search className="h-4 w-4 text-muted" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Jump to order, driver, or settings…"
            className="w-full bg-transparent text-sm text-primary outline-none placeholder:text-muted"
          />
          <kbd className="rounded border border-primary/15 px-1.5 py-0.5 text-[10px] text-muted">
            esc
          </kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {q.trim().length > 0 &&
            onJumpView &&
            VIEW_JUMPS.some(
              (j) =>
                j.id.includes(q.trim().toLowerCase()) ||
                j.label.toLowerCase().includes(q.trim().toLowerCase())
            ) && (
              <div className="mb-2">
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Dispatch
                </p>
                {VIEW_JUMPS.filter(
                  (j) =>
                    j.id.includes(q.trim().toLowerCase()) ||
                    j.label.toLowerCase().includes(q.trim().toLowerCase())
                )
                  .filter((j, i, arr) => arr.findIndex((x) => x.href === j.href) === i)
                  .map((j) => (
                    <button
                      key={`${j.href}-${j.id}`}
                      type="button"
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm hover:bg-gray-bg"
                      onClick={() => {
                        onJumpView(j.href);
                        setOpen(false);
                        setQ("");
                      }}
                    >
                      <span className="font-medium text-primary">{j.label}</span>
                      <span className="text-xs text-muted">Jump</span>
                    </button>
                  ))}
              </div>
            )}
          {q.trim().length > 0 &&
            ["pricing", "vehicles", "booking", "users", "dispatch", "settings"].some(
              (k) => k.includes(q.trim().toLowerCase()) || q.trim().toLowerCase().includes(k)
            ) && (
              <div className="mb-2">
                <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
                  Settings
                </p>
                {(
                  [
                    ["pricing", "Pricing"],
                    ["vehicles", "Vehicle classes"],
                    ["booking", "Booking / SLA"],
                    ["users", "Users"],
                    ["dispatch", "Dispatch"],
                  ] as const
                )
                  .filter(
                    ([id, label]) =>
                      id.includes(q.trim().toLowerCase()) ||
                      label.toLowerCase().includes(q.trim().toLowerCase()) ||
                      "settings".includes(q.trim().toLowerCase())
                  )
                  .map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm hover:bg-gray-bg"
                      onClick={() => {
                        window.location.href = `/settings?section=${id}`;
                        setOpen(false);
                        setQ("");
                      }}
                    >
                      <span className="font-medium text-primary">{label}</span>
                      <span className="text-xs text-muted">Settings</span>
                    </button>
                  ))}
              </div>
            )}
          {busy && <p className="px-3 py-2 text-xs text-muted">Searching…</p>}
          {!busy && results && (
            <>
              {results.orders.length > 0 && (
                <div className="mb-2">
                  <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Orders
                  </p>
                  {results.orders.map((o) => (
                    <button
                      key={o.id}
                      type="button"
                      className="flex w-full items-center justify-between rounded-xl px-3 py-2 text-left text-sm hover:bg-gray-bg"
                      onClick={() => {
                        onOpenOrder(o.id);
                        setOpen(false);
                        setQ("");
                      }}
                    >
                      <span className="font-mono font-medium text-primary">
                        {o.tracking_number}
                      </span>
                      <span className="text-xs text-muted">{titleCase(o.state)}</span>
                    </button>
                  ))}
                </div>
              )}
              {results.drivers.length > 0 && (
                <div>
                  <p className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Drivers
                  </p>
                  {results.drivers.map((d) => (
                    <div
                      key={d.id}
                      className="flex items-center justify-between rounded-xl px-3 py-2 text-sm"
                    >
                      <span className="text-primary">{d.name}</span>
                      <span className="text-xs text-muted">{d.online ? "Online" : "Offline"}</span>
                    </div>
                  ))}
                </div>
              )}
              {!results.orders.length && !results.drivers.length && (
                <p className="px-3 py-4 text-center text-sm text-muted">No matches</p>
              )}
            </>
          )}
          {!busy && !results && (
            <p className="px-3 py-4 text-center text-sm text-muted">
              Type a tracking number, order id, or driver name
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
