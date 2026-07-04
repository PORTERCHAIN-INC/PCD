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
  exportClaimsCsv,
  formatClaimType,
  PRIORITY_STYLES,
  STATUS_STYLES,
  type ClaimRow,
} from "@/lib/claims";
import { Button } from "@/components/crm/primitives";

const COLS_KEY = "porterchain.claims.columns";
const VIEWS_KEY = "porterchain.claims.views";

type Props = {
  rows: ClaimRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
};

export default function ClaimsGrid({ rows, selected, onSelect }: Props) {
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

  const columns = useMemo<ColumnDef<ClaimRow>[]>(
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
        accessorKey: "claim_number",
        header: "Claim #",
        size: 110,
        cell: ({ row }) => (
          <Link href={`/claims/${row.original.id}`} className="font-mono text-xs font-semibold text-secondary hover:underline">
            {row.original.claim_number}
          </Link>
        ),
      },
      {
        accessorKey: "claim_type",
        header: "Type",
        size: 140,
        enableGrouping: true,
        cell: ({ getValue }) => <span className="text-xs">{formatClaimType(String(getValue()))}</span>,
      },
      {
        accessorKey: "priority",
        header: "Priority",
        size: 90,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span className={cn("rounded-full px-2 py-0.5 text-xs font-bold capitalize", PRIORITY_STYLES[v] ?? PRIORITY_STYLES.normal)}>
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "display_status",
        header: "Status",
        size: 140,
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
      { accessorKey: "merchant_name", header: "Merchant", size: 130, cell: ({ getValue }) => String(getValue() || "—") },
      { accessorKey: "customer_email", header: "Customer", size: 160, cell: ({ getValue }) => <span className="truncate text-xs">{String(getValue() || "—")}</span> },
      { accessorKey: "driver_name", header: "Driver", size: 120, cell: ({ getValue }) => String(getValue() || "—") },
      { accessorKey: "tracking_number", header: "Tracking", size: 120, cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue() || "—")}</span> },
      {
        accessorKey: "amount_cents",
        header: "Amount",
        size: 90,
        cell: ({ getValue }) => formatCents(Number(getValue())),
      },
      {
        accessorKey: "has_insurance",
        header: "Insurance",
        size: 80,
        cell: ({ getValue }) => (getValue() ? "Yes" : "—"),
      },
      { accessorKey: "assigned_investigator", header: "Investigator", size: 130, cell: ({ getValue }) => String(getValue() || "—") },
      {
        accessorKey: "risk_score",
        header: "Risk",
        size: 70,
        cell: ({ getValue }) => {
          const v = Number(getValue());
          return <span className={cn("font-bold", v >= 70 ? "text-red-600" : v >= 40 ? "text-amber-600" : "text-green-600")}>{v}</span>;
        },
      },
      {
        accessorKey: "created_at",
        header: "Created",
        size: 120,
        cell: ({ getValue }) => String(getValue()).slice(0, 16).replace("T", " "),
      },
      {
        id: "actions",
        header: "",
        size: 50,
        cell: ({ row }) => (
          <Link href={`/claims/${row.original.id}`} className="text-secondary">
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
          <option value="claim_type">Group by type</option>
        </select>
        <Button variant="outline" onClick={() => exportClaimsCsv(rows)}>
          <Download className="h-4 w-4" />
          CSV
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
