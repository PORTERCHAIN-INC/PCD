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
import {
  exportTicketsCsv,
  formatCategory,
  PRIORITY_STYLES,
  SLA_STYLES,
  STATUS_STYLES,
  type TicketRow,
} from "@/lib/support";
import { relativeTime } from "@/lib/crmFormat";
import { Button } from "@/components/crm/primitives";

const COLS_KEY = "porterchain.support.columns";

type Props = {
  rows: TicketRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
};

export default function SupportGrid({ rows, selected, onSelect }: Props) {
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

  const columns = useMemo<ColumnDef<TicketRow>[]>(
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
            checked={selected.includes(row.original.id)}
            onChange={(e) => {
              const id = row.original.id;
              onSelect(e.target.checked ? [...selected, id] : selected.filter((x) => x !== id));
            }}
          />
        ),
      },
      {
        accessorKey: "ticket_number",
        header: "Ticket #",
        size: 110,
        cell: ({ row }) => (
          <Link
            href={`/support/${row.original.id}`}
            className="font-mono text-xs font-semibold text-secondary hover:underline"
          >
            {row.original.ticket_number}
          </Link>
        ),
      },
      {
        accessorKey: "subject",
        header: "Subject",
        size: 200,
        cell: ({ getValue }) => <span className="line-clamp-2 text-xs">{String(getValue())}</span>,
      },
      {
        accessorKey: "category",
        header: "Category",
        size: 130,
        enableGrouping: true,
        cell: ({ getValue }) => <span className="text-xs capitalize">{formatCategory(String(getValue()))}</span>,
      },
      {
        accessorKey: "priority",
        header: "Priority",
        size: 90,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold capitalize",
                PRIORITY_STYLES[v] ?? PRIORITY_STYLES.normal
              )}
            >
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "display_status",
        header: "Status",
        size: 130,
        enableGrouping: true,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-bold", STATUS_STYLES[v] ?? "bg-gray-100")}>
              {v.replace(/_/g, " ")}
            </span>
          );
        },
      },
      {
        accessorKey: "customer_email",
        header: "Customer",
        size: 150,
        cell: ({ getValue }) => <span className="truncate text-xs">{String(getValue() || "—")}</span>,
      },
      { accessorKey: "merchant_name", header: "Merchant", size: 120, cell: ({ getValue }) => String(getValue() || "—") },
      { accessorKey: "driver_name", header: "Driver", size: 110, cell: ({ getValue }) => String(getValue() || "—") },
      {
        accessorKey: "order_number",
        header: "Order",
        size: 100,
        cell: ({ row, getValue }) =>
          row.original.order_id ? (
            <Link href={`/orders/${row.original.order_id}`} className="font-mono text-xs text-secondary hover:underline">
              {String(getValue() || "—")}
            </Link>
          ) : (
            "—"
          ),
      },
      {
        accessorKey: "booking_number",
        header: "Booking",
        size: 100,
        cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue() || "—")}</span>,
      },
      {
        accessorKey: "tracking_number",
        header: "Tracking",
        size: 110,
        cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue() || "—")}</span>,
      },
      { accessorKey: "assigned_agent", header: "Agent", size: 120, cell: ({ getValue }) => String(getValue() || "—") },
      {
        accessorKey: "created_at",
        header: "Created",
        size: 110,
        cell: ({ getValue }) => relativeTime(String(getValue())),
      },
      {
        accessorKey: "updated_at",
        header: "Updated",
        size: 110,
        cell: ({ getValue }) => relativeTime(String(getValue())),
      },
      {
        accessorKey: "sla_status",
        header: "SLA",
        size: 80,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-bold capitalize", SLA_STYLES[v] ?? "bg-gray-100")}>
              {v}
            </span>
          );
        },
      },
      {
        id: "actions",
        header: "",
        size: 50,
        cell: ({ row }) => (
          <Link href={`/support/${row.original.id}`} className="text-secondary">
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

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
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
          <option value="display_status">Group by status</option>
          <option value="category">Group by category</option>
          <option value="priority">Group by priority</option>
        </select>
        <Button variant="outline" onClick={() => exportTicketsCsv(rows)}>
          <Download className="h-4 w-4" />
          CSV export
        </Button>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm" style={{ width: table.getCenterTotalSize() }}>
          <thead className="border-b border-primary/10 bg-gray-bg/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th key={header.id} className="relative px-3 py-3 font-medium" style={{ width: header.getSize() }}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    <div
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                      className="absolute right-0 top-0 h-full w-1 cursor-col-resize bg-primary/10 hover:bg-secondary/40"
                    />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-primary/5 hover:bg-secondary/5">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2.5">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
