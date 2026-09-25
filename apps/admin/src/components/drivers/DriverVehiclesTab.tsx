"use client";

import { useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useApiData } from "@/hooks/useApiData";
import { drivers } from "@/lib/drivers";
import { Badge, Button, SectionCard } from "@/components/crm/primitives";
import { shortDate, titleCase } from "@/lib/crmFormat";

export function VehiclesTab({ id, canWrite }: { id: string; canWrite: boolean }) {
  const { getApiToken } = useAdminAuth();
  const [version, setVersion] = useState(0);
  const [open, setOpen] = useState(false);
  const [vehicleClass, setVehicleClass] = useState("cargoVan");
  const [plate, setPlate] = useState("");
  const [makeModel, setMakeModel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editClass, setEditClass] = useState("cargoVan");
  const [editPlate, setEditPlate] = useState("");
  const [editMake, setEditMake] = useState("");
  const vehicleClasses = ["sedan", "suv", "pickup", "cargoVan", "highRoof", "box16", "box20"];
  const classOptions = (current: string) =>
    vehicleClasses.includes(current) ? vehicleClasses : [current, ...vehicleClasses];
  const { data } = useApiData((t) => drivers.vehicles(t, id), [id, version], {
    key: `driver-vehicles-${id}`,
  });
  async function addVehicle(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const token = await getApiToken();
      await drivers.addVehicle(token, id, {
        vehicle_class: vehicleClass,
        plate_number: plate,
        make_model: makeModel || undefined,
      });
      setPlate("");
      setMakeModel("");
      setOpen(false);
      setVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add vehicle");
    }
  }
  async function setActive(vehicleId: string, active: boolean) {
    setError(null);
    try {
      const token = await getApiToken();
      if (active) await drivers.updateVehicle(token, id, vehicleId, { is_active: true });
      else await drivers.deactivateVehicle(token, id, vehicleId);
      setVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update vehicle");
    }
  }
  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editingId) return;
    setError(null);
    try {
      const token = await getApiToken();
      await drivers.updateVehicle(token, id, editingId, {
        vehicle_class: editClass,
        plate_number: editPlate,
        make_model: editMake || undefined,
      });
      setEditingId(null);
      setVersion((n) => n + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update vehicle");
    }
  }
  return (
    <SectionCard
      title={`Vehicles (${data?.length ?? 0})`}
      action={
        canWrite ? (
          <Button variant="outline" onClick={() => setOpen((v) => !v)}>
            Add vehicle
          </Button>
        ) : undefined
      }
    >
      {open && (
        <form
          onSubmit={addVehicle}
          className="grid gap-2 border-b border-primary/10 p-5 sm:grid-cols-3"
        >
          <select
            value={vehicleClass}
            onChange={(e) => setVehicleClass(e.target.value)}
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          >
            {classOptions(vehicleClass).map((item) => (
              <option key={item} value={item}>
                {titleCase(item)}
              </option>
            ))}
          </select>
          <input
            value={plate}
            onChange={(e) => setPlate(e.target.value)}
            placeholder="Plate"
            required
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          />
          <input
            value={makeModel}
            onChange={(e) => setMakeModel(e.target.value)}
            placeholder="Make and model"
            className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
          />
          <Button type="submit">Save vehicle</Button>
          {error && <p className="text-sm text-red-600 sm:col-span-3">{error}</p>}
        </form>
      )}
      {error && <p className="px-5 pt-3 text-sm text-red-600">{error}</p>}
      <div className="divide-y divide-primary/5">
        {(data ?? []).map((v) => (
          <div key={v.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
            {editingId === v.id ? (
              <form onSubmit={saveEdit} className="grid w-full gap-2 sm:grid-cols-4">
                <select
                  value={editClass}
                  onChange={(e) => setEditClass(e.target.value)}
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                >
                  {classOptions(editClass).map((item) => (
                    <option key={item} value={item}>
                      {titleCase(item)}
                    </option>
                  ))}
                </select>
                <input
                  value={editPlate}
                  onChange={(e) => setEditPlate(e.target.value)}
                  required
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                />
                <input
                  value={editMake}
                  onChange={(e) => setEditMake(e.target.value)}
                  placeholder="Make and model"
                  className="rounded-xl border border-primary/15 px-3 py-2 text-sm"
                />
                <div className="flex gap-2">
                  <Button type="submit">Save</Button>
                  <Button type="button" variant="outline" onClick={() => setEditingId(null)}>
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <>
                <div>
                  <p className="text-sm font-medium text-primary">
                    {v.make_model ?? titleCase(v.vehicle_class)}{" "}
                    {v.is_active && <Badge tone="green">Active</Badge>}
                  </p>
                  <p className="text-xs text-muted">
                    {titleCase(v.vehicle_class)} · {v.plate_number} ·{" "}
                    {v.capacity_kg ? `${v.capacity_kg} kg` : "—"}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {v.compliance_expires_at && (
                    <Badge tone="slate">Expires {shortDate(v.compliance_expires_at)}</Badge>
                  )}
                  {canWrite && (
                    <Button
                      variant="outline"
                      onClick={() => {
                        setEditingId(v.id);
                        setEditClass(v.vehicle_class);
                        setEditPlate(v.plate_number);
                        setEditMake(v.make_model ?? "");
                      }}
                    >
                      Edit
                    </Button>
                  )}
                  {canWrite && v.is_active && (
                    <Button variant="outline" onClick={() => void setActive(v.id, false)}>
                      Take off the road
                    </Button>
                  )}
                  {canWrite && !v.is_active && (
                    <Button variant="outline" onClick={() => void setActive(v.id, true)}>
                      Set active
                    </Button>
                  )}
                </div>
              </>
            )}
          </div>
        ))}
        {(!data || data.length === 0) && (
          <p className="px-5 py-10 text-center text-sm text-muted">
            No vehicles yet. {canWrite ? "Add the vehicle this driver will use." : ""}
          </p>
        )}
      </div>
    </SectionCard>
  );
}
