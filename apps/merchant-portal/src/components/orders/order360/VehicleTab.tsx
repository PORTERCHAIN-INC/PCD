"use client";

import { vehicleLabel } from "@/lib/catalog";
import type { OrderDetail } from "@/lib/orders";
import { Card } from "./shared";

export function VehicleTab({
  vehicle,
  status,
}: {
  vehicle: Record<string, unknown> | null | undefined;
  status?: string | null;
}) {
  if (!vehicle) return <Card title="Vehicle">No vehicle assigned yet.</Card>;
  return (
    <Card title="Vehicle">
      <p className="font-medium">{String(vehicle.label ?? "—")}</p>
      <p className="mt-1 text-muted">Class: {vehicleLabel(String(vehicle.vehicle_class ?? ""))}</p>
      <p className="mt-1 text-muted">Plate: {String(vehicle.plate_number ?? "—")}</p>
      <p className="mt-1 text-muted">Status: {status ?? "—"}</p>
    </Card>
  );
}
