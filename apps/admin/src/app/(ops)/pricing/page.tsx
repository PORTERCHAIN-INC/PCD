"use client";

import { DataTable } from "@/components/DataTable";
import { useApiData } from "@/hooks/useApiData";
import { api } from "@/lib/api";
import { formatCents } from "@porterchain/ui/utils";

export default function PricingPage() {
  const { data } = useApiData((t) => api.tariffs(t));

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Pricing</h1>
      <DataTable
        columns={["Name", "Type", "Vehicle", "Base", "Per km", "Fuel %"]}
        rows={(data || []).map((t) => [
          String(t.name),
          String(t.tariff_type),
          String(t.vehicle_class || "—"),
          formatCents(Number(t.base_cents)),
          formatCents(Number(t.per_km_cents)),
          String(t.fuel_surcharge_percent),
        ])}
      />
    </div>
  );
}
