"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Box, Car, Plus, Save, Search, Truck } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button, Drawer, Field, Input, Textarea } from "@/components/crm/primitives";
import { settingsApi, type VehicleClassConfig, type VehiclesOverview } from "@/lib/settings";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { SettingsCard, SettingsPageHeader, StatTile, Toggle } from "../ui/SettingsPrimitives";

type Props = {
  data: unknown;
  defaultClass?: string;
  saving?: boolean;
  onSave: (value: VehicleClassConfig[], reason: string) => Promise<void>;
};

const VEHICLE_ICONS: Record<string, typeof Car> = {
  sedan: Car,
  suv: Car,
  sedan_suv: Car,
  pickup: Truck,
  cargo_van: Truck,
  sprinter_van: Truck,
  box_truck: Box,
  box_16: Box,
  box_20: Box,
};

function slugify(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
}

function normalizeList(raw: unknown): VehicleClassConfig[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null)
    .map((item, index) => ({
      id: String(item.id ?? `vehicle_${index + 1}`),
      label: String(item.label ?? item.id ?? "Vehicle"),
      capacity_kg: Number(item.capacity_kg ?? 0),
      max_length_cm: item.max_length_cm != null ? Number(item.max_length_cm) : undefined,
      max_width_cm: item.max_width_cm != null ? Number(item.max_width_cm) : undefined,
      max_height_cm: item.max_height_cm != null ? Number(item.max_height_cm) : undefined,
      booking_enabled: item.booking_enabled !== false,
      retail_enabled: item.retail_enabled !== false,
      merchant_enabled: item.merchant_enabled !== false,
      whole_vehicle_enabled: item.whole_vehicle_enabled !== false,
      allowed_presets: Array.isArray(item.allowed_presets)
        ? item.allowed_presets.map(String)
        : undefined,
      description: item.description ? String(item.description) : undefined,
      sort_order: item.sort_order != null ? Number(item.sort_order) : index + 1,
    }))
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
}

function blankVehicle(existing: VehicleClassConfig[]): VehicleClassConfig {
  const nextOrder = existing.reduce((max, v) => Math.max(max, v.sort_order ?? 0), 0) + 1;
  return {
    id: "",
    label: "",
    capacity_kg: 50,
    booking_enabled: true,
    retail_enabled: true,
    merchant_enabled: true,
    whole_vehicle_enabled: true,
    allowed_presets: ["small", "medium", "large", "extra_large", "skid", "furniture", "other"],
    sort_order: nextOrder,
  };
}

export default function VehiclesPanel({ data, defaultClass, saving, onSave }: Props) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const initial = useMemo(() => normalizeList(data), [data]);
  const [classes, setClasses] = useState<VehicleClassConfig[]>(initial);
  const [reason, setReason] = useState("");
  const [dirty, setDirty] = useState(false);
  const [search, setSearch] = useState("");
  const [editor, setEditor] = useState<VehicleClassConfig | null>(null);
  const [editorIndex, setEditorIndex] = useState<number | null>(null);

  const { data: overview } = useQuery({
    queryKey: ["settings-vehicles-overview"],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => settingsApi.vehiclesOverview(await getApiToken()),
  });

  useEffect(() => {
    setClasses(initial);
    setDirty(false);
    setReason("");
  }, [initial]);

  const fleetByClass = useMemo(() => {
    const map = new Map<string, VehiclesOverview["by_class"][number]>();
    for (const row of overview?.by_class ?? []) {
      map.set(row.vehicle_class, row);
    }
    return map;
  }, [overview]);

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return classes;
    return classes.filter(
      (v) =>
        v.label.toLowerCase().includes(q) ||
        v.id.toLowerCase().includes(q) ||
        (v.description ?? "").toLowerCase().includes(q)
    );
  }, [classes, search]);

  const stats = useMemo(
    () => ({
      catalog: classes.length,
      bookingEnabled: classes.filter((v) => v.booking_enabled !== false).length,
    }),
    [classes]
  );

  function updateClasses(next: VehicleClassConfig[]) {
    setClasses(next.map((v, i) => ({ ...v, sort_order: v.sort_order ?? i + 1 })));
    setDirty(true);
  }

  function openCreate() {
    setEditor(blankVehicle(classes));
    setEditorIndex(null);
  }

  function openEdit(item: VehicleClassConfig, index: number) {
    setEditor({ ...item });
    setEditorIndex(index);
  }

  function saveEditor() {
    if (!editor || !editor.label.trim()) return;
    const id = editor.id.trim() || slugify(editor.label);
    const payload: VehicleClassConfig = { ...editor, id, label: editor.label.trim() };
    if (classes.some((v, i) => v.id === payload.id && i !== editorIndex)) {
      window.alert("A vehicle class with this ID already exists.");
      return;
    }
    if (payload.capacity_kg <= 0) {
      window.alert("Capacity must be greater than zero.");
      return;
    }
    if (editorIndex == null) {
      updateClasses([...classes, payload]);
    } else {
      updateClasses(classes.map((v, i) => (i === editorIndex ? payload : v)));
    }
    setEditor(null);
    setEditorIndex(null);
  }

  function removeClass(index: number) {
    const target = classes[index];
    if (!target) return;
    const fleet = fleetByClass.get(target.id)?.fleet_count ?? 0;
    if (fleet > 0) {
      window.alert(
        `Cannot remove "${target.label}" — ${fleet} registered fleet vehicle(s) use this class.`
      );
      return;
    }
    if (classes.length <= 1) {
      window.alert("At least one vehicle class must remain in the catalog.");
      return;
    }
    if (!window.confirm(`Remove vehicle class "${target.label}"?`)) return;
    updateClasses(classes.filter((_, i) => i !== index));
  }

  function toggleField(index: number, field: keyof VehicleClassConfig, value: boolean) {
    updateClasses(classes.map((v, i) => (i === index ? { ...v, [field]: value } : v)));
  }

  async function handleSave() {
    if (!reason.trim()) {
      window.alert("Change reason is required for vehicle catalog updates");
      return;
    }
    await onSave(classes, reason.trim());
    setDirty(false);
    setReason("");
  }

  return (
    <div className="space-y-6">
      <SettingsPageHeader
        title="Vehicle Classes"
        description={SECTION_DESCRIPTIONS.vehicles}
        actions={
          <>
            <Button variant="outline" onClick={openCreate}>
              <Plus className="h-4 w-4" /> Add class
            </Button>
            <Button variant="primary" disabled={!dirty || saving} onClick={() => void handleSave()}>
              <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save catalog"}
            </Button>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Vehicle classes" value={String(stats.catalog)} />
        <StatTile label="Booking enabled" value={String(stats.bookingEnabled)} tone="success" />
        <StatTile
          label="Physical fleet"
          value="PorterChain"
          sub="Bonded execution — not edited here"
        />
        <StatTile
          label="Default booking class"
          value={defaultClass ?? overview?.default_vehicle_class ?? "sedan_suv"}
        />
      </div>

      <div className="flex flex-wrap gap-3 rounded-xl border border-primary/10 bg-gray-bg/40 px-4 py-3 text-sm">
        <span className="text-muted">
          Default booking class:{" "}
          <strong className="text-primary">
            {defaultClass ?? overview?.default_vehicle_class ?? "sedan_suv"}
          </strong>
        </span>
        <Link
          href="/settings?section=booking"
          className="inline-flex items-center gap-1 font-medium text-secondary"
        >
          Change in Booking settings <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <Link
          href="/settings?section=pricing"
          className="inline-flex items-center gap-1 font-medium text-secondary"
        >
          Quote rates in Pricing <ArrowRight className="h-3.5 w-3.5" />
        </Link>
        <Link href="/drivers" className="inline-flex items-center gap-1 font-medium text-secondary">
          Driver fleet registry <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <SettingsCard
        title="Vehicle class catalog"
        description="Platform-wide classes for quotes, booking eligibility, route planning, and driver registration. Physical fleet vehicles are registered per driver."
        action={
          <div className="relative w-56">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search classes…"
              className="w-full rounded-xl border border-primary/15 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20"
            />
          </div>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[880px] text-left text-sm">
            <thead className="border-b border-primary/10 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th className="px-3 py-3">Class</th>
                <th className="px-3 py-3">Capacity</th>
                <th className="px-3 py-3">Channels</th>
                <th className="px-3 py-3">Fleet</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => {
                const index = classes.findIndex((v) => v.id === item.id);
                const Icon = VEHICLE_ICONS[item.id] ?? Truck;
                const fleet = fleetByClass.get(item.id);
                const isDefault =
                  item.id === (defaultClass ?? overview?.default_vehicle_class ?? "sedan_suv");
                return (
                  <tr
                    key={item.id}
                    className="border-b border-primary/5 last:border-0 hover:bg-secondary/5"
                  >
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-secondary/10 text-secondary">
                          <Icon className="h-5 w-5" />
                        </span>
                        <div>
                          <p className="flex items-center gap-2 font-semibold text-primary">
                            {item.label}
                            {isDefault && <Badge tone="blue">Default</Badge>}
                          </p>
                          <p className="font-mono text-xs text-muted">{item.id}</p>
                          {item.description && (
                            <p className="mt-0.5 max-w-xs truncate text-xs text-muted">
                              {item.description}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <p className="font-medium text-primary">
                        {item.capacity_kg.toLocaleString()} kg
                      </p>
                      {(item.max_length_cm || item.max_width_cm || item.max_height_cm) && (
                        <p className="text-xs text-muted">
                          {[item.max_length_cm, item.max_width_cm, item.max_height_cm]
                            .filter(Boolean)
                            .join(" × ")}{" "}
                          cm
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex flex-wrap gap-1">
                        {item.retail_enabled !== false && <Badge tone="sky">Retail</Badge>}
                        {item.merchant_enabled !== false && <Badge tone="violet">Merchant</Badge>}
                        {item.retail_enabled === false && item.merchant_enabled === false && (
                          <Badge tone="slate">None</Badge>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      {fleet ? (
                        <div>
                          <p className="font-medium text-primary">{fleet.fleet_count} registered</p>
                          <p className="text-xs text-muted">{fleet.assigned_count} assigned</p>
                        </div>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3">
                      <Badge tone={item.booking_enabled !== false ? "green" : "slate"}>
                        {item.booking_enabled !== false ? "Bookable" : "Disabled"}
                      </Badge>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            toggleField(index, "booking_enabled", item.booking_enabled === false)
                          }
                          className="text-xs font-medium text-secondary hover:underline"
                        >
                          {item.booking_enabled !== false ? "Disable" : "Enable"}
                        </button>
                        <button
                          type="button"
                          onClick={() => openEdit(item, index)}
                          className="text-xs font-medium text-primary hover:underline"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => removeClass(index)}
                          className="text-xs font-medium text-red-600 hover:underline"
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <p className="py-10 text-center text-sm text-muted">
              No vehicle classes match your search.
            </p>
          )}
        </div>
      </SettingsCard>

      <SettingsCard
        collapsed
        title="How this works"
        description="Porterchain owns the catalog and the vans"
      >
        <ul className="space-y-2 text-sm text-muted">
          <li className="flex gap-2">
            <Car className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
            <span>
              <strong className="text-primary">Vehicle classes</strong> are the quote catalog.
              Retail/booking enabled flags gate <code className="text-xs">POST /v1/quotes</code> and
              must have matching Pricing rows.
            </span>
          </li>
          <li className="flex gap-2">
            <Truck className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
            <span>
              <strong className="text-primary">Fleet vehicles</strong> are physical units (plate,
              compliance, driver assignment) registered on each driver profile — not edited here.
            </span>
          </li>
          <li className="flex gap-2">
            <Car className="mt-0.5 h-4 w-4 shrink-0 text-secondary" />
            <span>
              Disabling booking for a class hides it from new quotes but does not remove existing
              driver vehicles or tariffs.
            </span>
          </li>
        </ul>
      </SettingsCard>

      <SettingsCard
        title="Change reason"
        description="Optional — recorded in the settings audit log"
      >
        <Input
          placeholder="e.g. Added sprinter class for GTA merchant routes"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </SettingsCard>

      <Drawer
        open={editor != null}
        onClose={() => {
          setEditor(null);
          setEditorIndex(null);
        }}
        title={editorIndex == null ? "Add vehicle class" : "Edit vehicle class"}
        footer={
          <>
            <Button
              variant="outline"
              onClick={() => {
                setEditor(null);
                setEditorIndex(null);
              }}
            >
              Cancel
            </Button>
            <Button onClick={saveEditor} disabled={!editor?.label.trim()}>
              {editorIndex == null ? "Add class" : "Save changes"}
            </Button>
          </>
        }
      >
        {editor && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Display name *" className="sm:col-span-2">
              <Input
                value={editor.label}
                onChange={(e) =>
                  setEditor({
                    ...editor,
                    label: e.target.value,
                    id: editorIndex == null ? slugify(e.target.value) : editor.id,
                  })
                }
                placeholder="e.g. Sprinter Van"
              />
            </Field>
            <Field label="Class ID" hint="Used in API, pricing, and driver registration">
              <Input
                value={editor.id}
                onChange={(e) => setEditor({ ...editor, id: slugify(e.target.value) })}
                disabled={editorIndex != null}
                className={cn(editorIndex != null && "bg-gray-bg text-muted")}
              />
            </Field>
            <Field label="Sort order">
              <Input
                type="number"
                min={1}
                value={editor.sort_order ?? 1}
                onChange={(e) => setEditor({ ...editor, sort_order: Number(e.target.value) })}
              />
            </Field>
            <Field label="Capacity (kg) *">
              <Input
                type="number"
                min={1}
                value={editor.capacity_kg}
                onChange={(e) => setEditor({ ...editor, capacity_kg: Number(e.target.value) })}
              />
            </Field>
            <Field label="Max length (cm)">
              <Input
                type="number"
                min={0}
                value={editor.max_length_cm ?? ""}
                onChange={(e) =>
                  setEditor({
                    ...editor,
                    max_length_cm: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
              />
            </Field>
            <Field label="Max width (cm)">
              <Input
                type="number"
                min={0}
                value={editor.max_width_cm ?? ""}
                onChange={(e) =>
                  setEditor({
                    ...editor,
                    max_width_cm: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
              />
            </Field>
            <Field label="Max height (cm)">
              <Input
                type="number"
                min={0}
                value={editor.max_height_cm ?? ""}
                onChange={(e) =>
                  setEditor({
                    ...editor,
                    max_height_cm: e.target.value ? Number(e.target.value) : undefined,
                  })
                }
              />
            </Field>
            <Field label="Description" className="sm:col-span-2">
              <Textarea
                rows={3}
                value={editor.description ?? ""}
                onChange={(e) => setEditor({ ...editor, description: e.target.value || undefined })}
                placeholder="Ops notes, typical use case, or restrictions"
              />
            </Field>
            <div className="space-y-2 sm:col-span-2">
              <Toggle
                label="Booking enabled"
                hint="Allow this class in quotes and dispatch planning"
                checked={editor.booking_enabled !== false}
                onChange={(v) => setEditor({ ...editor, booking_enabled: v })}
              />
              <Toggle
                label="Retail channel"
                hint="Website and consumer booking widget"
                checked={editor.retail_enabled !== false}
                onChange={(v) => setEditor({ ...editor, retail_enabled: v })}
              />
              <Toggle
                label="Merchant channel"
                hint="B2B portal and merchant API shipments"
                checked={editor.merchant_enabled !== false}
                onChange={(v) => setEditor({ ...editor, merchant_enabled: v })}
              />
              <Toggle
                label="Whole vehicle"
                hint="Customer can book the vehicle with no parcel list"
                checked={editor.whole_vehicle_enabled !== false}
                onChange={(v) => setEditor({ ...editor, whole_vehicle_enabled: v })}
              />
            </div>
            <Field label="Allowed parcel sizes" className="sm:col-span-2">
              <div className="flex flex-wrap gap-2">
                {["small", "medium", "large", "extra_large", "skid", "furniture", "other"].map(
                  (preset) => {
                    const selected = (editor.allowed_presets ?? []).includes(preset);
                    return (
                      <button
                        key={preset}
                        type="button"
                        className={cn(
                          "rounded-full border px-3 py-1 text-sm",
                          selected ? "border-sky bg-sky/10" : "border-gray-line text-muted"
                        )}
                        onClick={() => {
                          const current = new Set(editor.allowed_presets ?? []);
                          if (preset !== "other") {
                            if (current.has(preset)) current.delete(preset);
                            else current.add(preset);
                          }
                          current.add("other");
                          setEditor({ ...editor, allowed_presets: [...current] });
                        }}
                      >
                        {preset.replaceAll("_", " ")}
                      </button>
                    );
                  }
                )}
              </div>
            </Field>
          </div>
        )}
      </Drawer>
    </div>
  );
}
