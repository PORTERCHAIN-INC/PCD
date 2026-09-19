"use client";

import { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import { cn, formatCents } from "@porterchain/ui/utils";
import { PAYMENT_STATUS_STYLES, type PaymentRow } from "@/lib/finance";

type Props = { rows: PaymentRow[] };

export default function FinancePaymentsGrid({ rows }: Props) {
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<PaymentRow>[]>(
    () => [
      {
        accessorKey: "payment_reference",
        header: "Reference",
        size: 120,
        cell: ({ row }) => (
          <span className="font-mono text-xs">
            {row.original.payment_reference || row.original.payment_id.slice(0, 8)}
          </span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 100,
        cell: ({ getValue }) => {
          const v = String(getValue());
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
      { accessorKey: "payment_method", header: "Method", size: 90 },
      {
        accessorKey: "amount_cents",
        header: "Amount",
        size: 90,
        cell: ({ getValue }) => formatCents(Number(getValue())),
      },
      {
        accessorKey: "order_number",
        header: "Order",
        size: 100,
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
        accessorKey: "stripe_payment_intent_id",
        header: "Stripe PI",
        size: 140,
        cell: ({ getValue }) => (
          <span className="truncate font-mono text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "created_at",
        header: "Date",
        size: 110,
        cell: ({ getValue }) => String(getValue()).slice(0, 16).replace("T", " "),
      },
    ],
    []
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  return (
    <div className="space-y-3">
      <input
        value={globalFilter}
        onChange={(e) => setGlobalFilter(e.target.value)}
        placeholder="Filter payments…"
        className="w-full max-w-sm rounded-xl border border-primary/10 px-3 py-2 text-sm"
      />
      {!rows.length ? (
        <div className="rounded-xl border border-dashed border-primary/15 px-6 py-12 text-center">
          <p className="text-sm font-medium text-primary">No payments</p>
          <p className="mt-1 text-xs text-muted">Stripe and offline payments will list here.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-primary/10">
          <table className="w-full min-w-[48rem] text-left text-sm">
            <thead className="border-b border-primary/10 bg-gray-bg/60">
              {table.getHeaderGroups().map((hg) => (
                <tr key={hg.id}>
                  {hg.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-muted"
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="border-b border-primary/5 hover:bg-secondary/[0.04]">
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
      )}
    </div>
  );
}
