"use client";

import { useMemo } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { formatCents } from "@porterchain/ui/utils";
import {
  exportCsv,
  PAYMENT_STATUS_STYLES,
  STATE_STYLES,
  type BookingDraftRow,
} from "@/lib/booking-drafts";
import { Badge } from "@/components/crm/primitives";
import DeleteButton from "@/components/common/DeleteButton";
import SelectableGrid from "@/components/common/SelectableGrid";

const VIEWS_KEY = "porterchain.booking-drafts.views";
const COLS_KEY = "porterchain.booking-drafts.columns";

const COLUMN_LABELS: Record<string, string> = {
  select: "Select",
  draft_number: "Draft #",
  display_state: "Status",
  customer_email: "Customer",
  merchant_name: "Merchant",
  booking_type: "Type",
  vehicle_class: "Vehicle",
  amount_cents: "Amount",
  payment_status: "Payment",
  current_step: "Step",
  created_at: "Created",
  updated_at: "Updated",
  expires_at: "Expires",
  actions: "Actions",
};

type Props = {
  rows: BookingDraftRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
  loading?: boolean;
};

const rowLabel = (r: BookingDraftRow) => r.draft_number;
const draftId = (r: BookingDraftRow) => r.draft_id;
const GROUP_OPTIONS = [
  { value: "display_state", label: "Group by status" },
  { value: "booking_type", label: "Group by type" },
];

export default function BookingDraftsGrid({ rows, selected, onSelect, loading }: Props) {
  const columns = useMemo<ColumnDef<BookingDraftRow>[]>(
    () => [
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
      {
        id: "delete",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <DeleteButton compact entity="booking_draft" id={row.original.draft_id} />
        ),
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
      rowId={draftId}
      columnsKey={COLS_KEY}
      groupOptions={GROUP_OPTIONS}
      onExport={() => exportCsv(rows)}
      viewsKey={VIEWS_KEY}
      columnLabels={COLUMN_LABELS}
      loading={loading}
      emptyMessage="No booking drafts match your filters"
    />
  );
}
