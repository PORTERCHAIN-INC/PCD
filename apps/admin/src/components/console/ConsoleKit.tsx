"use client";

import type { ComponentType, ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { downloadCsv, toCsv } from "@/lib/crmFormat";

/** Shared list-console pieces (same look as Customers / Drivers): KPI tile, facet, search, sort, CSV. */
export function StatTile({
  icon: Icon,
  label,
  value,
  accent = "text-secondary",
  active,
  onClick,
}: {
  icon: ComponentType<{ className?: string }>;
  label: string;
  value: string;
  accent?: string;
  active?: boolean;
  onClick?: () => void;
}) {
  const body = (
    <>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-muted">{label}</p>
        <Icon className={`h-4 w-4 ${accent}`} />
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums text-primary">{value}</p>
    </>
  );
  const cls = cn(
    "rounded-2xl border bg-white p-4 text-left",
    active ? "border-secondary/50 ring-1 ring-secondary/30" : "border-primary/10"
  );
  return onClick ? (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(cls, "hover:bg-gray-bg/40")}
    >
      {body}
    </button>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function FacetButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        "rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "border-secondary/40 bg-secondary/5 text-secondary"
          : "border-primary/15 bg-white text-primary/80 hover:bg-gray-bg"
      )}
    >
      {children}
    </button>
  );
}

export function SearchBox({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="relative min-w-[220px] max-w-md flex-1">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
      <input
        type="search"
        aria-label={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm"
      />
    </div>
  );
}

export type Sort<K extends string> = { key: K; dir: "asc" | "desc" };

export function SortHeader<K extends string>({
  label,
  k,
  sort,
  onSort,
  className,
}: {
  label: string;
  k: K;
  sort: Sort<K>;
  onSort: (s: Sort<K>) => void;
  className?: string;
}) {
  const on = sort.key === k;
  const Icon = !on ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <th
      className={cn("px-4 py-2", className)}
      aria-sort={on ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
    >
      <button
        type="button"
        className="inline-flex items-center gap-1 uppercase hover:text-primary"
        onClick={() => onSort({ key: k, dir: on && sort.dir === "asc" ? "desc" : "asc" })}
      >
        {label}
        <Icon className="h-3 w-3" aria-hidden />
      </button>
    </th>
  );
}

export function sortRows<T, K extends string>(
  rows: T[],
  sort: Sort<K>,
  get: (row: T, key: K) => string | number | null | undefined
): T[] {
  const m = sort.dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const x = get(a, sort.key);
    const y = get(b, sort.key);
    if (x == null && y == null) return 0;
    if (x == null) return 1;
    if (y == null) return -1;
    return (
      (typeof x === "number" && typeof y === "number"
        ? x - y
        : String(x).localeCompare(String(y), "en-CA")) * m
    );
  });
}

export function CsvButton({
  filename,
  headers,
  rows,
}: {
  filename: string;
  headers: string[];
  rows: string[][];
}) {
  return (
    <button
      type="button"
      disabled={rows.length === 0}
      onClick={() => downloadCsv(filename, toCsv(headers, rows))}
      className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-white px-3.5 py-2 text-sm font-medium text-primary hover:bg-gray-bg disabled:opacity-50"
    >
      <Download className="h-4 w-4" aria-hidden /> Export CSV
    </button>
  );
}
