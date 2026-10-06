"use client";

import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { PageSkeleton } from "@porterchain/ui/loading";
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
import { cn, formatCents } from "@porterchain/ui/utils";
import {
  exportOrdersCsv,
  formatState,
  PAYMENT_STYLES,
  SLA_STYLES,
  STATE_STYLES,
  type OrderRow,
} from "@/lib/orders";
import { Button } from "@/components/crm/primitives";

const COLS_KEY = "porterchain.orders.columns";

type Props = {
  rows: OrderRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
  loading?: boolean;
};

function selectionKey(ids: string[]): string {
  return ids.slice().sort().join("\0");
}

/**
 * TanStack Table can queue row-selection sync during first construction.
 * Defer the table until after mount so React 19 does not warn that OrdersPage
 * updated before it committed (same pattern as FinanceInvoicesGrid).
 */
export default function OrdersGrid(props: Props) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setReady(true);
  }, []);

  if (!ready) {
    return (
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        <div className="flex justify-center py-12">
          <PageSkeleton rows={3} />
        </div>
      </div>
    );
  }

  return <OrdersGridTable {...props} />;
}

function OrdersGridTable({ rows, selected, onSelect, loading }: Props) {
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const mounted = useRef(false);

  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [globalFilter, setGlobalFilter] = useState("");
  const deferredFilter = useDeferredValue(globalFilter);
  const [rowSelection, setRowSelection] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(selected.map((id) => [id, true]))
  );
  const lastEmittedKey = useRef(selectionKey(selected));

  useEffect(() => {
    mounted.current = true;
    try {
      const raw = localStorage.getItem(COLS_KEY);
      if (raw) setColumnVisibility(JSON.parse(raw) as VisibilityState);
    } catch {
      /* saved columns are optional */
    }
    return () => {
      mounted.current = false;
    };
  }, []);

  // Parent cleared or replaced selection (filters / page change).
  useEffect(() => {
    const key = selectionKey(selected);
    if (key === lastEmittedKey.current) return;
    lastEmittedKey.current = key;
    setRowSelection(Object.fromEntries(selected.map((id) => [id, true])));
  }, [selected]);

  // Push local checkbox changes to the parent after this grid has mounted.
  useEffect(() => {
    if (!mounted.current) return;
    const ids = Object.keys(rowSelection).filter((id) => rowSelection[id]);
    const key = selectionKey(ids);
    if (key === lastEmittedKey.current) return;
    lastEmittedKey.current = key;
    onSelectRef.current(ids);
  }, [rowSelection]);

  const applyRowSelection = (
    updater: Record<string, boolean> | ((prev: Record<string, boolean>) => Record<string, boolean>)
  ) => {
    if (!mounted.current) return;
    setRowSelection(updater);
  };

  const columns = useMemo<ColumnDef<OrderRow>[]>(
    () => [
      {
        id: "select",
        size: 40,
        header: ({ table }) => {
          const all = table.getIsAllPageRowsSelected();
          const some = table.getIsSomePageRowsSelected();
          return (
            <input
              type="checkbox"
              checked={all}
              ref={(el) => {
                if (el) el.indeterminate = some && !all;
              }}
              onChange={table.getToggleAllPageRowsSelectedHandler()}
              aria-label="Select all"
            />
          );
        },
        cell: ({ row }) => (
          <input
            type="checkbox"
            checked={row.getIsSelected()}
            disabled={!row.getCanSelect()}
            onChange={row.getToggleSelectedHandler()}
            aria-label="Select row"
          />
        ),
      },
      {
        accessorKey: "order_number",
        header: "Order #",
        size: 110,
        cell: ({ row }) => (
          <Link
            href={`/orders/${row.original.order_id}`}
            className="font-mono text-xs font-semibold text-secondary hover:underline"
          >
            {row.original.order_number}
          </Link>
        ),
      },
      {
        accessorKey: "tracking_number",
        header: "Tracking",
        size: 120,
        cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue())}</span>,
      },
      {
        accessorKey: "booking_number",
        header: "Booking",
        size: 100,
        cell: ({ getValue }) => (
          <span className="font-mono text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "merchant_name",
        header: "Merchant",
        size: 130,
        enableGrouping: true,
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
        accessorKey: "driver_name",
        header: "Driver",
        size: 120,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "vehicle_label",
        header: "Vehicle",
        size: 120,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "pickup",
        header: "Pickup",
        size: 140,
        cell: ({ getValue }) => <span className="truncate text-xs">{String(getValue())}</span>,
      },
      {
        accessorKey: "destination",
        header: "Destination",
        size: 140,
        cell: ({ getValue }) => <span className="truncate text-xs">{String(getValue())}</span>,
      },
      {
        accessorKey: "service_type",
        header: "Service",
        size: 90,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "priority",
        header: "Priority",
        size: 80,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold capitalize",
                v === "high" ? "bg-amber-100 text-amber-800" : "bg-gray-100 text-gray-600"
              )}
            >
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "state",
        header: "Status",
        size: 130,
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
              {formatState(v)}
            </span>
          );
        },
      },
      {
        accessorKey: "payment_status",
        header: "Payment",
        size: 100,
        cell: ({ getValue }) => {
          const v = String(getValue() || "—");
          if (v === "—") return v;
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold",
                PAYMENT_STYLES[v] ?? "bg-gray-100"
              )}
            >
              {v}
            </span>
          );
        },
      },
      {
        accessorKey: "invoice_status",
        header: "Invoice",
        size: 90,
        cell: ({ getValue }) => String(getValue()),
      },
      {
        accessorKey: "amount_cents",
        header: "Amount",
        size: 90,
        cell: ({ getValue }) => formatCents(Number(getValue())),
      },
      {
        accessorKey: "eta",
        header: "ETA",
        size: 120,
        cell: ({ getValue }) => {
          const v = getValue();
          return v ? String(v).slice(0, 16).replace("T", " ") : "—";
        },
      },
      {
        accessorKey: "sla_status",
        header: "SLA",
        size: 80,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return (
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold capitalize",
                SLA_STYLES[v] ?? "bg-gray-100"
              )}
            >
              {v}
            </span>
          );
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
          <Link href={`/orders/${row.original.order_id}`} className="text-secondary">
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
    state: { grouping, columnSizing, columnVisibility, globalFilter: deferredFilter, rowSelection },
    enableRowSelection: true,
    // Parent clears selection on filter/page change. Auto-reset runs during render
    // and would call setState before this grid has mounted.
    // TanStack Table supports this; some pin typings omit it.
    ...({ autoResetRowSelection: false } as object),
    getRowId: (row) => row.order_id,
    onRowSelectionChange: applyRowSelection,
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
    columnResizeMode: "onEnd",
    enableColumnResizing: true,
  });

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <input
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          placeholder="Narrow this page…"
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
          title="Client filter on the current page only — use server filters above for the full result set"
        />
        <select
          value={grouping[0] ?? ""}
          onChange={(e) => setGrouping(e.target.value ? [e.target.value] : [])}
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        >
          <option value="">No grouping</option>
          <option value="state">Group by status</option>
          <option value="merchant_name">Group by merchant</option>
          <option value="payment_status">Group by payment</option>
        </select>
        <Button
          variant="outline"
          onClick={() => exportOrdersCsv(rows)}
          title="Exports the current page only"
        >
          <Download className="h-4 w-4" />
          Export this page
        </Button>
      </div>
      <div className="overflow-x-auto rounded-2xl border border-primary/10 bg-white">
        {loading ? (
          <div className="flex justify-center py-12">
            <PageSkeleton rows={3} />
          </div>
        ) : (
          <table
            className="min-w-full text-left text-sm"
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
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
