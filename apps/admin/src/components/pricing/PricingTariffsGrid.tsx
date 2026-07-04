"use client";

import { useMemo, useState } from "react";
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
import { Download } from "lucide-react";
import { cn, formatCents } from "@porterchain/ui/utils";
import { exportTariffsCsv, STATUS_STYLES, type TariffRow } from "@/lib/pricing";
import { Button } from "@/components/crm/primitives";

type Props = {
  rows: TariffRow[];
  onPublish: (id: string) => void;
};

export default function PricingTariffsGrid({ rows, onPublish }: Props) {
  const [grouping, setGrouping] = useState<GroupingState>([]);
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [globalFilter, setGlobalFilter] = useState("");

  const columns = useMemo<ColumnDef<TariffRow>[]>(
    () => [
      { accessorKey: "name", header: "Rule", size: 160 },
      {
        accessorKey: "tariff_type",
        header: "Type",
        size: 100,
        enableGrouping: true,
        cell: ({ getValue }) => <span className="text-xs capitalize">{String(getValue()).replace(/_/g, " ")}</span>,
      },
      { accessorKey: "vehicle_class", header: "Vehicle", size: 90, cell: ({ getValue }) => String(getValue() || "—") },
      { accessorKey: "zone", header: "Zone", size: 90, cell: ({ getValue }) => String(getValue() || "—") },
      { accessorKey: "merchant_name", header: "Merchant", size: 120, cell: ({ getValue }) => String(getValue() || "—") },
      { accessorKey: "base_cents", header: "Base", size: 80, cell: ({ getValue }) => formatCents(Number(getValue())) },
      { accessorKey: "per_km_cents", header: "/km", size: 70, cell: ({ getValue }) => formatCents(Number(getValue())) },
      {
        accessorKey: "status",
        header: "Status",
        size: 110,
        enableGrouping: true,
        cell: ({ getValue }) => {
          const v = String(getValue());
          return <span className={cn("rounded-full px-2 py-0.5 text-xs font-bold capitalize", STATUS_STYLES[v] ?? "bg-gray-100")}>{v.replace(/_/g, " ")}</span>;
        },
      },
      { accessorKey: "version", header: "Ver", size: 50 },
      {
        id: "actions",
        header: "",
        size: 90,
        cell: ({ row }) =>
          row.original.status !== "published" ? (
            <Button variant="outline" onClick={() => onPublish(row.original.id)}>Publish</Button>
          ) : null,
      },
    ],
    [onPublish]
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
          placeholder="Filter rules…"
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        />
        <select
          value={grouping[0] ?? ""}
          onChange={(e) => setGrouping(e.target.value ? [e.target.value] : [])}
          className="rounded-xl border border-primary/10 px-3 py-2 text-sm"
        >
          <option value="">No grouping</option>
          <option value="tariff_type">Group by type</option>
          <option value="status">Group by status</option>
        </select>
        <Button variant="outline" onClick={() => exportTariffsCsv(rows)}>
          <Download className="h-4 w-4" /> CSV
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
