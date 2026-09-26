"use client";

import { vehicleLabel } from "@/lib/catalog";
import { Card } from "./shared";

export function VehicleTab({
  vehicle,
  status,
  bookedClass,
  bookedLabel,
}: {
  vehicle: Record<string, unknown> | null | undefined;
  status?: string | null;
  bookedClass?: string | null;
  bookedLabel?: string | null;
}) {
  return (
    <div className="space-y-4">
      <Card title="Booked capacity">
        <p className="font-medium">{bookedLabel?.trim() || vehicleLabel(bookedClass) || "—"}</p>
        {bookedClass ? <p className="mt-1 text-muted">Class id: {bookedClass}</p> : null}
      </Card>
      <Card title="Assigned fleet unit">
        {!vehicle ? (
          <p className="text-muted">No vehicle assigned yet.</p>
        ) : (
          <>
            <p className="font-medium">{String(vehicle.label ?? "—")}</p>
            <p className="mt-1 text-muted">
              Class: {vehicleLabel(String(vehicle.vehicle_class ?? ""))}
            </p>
            <p className="mt-1 text-muted">Plate: {String(vehicle.plate_number ?? "—")}</p>
            <p className="mt-1 text-muted">Status: {status ?? "—"}</p>
          </>
        )}
      </Card>
    </div>
  );
}
