"use client";

import { useState, type ReactNode } from "react";
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { ArrowUpDown, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { EmptyState, Spinner } from "@/components/crm/primitives";

export function CrmTable<T>({
  data,
  columns,
  loading,
  onRowClick,
  searchPlaceholder = "Search…",
  toolbar,
  emptyTitle = "No records yet",
  emptyHint,
  pageSize = 12,
}: {
  data: T[] | null;
  columns: ColumnDef<T, unknown>[];
  loading?: boolean;
  onRowClick?: (row: T) => void;
  searchPlaceholder?: string;
  toolbar?: ReactNode;
  emptyTitle?: string;
  emptyHint?: string;
  pageSize?: number;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data: data ?? [],
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  return (
    <div className="rounded-2xl border border-primary/10 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-primary/10 px-4 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-64 rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
          />
        </div>
        <div className="flex items-center gap-2">{toolbar}</div>
      </div>

      {loading ? (
        <Spinner />
      ) : !data || data.length === 0 ? (
        <EmptyState title={emptyTitle} hint={emptyHint} />
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-primary/10 bg-gray-bg/40">
                {table.getHeaderGroups().map((hg) => (
                  <tr key={hg.id}>
                    {hg.headers.map((header) => {
                      const sortable = header.column.getCanSort();
                      return (
                        <th
                          key={header.id}
                          onClick={sortable ? header.column.getToggleSortingHandler() : undefined}
                          className={
                            "whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-muted" +
                            (sortable ? " cursor-pointer select-none" : "")
                          }
                        >
                          <span className="inline-flex items-center gap-1">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {sortable && <ArrowUpDown className="h-3 w-3 opacity-50" />}
                          </span>
                        </th>
                      );
                    })}
                  </tr>
                ))}
              </thead>
              <tbody>
                {table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                    className={
                      "border-b border-primary/5 last:border-0" +
                      (onRowClick ? " cursor-pointer hover:bg-secondary/5" : "")
                    }
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="whitespace-nowrap px-4 py-3 text-primary">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {table.getPageCount() > 1 && (
            <div className="flex items-center justify-between border-t border-primary/10 px-4 py-3 text-sm text-muted">
              <span>
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()} ·{" "}
                {table.getFilteredRowModel().rows.length} records
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                  className="rounded-lg border border-primary/15 p-1.5 disabled:opacity-40"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                  className="rounded-lg border border-primary/15 p-1.5 disabled:opacity-40"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
