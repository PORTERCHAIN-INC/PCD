"use client";

import { useEffect, useState } from "react";
import { cn } from "@porterchain/ui/utils";
import type { LeadFilters } from "@/lib/leads";

type SavedView = { id: string; label: string; filters: LeadFilters; builtin?: boolean };

const STORAGE_KEY = "pc_admin_lead_views_v1";

export const BUILTIN_VIEWS: SavedView[] = [
  { id: "inbox", label: "Inbox", filters: { view: "buyers", sort: "smart" }, builtin: true },
  {
    id: "awaiting",
    label: "Awaiting reply",
    filters: { view: "buyers", awaiting_reply: true, sort: "smart" },
    builtin: true,
  },
  {
    id: "hot",
    label: "Hot (high)",
    filters: { view: "buyers", priority: "high", status: "new", sort: "smart" },
    builtin: true,
  },
  {
    id: "sla",
    label: "SLA breached",
    filters: { view: "buyers", sla_breached: true, sort: "smart" },
    builtin: true,
  },
  {
    id: "unassigned",
    label: "Unassigned",
    filters: { view: "buyers", unassigned: true, sort: "smart" },
    builtin: true,
  },
  {
    id: "whatsapp",
    label: "WhatsApp",
    filters: { view: "buyers", channel: "whatsapp", sort: "smart" },
    builtin: true,
  },
  {
    id: "signups",
    label: "Sign-ups",
    filters: { view: "buyers", tag: "self_serve", sort: "created_at" },
    builtin: true,
  },
  {
    id: "drivers",
    label: "Driver applicants",
    filters: { view: "drivers", sort: "created_at" },
    builtin: true,
  },
];

function readCustom(): SavedView[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as SavedView[]) : [];
    return Array.isArray(parsed) ? parsed.filter((v) => v && v.id && v.label) : [];
  } catch {
    return [];
  }
}

function sameFilters(a: LeadFilters, b: LeadFilters): boolean {
  const clean = (f: LeadFilters) =>
    JSON.stringify(
      Object.fromEntries(
        Object.entries({ ...f, search: undefined, limit: undefined, offset: undefined })
          .filter(([, v]) => v !== undefined && v !== "" && v !== false)
          .sort(([x], [y]) => x.localeCompare(y))
      )
    );
  return clean(a) === clean(b);
}

/** Saved views: one-click inbox filters. Custom views live in this browser. */
export default function LeadSavedViews({
  filters,
  onApply,
}: {
  filters: LeadFilters;
  onApply: (filters: LeadFilters) => void;
}) {
  const [custom, setCustom] = useState<SavedView[]>([]);
  useEffect(() => setCustom(readCustom()), []);

  const persist = (next: SavedView[]) => {
    setCustom(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* private mode — views just won't persist */
    }
  };

  const saveCurrent = () => {
    const label = window.prompt("Name this view")?.trim();
    if (!label) return;
    const rest: LeadFilters = {
      ...filters,
      search: undefined,
      limit: undefined,
      offset: undefined,
    };
    persist([...custom, { id: `v_${Date.now().toString(36)}`, label, filters: rest }]);
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5" role="toolbar" aria-label="Saved views">
      {[...BUILTIN_VIEWS, ...custom].map((v) => {
        const active = sameFilters(filters, v.filters);
        return (
          <span key={v.id} className="inline-flex items-center">
            <button
              type="button"
              onClick={() => onApply({ ...v.filters, search: filters.search })}
              aria-pressed={active}
              className={cn(
                "rounded-full border px-2.5 py-1 text-xs font-medium",
                active
                  ? "border-secondary bg-secondary/10 text-secondary"
                  : v.id === "drivers"
                    ? "border-amber-300 text-amber-800 hover:bg-amber-50"
                    : "border-primary/10 text-muted hover:bg-slate-50"
              )}
            >
              {v.label}
            </button>
            {!v.builtin ? (
              <button
                type="button"
                aria-label={`Delete view ${v.label}`}
                className="ml-0.5 rounded-full px-1 text-xs text-muted hover:text-red-600"
                onClick={() => persist(custom.filter((c) => c.id !== v.id))}
              >
                ×
              </button>
            ) : null}
          </span>
        );
      })}
      <button
        type="button"
        onClick={saveCurrent}
        className="rounded-full border border-dashed border-primary/20 px-2.5 py-1 text-xs font-medium text-secondary hover:bg-slate-50"
      >
        + Save view
      </button>
    </div>
  );
}
