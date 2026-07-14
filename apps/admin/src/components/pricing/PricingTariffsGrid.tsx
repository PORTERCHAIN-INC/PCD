"use client";

import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getGroupedRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type ColumnSizingState,
  type GroupingState,
} from "@tanstack/react-table";
import { Download } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { exportTariffsCsv, STATUS_STYLES, type TariffRow } from "@/lib/pricing";
import { Button } from "@/components/crm/primitives";

type Props = {
  rows: TariffRow[];
  onPublish: (id: string) => void;
  /** Parent supplies server-side filters — hide duplicate search row */
  hideToolbar?: boolean;
};

export default function PricingTariffsGrid({ rows, onPublish, hideToolbar = false }: Props) {
  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<TariffRow>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Rule",
        size: 180,
        minSize: 140,
        cell: ({ getValue }) => (
          <span className="block truncate font-medium text-primary" title={String(getValue())}>
            {String(getValue())}
          </span>
        ),
      },
      {
        accessorKey: "tariff_type",
        header: "Type",
        size: 120,
        minSize: 100,
        enableGrouping: true,
        cell: ({ getValue }) => (
          <span className="text-xs capitalize text-muted">
            {String(getValue()).replace(/_/g, " ")}
          </span>
        ),
      },
      {
        accessorKey: "vehicle_class",
        header: "Vehicle",
        size: 100,
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "zone",
        header: "Zone",
        size: 100,
        cell: ({ getValue }) => <span className="text-xs">{String(getValue() || "—")}</span>,
      },
      {
        accessorKey: "merchant_name",
        header: "Merchant",
        size: 140,
        cell: ({ getValue }) => (
          <span className="block max-w-[10rem] truncate text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "base_cents",
        header: "Base",
        size: 88,
        cell: ({ getValue }) => (
          <span className="block text-right tabular-nums">{formatCents(Number(getValue()))}</span>
        ),
      },
      {
        accessorKey: "per_km_cents",
        header: "/km",
        size: 72,
        cell: ({ getValue }) => (
          <span className="block text-right tabular-nums">{formatCents(Number(getValue()))}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 120,
        minSize: 100,
        enableGrouping: true,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span
              className={cn(
                "inline-flex rounded-full px-2 py-0.5 text-xs font-bold capitalize",
                STATUS_STYLES[v] ?? "bg-gray-100 text-gray-700"
              )}
            >
              {v.replace(/_/g, " ")}
            </span>
          );
        },
      },
      {
        accessorKey: "version",
        header: "Ver",
        size: 56,
        cell: ({ getValue }) => (
          <span className="block text-center tabular-nums text-xs text-muted">
            {String(getValue())}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        size: 96,
        enableResizing: false,
        cell: ({ row }) =>
          row.original.status !== "published" ? (
            <div className="flex justify-end">
              <Button
                variant="outline"
                className="!px-2 !py-1 text-xs"
                onClick={() => onPublish(row.original.id)}
              >
                Publish
              </Button>
            </div>
          ) : null,
      },
    ],
    [onPublish]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { grouping, columnSizing, globalFilter },
    onGroupingChange: setGrouping,
    onColumnSizingChange: setColumnSizing,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    columnResizeMode: "onChange",
    enableColumnResizing: true,
    defaultColumn: { minSize: 56 },
  });

  if (!rows.length) {
    return (
      <div className="rounded-xl border border-dashed border-primary/15 px-6 py-12 text-center">
        <p className="text-sm font-medium text-primary">No pricing rules</p>
        <p className="mt-1 text-xs text-muted">Adjust filters or create a new rule.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {!hideToolbar ? (
        <div className="flex flex-wrap gap-2">
          <input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Filter visible rows…"
            className="min-w-[12rem] flex-1 rounded-xl border border-primary/10 px-3 py-2 text-sm"
          />
          <select
            value={grouping[0] ?? ""}
            onChange={(e) => setGrouping(e.target.value ? [e.target.value] : [])}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          >
            <option value="">No grouping</option>
            <option value="tariff_type">Group by type</option>
            <option value="status">Group by status</option>
          </select>
          <Button variant="outline" onClick={() => exportTariffsCsv(rows)}>
            <Download className="h-4 w-4" /> CSV
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <select
            value={grouping[0] ?? ""}
            onChange={(e) => setGrouping(e.target.value ? [e.target.value] : [])}
            className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
            aria-label="Group rules"
          >
            <option value="">No grouping</option>
            <option value="tariff_type">Group by type</option>
            <option value="status">Group by status</option>
          </select>
          <Button variant="outline" onClick={() => exportTariffsCsv(rows)}>
            <Download className="h-4 w-4" /> Export CSV
          </Button>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-primary/10">
        <table className="w-full min-w-[62rem] table-fixed text-left text-sm">
          <thead className="border-b border-primary/10 bg-gray-bg/60">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className={cn(
                      "relative px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted",
                      header.column.id === "base_cents" || header.column.id === "per_km_cents"
                        ? "text-right"
                        : header.column.id === "version"
                          ? "text-center"
                          : "text-left"
                    )}
                    style={{ width: header.getSize() }}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                    {header.column.getCanResize() ? (
                      <div
                        onMouseDown={header.getResizeHandler()}
                        onTouchStart={header.getResizeHandler()}
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize bg-transparent hover:bg-secondary/40"
                      />
                    ) : null}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-primary/5 hover:bg-secondary/[0.04]">
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-3 py-2.5 align-middle"
                    style={{ width: cell.column.getSize() }}
                  >
                    {cell.getIsGrouped() ? (
                      <button
                        type="button"
                        className="flex items-center gap-1.5 text-left font-medium text-primary"
                        onClick={row.getToggleExpandedHandler()}
                      >
                        <span className="text-muted">{row.getIsExpanded() ? "▾" : "▸"}</span>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        <span className="text-xs font-normal text-muted">
                          ({row.subRows.length})
                        </span>
                      </button>
                    ) : cell.getIsAggregated() ? (
                      flexRender(
                        cell.column.columnDef.aggregatedCell ?? cell.column.columnDef.cell,
                        cell.getContext()
                      )
                    ) : cell.getIsPlaceholder() ? null : (
                      flexRender(cell.column.columnDef.cell, cell.getContext())
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-muted">
        {table.getRowModel().rows.length} row{table.getRowModel().rows.length === 1 ? "" : "s"}
        {grouping.length ? " (grouped)" : ""}
      </p>
    </div>
  );
}
