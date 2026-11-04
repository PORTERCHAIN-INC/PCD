"use client";

import { useMemo } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import { ExternalLink } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { formatCents } from "@porterchain/ui/utils";
import {
  exportClaimsCsv,
  formatClaimType,
  PRIORITY_STYLES,
  STATUS_STYLES,
  type ClaimRow,
} from "@/lib/claims";
import DeleteButton from "@/components/common/DeleteButton";
import SelectableGrid from "@/components/common/SelectableGrid";

const COLS_KEY = "porterchain.claims.columns";

type Props = {
  rows: ClaimRow[];
  selected: string[];
  onSelect: (ids: string[]) => void;
};

const rowLabel = (r: ClaimRow) => r.claim_number;
const GROUP_OPTIONS = [
  { value: "display_status", label: "Group by status" },
  { value: "claim_type", label: "Group by type" },
];

export default function ClaimsGrid({ rows, selected, onSelect }: Props) {
  const columns = useMemo<ColumnDef<ClaimRow>[]>(
    () => [
      {
        accessorKey: "claim_number",
        header: "Claim #",
        size: 110,
        cell: ({ row }) => (
          <Link
            href={`/claims/${row.original.id}`}
            className="font-mono text-xs font-semibold text-secondary hover:underline"
          >
            {row.original.claim_number}
          </Link>
        ),
      },
      {
        accessorKey: "claim_type",
        header: "Type",
        size: 140,
        enableGrouping: true,
        cell: ({ getValue }) => (
          <span className="text-xs">{formatClaimType(String(getValue()))}</span>
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
        size: 140,
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
        accessorKey: "merchant_name",
        header: "Merchant",
        size: 130,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "customer_email",
        header: "Customer",
        size: 160,
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
        accessorKey: "tracking_number",
        header: "Tracking",
        size: 120,
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
        accessorKey: "has_insurance",
        header: "Insurance",
        size: 80,
        cell: ({ getValue }) => (getValue() ? "Yes" : "—"),
      },
      {
        accessorKey: "assigned_investigator",
        header: "Investigator",
        size: 130,
        cell: ({ getValue }) => String(getValue() || "—"),
      },
      {
        accessorKey: "risk_score",
        header: "Risk",
        size: 70,
        cell: ({ getValue }) => {
          const v = Number(getValue());
          return (
            <span
              className={cn(
                "font-bold",
                v >= 70 ? "text-red-600" : v >= 40 ? "text-amber-600" : "text-green-600"
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
          <Link href={`/claims/${row.original.id}`} className="text-secondary">
            <ExternalLink className="h-4 w-4" />
          </Link>
        ),
      },
      {
        id: "delete",
        header: "",
        enableSorting: false,
        cell: ({ row }) => <DeleteButton compact entity="claim" id={row.original.id} />,
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
      onExport={() => exportClaimsCsv(rows)}
    />
  );
}
