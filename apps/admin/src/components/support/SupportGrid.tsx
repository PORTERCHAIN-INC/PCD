"use client";

import { useMemo } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";
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
import DeleteButton from "@/components/common/DeleteButton";
import SelectableGrid from "@/components/common/SelectableGrid";

const COLS_KEY = "porterchain.support.columns";

type Props = {
  rows: TicketRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
};

const rowLabel = (r: TicketRow) => r.ticket_number;
const GROUP_OPTIONS = [
  { value: "display_status", label: "Group by status" },
  { value: "category", label: "Group by category" },
  { value: "priority", label: "Group by priority" },
];

export default function SupportGrid({ rows, selected, onSelect }: Props) {
  const columns = useMemo<ColumnDef<TicketRow>[]>(
    () => [
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
        cell: ({ getValue }) => (
          <span className="text-xs capitalize">{formatCategory(String(getValue()))}</span>
        ),
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
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-bold",
                STATUS_STYLES[v] ?? "bg-gray-100"
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
        size: 150,
        cell: ({ getValue }) => (
          <span className="truncate text-xs">{String(getValue() || "—")}</span>
        ),
      },
      {
        accessorKey: "merchant_name",
        header: "Merchant",
        size: 120,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "driver_name",
        header: "Driver",
        size: 110,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "order_number",
        header: "Order",
        size: 100,
        cell: ({ row, getValue }) =>
          row.original.order_id ? (
            <Link
              href={`/orders/${row.original.order_id}`}
              className="font-mono text-xs text-secondary hover:underline"
            >
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
        accessorKey: "assigned_agent",
        header: "Agent",
        size: 120,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
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
        id: "actions",
        header: "",
        size: 50,
        cell: ({ row }) => (
          <Link href={`/support/${row.original.id}`} className="text-secondary">
            <ExternalLink className="h-4 w-4" />
          </Link>
        ),
      },
      {
        id: "delete",
        header: "",
        enableSorting: false,
        cell: ({ row }) => <DeleteButton compact entity="support_ticket" id={row.original.id} />,
      },
    ],
    []
  );

  return (
    <SelectableGrid
      rows={rows}
      columns={columns}
      selected={selected}
      onSelect={onSelect}
      rowLabel={rowLabel}
      columnsKey={COLS_KEY}
      groupOptions={GROUP_OPTIONS}
      onExport={() => exportTicketsCsv(rows)}
      exportLabel="CSV export"
    />
  );
}
