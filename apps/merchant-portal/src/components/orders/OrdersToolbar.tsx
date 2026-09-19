"use client";

import Button from "@/components/ui/Button";
import { DateRangeField } from "@porterchain/ui/date-fields";
import { invoiceStatusLabel, orderStateLabel } from "@/lib/catalog";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { hasMerchantModule } from "@/lib/merchant-nav";
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
  onPrintPreview: () => void;
  onPrintLabels: () => void;
  onPrintPickupList: () => void;
  onPrintManifest?: () => void;
  printBusy?: boolean;
};

export function OrdersToolbar({
  filters,
  onChange,
  onSearch,
  selectedCount,
  onBulkCancel,
  onBulkDuplicate,
  onExport,
  onPrintPreview,
  onPrintLabels,
  onPrintPickupList,
  onPrintManifest,
  printBusy,
}: Props) {
  const [savedNames] = useState(loadSavedFilterNames);
  const [saveName, setSaveName] = useState("");
  const { modules } = useMerchantAuth();
  const canWriteOrders = hasMerchantModule(modules, "orders_write");
  const canSeeInvoices = hasMerchantModule(modules, "invoices");

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap">
        <input
          type="search"
          placeholder="Order #, tracking, PO, reference…"
          value={filters.search ?? ""}
          onChange={(e) => onChange({ ...filters, search: e.target.value || undefined })}
          className="min-h-10 min-w-0 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:min-w-[220px] sm:flex-1"
        />
        <select
          value={filters.env ?? "live"}
          onChange={(e) =>
            onChange({
              ...filters,
              env: (e.target.value as OrderFilters["env"]) || "live",
            })
          }
          className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-auto"
          aria-label="Order environment"
        >
          <option value="live">Live only</option>
          <option value="sandbox">Test only</option>
          <option value="all">All (live + test)</option>
        </select>
        <select
          value={filters.state ?? ""}
          onChange={(e) => onChange({ ...filters, state: e.target.value || undefined })}
          className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-auto"
        >
          <option value="">All states</option>
          {ORDER_STATES.map((s) => (
            <option key={s} value={s}>
              {orderStateLabel(s)}
            </option>
          ))}
        </select>
        {canSeeInvoices ? (
          <select
            value={filters.invoice_status ?? ""}
            onChange={(e) => onChange({ ...filters, invoice_status: e.target.value || undefined })}
            className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-auto"
          >
            <option value="">Invoice</option>
            <option value="generated">{invoiceStatusLabel("generated")}</option>
            <option value="none">{invoiceStatusLabel("none")}</option>
          </select>
        ) : null}
        <select
          value={filters.priority ?? ""}
          onChange={(e) => onChange({ ...filters, priority: e.target.value || undefined })}
          className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-auto"
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
          className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-28"
        />
        <DateRangeField
          className="w-full sm:max-w-md"
          from={filters.date_from?.slice(0, 10) ?? ""}
          to={filters.date_to?.slice(0, 10) ?? ""}
          onFromChange={(value) => onChange({ ...filters, date_from: value || undefined })}
          onToChange={(value) => onChange({ ...filters, date_to: value || undefined })}
        />
        <Button type="button" size="sm" className="w-full sm:w-auto" onClick={onSearch}>
          Apply
        </Button>
      </div>

      {(filters.env === "sandbox" || filters.env === "all") && (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          {filters.env === "sandbox"
            ? "Showing Test orders only. Printed labels carry a TEST watermark and must not go to live docks."
            : "Showing Live and Test together. Prefer Live only for ops; Test rows are labeled TEST."}
        </p>
      )}

      <div className="grid grid-cols-1 gap-2 sm:flex sm:flex-wrap sm:items-center">
        <select
          className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-auto"
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
          className="min-h-10 w-full rounded-xl border border-primary/15 px-3 py-2 text-sm sm:w-auto"
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-full sm:w-auto"
          onClick={() => {
            if (!saveName.trim()) return;
            saveFilter(saveName.trim(), filters);
            setSaveName("");
          }}
        >
          Save filter
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="w-full sm:w-auto"
          onClick={onExport}
        >
          Export CSV
        </Button>
      </div>

      {selectedCount > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl bg-secondary/5 px-3 py-2">
          <span className="text-sm font-medium">{selectedCount} selected</span>
          {canWriteOrders ? (
            <Button type="button" size="sm" variant="outline" onClick={onBulkCancel}>
              Bulk cancel
            </Button>
          ) : null}
          {canWriteOrders ? (
            <Button type="button" size="sm" variant="outline" onClick={onBulkDuplicate}>
              Bulk duplicate
            </Button>
          ) : null}
          <Button
            type="button"
            size="sm"
            onClick={onPrintLabels}
            disabled={printBusy || selectedCount < 1}
          >
            {printBusy ? "Preparing…" : "Print labels"}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={onPrintPreview}
            disabled={printBusy || selectedCount !== 1}
          >
            {printBusy ? "Preparing…" : "Dock sheet"}
          </Button>
          {canWriteOrders ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onPrintPickupList}
              disabled={printBusy}
            >
              {printBusy ? "Preparing…" : "Print pickup list"}
            </Button>
          ) : null}
          {onPrintManifest ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onPrintManifest}
              disabled={printBusy || selectedCount < 1}
            >
              {printBusy ? "Preparing…" : "Pickup manifest"}
            </Button>
          ) : null}
        </div>
      )}
    </div>
  );
}
