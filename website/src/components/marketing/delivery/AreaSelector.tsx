"use client";

import { useId, useState } from "react";
import { ChevronDown, Search } from "lucide-react";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/utils";
import type { AreaLink, AreaRegion } from "@/lib/seo/area-regions";

/**
 * Compact area picker: region-grouped chips with a filter box. Every chip is a real <a> in the
 * server HTML (crawlable); the filter and the mobile collapse only toggle visibility.
 */
export default function AreaSelector({
  title,
  groups,
  currentSlug,
}: {
  title: string;
  groups: Array<{ region: AreaRegion; links: AreaLink[] }>;
  currentSlug?: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const listId = useId();
  const needle = q.trim().toLowerCase();
  const total = groups.reduce((n, g) => n + g.links.length, 0);

  return (
    <div
      className="rounded-2xl border border-primary/10 bg-white p-4 sm:p-5"
      data-testid="area-selector"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-primary">
          {title} <span className="font-normal text-muted">· {total}</span>
        </h2>
        <div className="flex w-full items-center gap-2 sm:w-auto">
          <label className="flex h-10 min-w-0 flex-1 items-center gap-2 rounded-full border border-primary/10 bg-gray-bg px-3 sm:w-64">
            <Search className="h-4 w-4 shrink-0 text-muted" aria-hidden />
            <span className="sr-only">Filter areas</span>
            <input
              type="search"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                if (e.target.value) setOpen(true);
              }}
              placeholder="Filter areas"
              className="h-10 min-w-0 flex-1 bg-transparent text-sm text-primary outline-none placeholder:text-muted"
            />
          </label>
          <button
            type="button"
            className="inline-flex h-10 items-center gap-1 rounded-full border border-primary/10 px-3 text-sm font-medium text-primary lg:hidden"
            aria-expanded={open}
            aria-controls={listId}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? "Hide" : "Show"}
            <ChevronDown
              className={cn("h-4 w-4 transition-transform", open && "rotate-180")}
              aria-hidden
            />
          </button>
        </div>
      </div>
      <div id={listId} className={cn("mt-4 space-y-3", open ? "block" : "hidden lg:block")}>
        {groups.map((g) => {
          const visible = g.links.filter(
            (l) =>
              !needle ||
              l.label.toLowerCase().includes(needle) ||
              g.region.toLowerCase().includes(needle)
          );
          return (
            <div
              key={g.region}
              className={cn(
                "grid gap-2 sm:grid-cols-[9rem_1fr] sm:items-start",
                !visible.length && "hidden"
              )}
            >
              <p className="pt-1.5 text-xs font-semibold uppercase tracking-wide text-muted">
                {g.region}
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {g.links.map((l) => {
                  const current = l.slug === currentSlug;
                  return (
                    <li key={l.href} className={cn(!visible.includes(l) && "hidden")}>
                      <Link
                        href={l.href}
                        title={l.note}
                        aria-current={current ? "page" : undefined}
                        className={cn(
                          "inline-flex min-h-8 items-center rounded-full border px-3 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary",
                          current
                            ? "border-primary bg-primary font-semibold text-white"
                            : "border-primary/12 bg-white text-primary hover:border-secondary hover:text-secondary"
                        )}
                      >
                        {l.label}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
