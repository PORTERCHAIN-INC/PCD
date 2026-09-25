"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
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
import { Download, ExternalLink } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { formatCents } from "@porterchain/ui/utils";
import {
  exportCsv,
  PAYMENT_STATUS_STYLES,
  STATE_STYLES,
  type BookingDraftRow,
} from "@/lib/booking-drafts";
import { Badge, Button } from "@/components/crm/primitives";

const VIEWS_KEY = "porterchain.booking-drafts.views";
const COLS_KEY = "porterchain.booking-drafts.columns";

type Props = {
  rows: BookingDraftRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
  loading?: boolean;
};

export default function BookingDraftsGrid({ rows, selected, onSelect, loading }: Props) {
  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem(COLS_KEY) || "{}") as VisibilityState;
    } catch {
      return {};
    }
  });
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<BookingDraftRow>[]>(
    () => [
      {
        id: "select",
        size: 40,
        header: ({ table }) => (
          <input
            type="checkbox"
            checked={table.getIsAllPageRowsSelected()}
            onChange={table.getToggleAllPageRowsSelectedHandler()}
            aria-label="Select all"
          />
        ),
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={selected.includes(row.original.draft_id)}
            onChange={(e) => {
              const id = row.original.draft_id;
              onSelect(e.target.checked ? [...selected, id] : selected.filter((x) => x !== id));
            }}
            aria-label={`Select ${row.original.draft_number}`}
          />
        ),
      },
      {
        accessorKey: "draft_number",
        header: "Draft #",
        size: 120,
        cell: ({ row }) => (
          <Link
            href={`/booking-drafts/${row.original.draft_id}`}
            className="font-mono text-xs font-semibold text-secondary hover:underline"
          >
            {row.original.draft_number}
          </Link>
        ),
      },
      {
        accessorKey: "display_state",
        header: "Status",
        size: 140,
        enableGrouping: true,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold",
                STATE_STYLES[v] ?? "bg-gray-100"
              )}
            >
              {v.replace(/_/g, " ")}
            </span>
          );
        },
      },
      {
        accessorKey: "customer_email",
        header: "Customer",
        size: 180,
        cell: ({ getValue }) => (
          <span className="truncate text-sm">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "merchant_name",
        header: "Merchant",
        size: 140,
        cell: ({ getValue }) => <span className="text-sm">{String(getValue() || "—")}</span>,
      },
      {
        accessorKey: "booking_type",
        header: "Type",
        size: 100,
        enableGrouping: true,
        cell: ({ getValue }) => <Badge tone="slate">{String(getValue())}</Badge>,
      },
      {
        accessorKey: "vehicle_class",
        header: "Vehicle",
        size: 100,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "amount_cents",
        header: "Price",
        size: 90,
        cell: ({ getValue }) => (getValue() != null ? formatCents(Number(getValue())) : "—"),
      },
      {
        accessorKey: "payment_status",
        header: "Payment",
        size: 110,
        cell: ({ getValue }) => {
          const v = getValue() as string | null;
          if (!v) return "—";
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold",
                PAYMENT_STATUS_STYLES[v] ?? "bg-gray-100"
              )}
            >
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "current_step",
        header: "Step",
        size: 100,
      },
      {
        accessorKey: "created_at",
        header: "Created",
        size: 130,
        cell: ({ getValue }) => String(getValue()).slice(0, 16).replace("T", " "),
      },
      {
        accessorKey: "updated_at",
        header: "Updated",
        size: 130,
        cell: ({ getValue }) => String(getValue()).slice(0, 16).replace("T", " "),
      },
      {
        accessorKey: "expires_at",
        header: "Expiry",
        size: 130,
        cell: ({ row, getValue }) => (
          <span className={row.original.is_expired ? "text-orange-600 font-medium" : ""}>
            {String(getValue()).slice(0, 16).replace("T", " ")}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        size: 60,
        cell: ({ row }) => (
          <Link
            href={`/booking-drafts/${row.original.draft_id}`}
            className="text-secondary hover:text-secondary/80"
          >
            <ExternalLink className="h-4 w-4" />
          </Link>
        ),
      },
    ],
    [selected, onSelect]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { grouping, columnSizing, columnVisibility, globalFilter },
    onGroupingChange: setGrouping,
    onColumnSizingChange: setColumnSizing,
    onColumnVisibilityChange: (updater) => {
      setColumnVisibility((prev) => {
        const next = typeof updater === "function" ? updater(prev) : updater;
        localStorage.setItem(COLS_KEY, JSON.stringify(next));
        return next;
      });
    },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getGroupedRowModel: getGroupedRowModel(),
    columnResizeMode: "onChange",
    enableColumnResizing: true,
  });

  function saveView() {
    const name = prompt("View name");
    if (!name) return;
    const views = JSON.parse(localStorage.getItem(VIEWS_KEY) || "{}") as Record<
      string,
      VisibilityState
    >;
    views[name] = columnVisibility;
    localStorage.setItem(VIEWS_KEY, JSON.stringify(views));
  }

  function loadView() {
    const views = JSON.parse(localStorage.getItem(VIEWS_KEY) || "{}") as Record<
      string,
      VisibilityState
    >;
    const names = Object.keys(views);
    if (!names.length) return alert("No saved views");
    const name = prompt(`Load view:\n${names.join("\n")}`);
    if (name && views[name]) setColumnVisibility(views[name]);
  }

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
          <option value="display_state">Group by status</option>
          <option value="booking_type">Group by type</option>
        </select>
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
                {col.id}
              </label>
            ))}
          </div>
        </details>
        <Button variant="outline" onClick={saveView}>
          Save view
        </Button>
        <Button variant="outline" onClick={loadView}>
          Load view
        </Button>
        <Button variant="outline" onClick={() => exportCsv(rows)}>
          <Download className="h-4 w-4" />
          CSV
        </Button>
      </div>

      <div className="min-w-0 overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        {loading ? (
          <p className="p-8 text-center text-sm text-muted">Loading drafts…</p>
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
              {!rows.length && (
                <tr>
                  <td colSpan={columns.length} className="px-4 py-8 text-center text-muted">
                    No booking drafts match your filters
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
