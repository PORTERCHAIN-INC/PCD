"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Check, ChevronDown, Search, X } from "lucide-react";
import { cn } from "@porterchain/ui/utils";

export type Option = { value: string; label: string; hint?: string | number };

function useOutsideClose(onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);
  return ref;
}

/** Modern single-select dropdown with a popover menu. */
export function Dropdown({
  label,
  value,
  options,
  onChange,
  icon,
  allLabel = "All",
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  icon?: ReactNode;
  allLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const ref = useOutsideClose(() => setOpen(false));
  const selected = options.find((o) => o.value === value);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
          value
            ? "border-secondary/40 bg-secondary/5 text-secondary"
            : "border-primary/15 bg-white text-primary/80 hover:bg-gray-bg"
        )}
      >
        {icon}
        <span className="text-muted">{label}:</span>
        <span className="max-w-[140px] truncate">{selected ? selected.label : allLabel}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute z-30 mt-1 max-h-72 w-56 overflow-y-auto rounded-xl border border-primary/10 bg-white p-1 shadow-xl">
          <button
            onClick={() => {
              onChange("");
              setOpen(false);
            }}
            className={cn(
              "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-gray-bg",
              !value && "text-secondary"
            )}
          >
            {allLabel}
            {!value && <Check className="h-4 w-4" />}
          </button>
          {options.map((o) => (
            <button
              key={o.value}
              onClick={() => {
                onChange(o.value);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-gray-bg",
                value === o.value && "text-secondary"
              )}
            >
              <span className="truncate">{o.label}</span>
              <span className="ml-2 flex items-center gap-2">
                {o.hint !== undefined && <span className="text-xs text-muted">{o.hint}</span>}
                {value === o.value && <Check className="h-4 w-4" />}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Searchable combobox for large option lists (e.g. cities). */
export function Combobox({
  label,
  value,
  options,
  onChange,
  placeholder = "Search…",
  icon,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const ref = useOutsideClose(() => setOpen(false));
  const filtered = query
    ? options.filter((o) => o.label.toLowerCase().includes(query.toLowerCase())).slice(0, 60)
    : options.slice(0, 60);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
          value
            ? "border-secondary/40 bg-secondary/5 text-secondary"
            : "border-primary/15 bg-white text-primary/80 hover:bg-gray-bg"
        )}
      >
        {icon}
        <span className="text-muted">{label}:</span>
        <span className="max-w-[140px] truncate">{value || "All"}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute z-30 mt-1 w-64 rounded-xl border border-primary/10 bg-white shadow-xl">
          <div className="relative border-b border-primary/10 p-2">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              className="w-full rounded-lg border border-primary/15 py-1.5 pl-8 pr-2 text-sm outline-none focus:border-secondary"
            />
          </div>
          <div className="max-h-64 overflow-y-auto p-1">
            <button
              onClick={() => {
                onChange("");
                setQuery("");
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-gray-bg",
                !value && "text-secondary"
              )}
            >
              All cities
              {!value && <Check className="h-4 w-4" />}
            </button>
            {filtered.map((o) => (
              <button
                key={o.value}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm hover:bg-gray-bg",
                  value === o.value && "text-secondary"
                )}
              >
                <span className="truncate">{o.label}</span>
                {o.hint !== undefined && <span className="ml-2 text-xs text-muted">{o.hint}</span>}
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="px-3 py-4 text-center text-sm text-muted">No matches</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Horizontal province pills with counts. */
export function ProvincePills({
  provinces,
  value,
  onChange,
}: {
  provinces: Array<{ code: string; count: number }>;
  value: string;
  onChange: (value: string) => void;
}) {
  if (provinces.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        onClick={() => onChange("")}
        className={cn(
          "rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset transition-colors",
          !value
            ? "bg-secondary text-white ring-secondary"
            : "bg-white text-primary/70 ring-primary/15 hover:bg-gray-bg"
        )}
      >
        All provinces
      </button>
      {provinces.map((p) => (
        <button
          key={p.code}
          onClick={() => onChange(value === p.code ? "" : p.code)}
          className={cn(
            "flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset transition-colors",
            value === p.code
              ? "bg-secondary text-white ring-secondary"
              : "bg-white text-primary/70 ring-primary/15 hover:bg-gray-bg"
          )}
        >
          {p.code}
          <span
            className={cn(
              "rounded-full px-1.5 text-[10px]",
              value === p.code ? "bg-white/20" : "bg-gray-bg text-muted"
            )}
          >
            {p.count}
          </span>
        </button>
      ))}
    </div>
  );
}

/** Removable active-filter chip. */
export function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-secondary/10 px-2.5 py-1 text-xs font-medium text-secondary">
      {label}
      <button onClick={onRemove} className="rounded-full p-0.5 hover:bg-secondary/20">
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}
