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
} from "@tanstack/react-table";
import { Download, ExternalLink } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { exportInvoicesCsv, INVOICE_STATUS_STYLES, type InvoiceRow } from "@/lib/finance";
import { Button } from "@/components/crm/primitives";

type Props = { rows: InvoiceRow[] };

export default function FinanceInvoicesGrid({ rows }: Props) {
  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<InvoiceRow>[]>(
    () => [
      {
        accessorKey: "invoice_number",
        header: "Invoice #",
        size: 120,
        cell: ({ row }) => (
          <Link
            href={`/finance/invoices/${row.original.invoice_id}`}
            className="font-mono text-xs font-semibold text-secondary hover:underline"
          >
            {row.original.invoice_number}
          </Link>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 110,
        enableGrouping: true,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold capitalize",
                INVOICE_STATUS_STYLES[v] ?? "bg-gray-100"
              )}
            >
              {v.replace(/_/g, " ")}
            </span>
          );
        },
      },
      {
        accessorKey: "merchant_name",
        header: "Merchant",
        size: 130,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "customer_email",
        header: "Customer",
        size: 150,
        cell: ({ getValue }) => (
          <span className="truncate text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "order_number",
        header: "Order",
        size: 100,
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "tracking_number",
        header: "Tracking",
        size: 110,
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "amount_cents",
        header: "Amount",
        size: 90,
        cell: ({ getValue }) => formatCents(Number(getValue())),
      },
      {
        accessorKey: "outstanding_cents",
        header: "Outstanding",
        size: 100,
        cell: ({ getValue }) => {
          const v = Number(getValue());
          return (
            <span className={cn(v > 0 && "font-semibold text-red-600")}>{formatCents(v)}</span>
          );
        },
      },
      { accessorKey: "payment_terms", header: "Terms", size: 90 },
      {
        accessorKey: "created_at",
        header: "Created",
        size: 110,
        cell: ({ getValue }) => String(getValue()).slice(0, 10),
      },
      {
        id: "actions",
        size: 40,
        cell: ({ row }) => (
          <Link href={`/finance/invoices/${row.original.invoice_id}`} className="text-secondary">
            <ExternalLink className="h-4 w-4" />
          </Link>
        ),
      },
    ],
    []
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
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <input
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Filter invoices…"
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        />
        <select
          value={grouping[0] ?? ""}
          onChange={(e) => setGrouping(e.target.value ? [e.target.value] : [])}
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        >
          <option value="">No grouping</option>
          <option value="status">Group by status</option>
          <option value="merchant_name">Group by merchant</option>
        </select>
        <Button variant="outline" onClick={() => exportInvoicesCsv(rows)}>
          <Download className="h-4 w-4" /> CSV
        </Button>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <table className="w-full text-left text-sm" style={{ width: table.getCenterTotalSize() }}>
          <thead className="border-b border-primary/10 bg-gray-bg/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="relative px-3 py-3 font-medium"
                    style={{ width: header.getSize() }}
                  >
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
