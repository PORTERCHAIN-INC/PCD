"use client";

import Button from "@/components/ui/Button";
import type { OrderFilters } from "@/lib/orders";
import { loadSavedFilter, loadSavedFilterNames, ORDER_STATES, saveFilter } from "@/lib/orders";
import { useState } from "react";

type Props = {
  filters: OrderFilters;
  onChange: (filters: OrderFilters) => void;
  onSearch: () => void;
  selectedCount: number;
  onBulkCancel: () => void;
  onBulkDuplicate: () => void;
  onExport: () => void;
  onPrintLabels: () => void;
  onPrintManifest: () => void;
};

export function OrdersToolbar({
  filters,
  onChange,
  onSearch,
  selectedCount,
  onBulkCancel,
  onBulkDuplicate,
  onExport,
  onPrintLabels,
  onPrintManifest,
}: Props) {
  const [savedNames] = useState(loadSavedFilterNames);
  const [saveName, setSaveName] = useState("");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <input
          type="search"
          placeholder="Order #, tracking, PO, reference…"
          value={filters.search ?? ""}
          onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
          className="min-w-[220px] flex-1 rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
        <select
          value={filters.state ?? ""}
          onChange={(e) => onChange({ ...filters, state: e.target.value || undefined })}
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
        >
          <option value="">All states</option>
          {ORDER_STATES.map((s) => (
            <option key={s} value={s}>
              {s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <select
          value={filters.invoice_status ?? ""}
          onChange={(e) => onChange({ ...filters, invoice_status: e.target.value || undefined })}
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
        >
          <option value="">Invoice</option>
          <option value="generated">Generated</option>
          <option value="none">None</option>
        </select>
        <select
          value={filters.priority ?? ""}
          onChange={(e) => onChange({ ...filters, priority: e.target.value || undefined })}
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
        >
          <option value="">Priority</option>
          <option value="normal">Normal</option>
          <option value="high">High</option>
        </select>
        <input
          type="text"
          placeholder="City"
          value={filters.city ?? ""}
          onChange={(e) => onChange({ ...filters, city: e.target.value || undefined })}
          className="w-28 rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
        <input
          type="date"
          value={filters.date_from?.slice(0, 10) ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              date_from: e.target.value ? `${e.target.value}T00:00:00Z` : undefined,
            })
          }
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
        <input
          type="date"
          value={filters.date_to?.slice(0, 10) ?? ""}
          onChange={(e) =>
            onChange({
              ...filters,
              date_to: e.target.value ? `${e.target.value}T23:59:59Z` : undefined,
            })
          }
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
        <Button type="button" size="sm" onClick={onSearch}>
          Apply
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          defaultValue=""
          onChange={(e) => {
            const name = e.target.value;
            if (!name) return;
            const saved = loadSavedFilter(name);
            if (saved) onChange(saved);
            e.target.value = "";
          }}
        >
          <option value="">Saved filters…</option>
          {savedNames.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Filter name"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => {
            if (!saveName.trim()) return;
            saveFilter(saveName.trim(), filters);
            setSaveName("");
          }}
        >
          Save filter
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={onExport}>
          Export CSV
        </Button>
      </div>

      {selectedCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-secondary/5 px-3 py-2">
          <span className="text-sm font-medium">{selectedCount} selected</span>
          <Button type="button" size="sm" variant="outline" onClick={onBulkCancel}>
            Bulk cancel
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={onBulkDuplicate}>
            Bulk duplicate
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={onPrintLabels}>
            Print labels
          </Button>
          <Button type="button" size="sm" variant="outline" onClick={onPrintManifest}>
            Print manifest
          </Button>
        </div>
      )}
    </div>
  );
}
