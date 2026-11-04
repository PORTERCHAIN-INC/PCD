"use client";

import { useDeferredValue, useMemo, useState } from "react";
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
  type VisibilityState,
} from "@tanstack/react-table";
import { Download } from "lucide-react";
import { Button } from "@/components/crm/primitives";
import { SavedPresetsControl } from "@/components/crm/SavedPresetsControl";
import { PageSkeleton } from "@porterchain/ui/loading";

export type SelectableGridProps<T> = {
  rows: T[];
  /** Data columns; the checkbox column is added in front. */
  columns: ColumnDef<T>[];
  selected: string[];
  onSelect: (ids: string[]) => void;
  /** Accessible label for a row checkbox. */
  rowLabel: (row: T) => string;
  /** Selection id for a row (defaults to `row.id`). */
  rowId?: (row: T) => string;
  /** localStorage key for column visibility. */
  columnsKey: string;
  groupOptions: Array<{ value: string; label: string }>;
  onExport: () => void;
  exportLabel?: string;
  /** Show the Columns picker + saved column views (stored under this key). */
  viewsKey?: string;
  columnLabels?: Record<string, string>;
  loading?: boolean;
  emptyMessage?: string;
};

const defaultRowId = (row: unknown) => (row as { id: string }).id;

function loadVisibility(key: string): VisibilityState {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(key) || "{}") as VisibilityState;
  } catch {
    return {};
  }
}

/** Admin list grid: select, filter, group, resize, persisted column visibility, CSV. */
export default function SelectableGrid<T>({
  rows,
  columns: dataColumns,
  selected,
  onSelect,
  rowLabel,
  rowId = defaultRowId,
  columnsKey,
  groupOptions,
  onExport,
  exportLabel = "CSV",
  viewsKey,
  columnLabels,
  loading,
  emptyMessage,
}: SelectableGridProps<T>) {
  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(() =>
    loadVisibility(columnsKey)
  );
  const [globalFilter, setGlobalFilter] = useState("");
  const deferredFilter = useDeferredValue(globalFilter);

  const columns = useMemo<ColumnDef<T>[]>(
    () => [
      {
        id: "select",
        size: 40,
        header: ({ table }) => {
          const ids = table
            .getFilteredRowModel()
            .rows.filter((r) => !r.getIsGrouped())
            .map((r) => rowId(r.original))
            .filter(Boolean);
          const allSelected = ids.length > 0 && ids.every((id) => selected.includes(id));
          const someSelected = ids.some((id) => selected.includes(id));
          return (
            <input
              type="checkbox"
              checked={allSelected}
              ref={(el) => {
                if (el) el.indeterminate = someSelected && !allSelected;
              }}
              onChange={(e) => {
                if (e.target.checked) {
                  onSelect([...new Set([...selected, ...ids])]);
                } else {
                  const drop = new Set(ids);
                  onSelect(selected.filter((id) => !drop.has(id)));
                }
              }}
              aria-label="Select all"
            />
          );
        },
        cell: ({ row }) =>
          row.getIsGrouped() ? null : (
            <input
              type="checkbox"
              checked={selected.includes(rowId(row.original))}
              onChange={(e) => {
                const id = rowId(row.original);
                onSelect(e.target.checked ? [...selected, id] : selected.filter((x) => x !== id));
              }}
              aria-label={`Select ${rowLabel(row.original)}`}
            />
          ),
      },
      ...dataColumns,
    ],
    [dataColumns, selected, onSelect, rowLabel, rowId]
  );

  const saveVisibility = (next: VisibilityState) => {
    localStorage.setItem(columnsKey, JSON.stringify(next));
    return next;
  };

  const table = useReactTable({
    data: rows,
    columns,
    state: { grouping, columnSizing, columnVisibility, globalFilter: deferredFilter },
    onGroupingChange: setGrouping,
    onColumnSizingChange: setColumnSizing,
    onColumnVisibilityChange: (updater) =>
      setColumnVisibility((prev) =>
        saveVisibility(typeof updater === "function" ? updater(prev) : updater)
      ),
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    columnResizeMode: "onChange",
    enableColumnResizing: true,
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Filter grid…"
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        />
        <select
          value={grouping[0] ?? ""}
          onChange={(e) => setGrouping(e.target.value ? [e.target.value] : [])}
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        >
          <option value="">No grouping</option>
          {groupOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        {viewsKey ? (
          <>
            <details className="relative">
              <summary className="cursor-pointer rounded-xl border border-primary/10 px-3 py-2 text-sm">
                Columns
              </summary>
              <div className="absolute z-20 mt-1 max-h-64 overflow-auto rounded-xl border border-primary/10 bg-white p-3 shadow-lg">
                {table.getAllLeafColumns().map((col) => (
                  <label key={col.id} className="flex items-center gap-2 py-1 text-sm">
                    <input
                      type="checkbox"
                      checked={col.getIsVisible()}
                      onChange={col.getToggleVisibilityHandler()}
                    />
                    {columnLabels?.[col.id] ?? col.id.replace(/_/g, " ")}
                  </label>
                ))}
              </div>
            </details>
            <SavedPresetsControl
              storageKey={viewsKey}
              value={columnVisibility}
              onLoad={(next) => setColumnVisibility(saveVisibility(next))}
              label="Column views"
            />
          </>
        ) : null}
        <Button variant="outline" onClick={onExport}>
          <Download className="h-4 w-4" />
          {exportLabel}
        </Button>
      </div>

      <div className="min-w-0 overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        {loading ? (
          <div className="p-6">
            <PageSkeleton rows={5} />
          </div>
        ) : (
          <table
            className="w-full min-w-full text-left text-sm"
            style={{ minWidth: Math.max(table.getCenterTotalSize(), 960) }}
          >
            <thead className="border-b border-primary/10 bg-gray-bg/50">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="relative px-3 py-3 font-medium"
                      style={{ width: header.getSize() }}
                    >
                      {header.isPlaceholder
                        ? null
                        : flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanResize() && (
                        <div
                          onMouseDown={header.getResizeHandler()}
                          onTouchStart={header.getResizeHandler()}
                          className="absolute right-0 top-0 h-full w-1 cursor-col-resize bg-primary/10 hover:bg-secondary/40"
                        />
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-b border-primary/5 hover:bg-secondary/5">
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="px-3 py-2.5"
                      style={{ width: cell.column.getSize() }}
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
              {!rows.length && emptyMessage ? (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                    {emptyMessage}
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
