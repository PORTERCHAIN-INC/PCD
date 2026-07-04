import { z } from "zod";
import { adminFetch } from "@/lib/api";

const coordSchema = z.object({ lat: z.number(), lng: z.number() });

export const liveMapDriverSchema = z.object({
  id: z.string(),
  reference: z.string(),
  name: z.string(),
  photo_url: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  status: z.string(),
  availability: z.string(),
  online: z.boolean(),
  vehicle_type: z.string().nullable().optional(),
  vehicle_id: z.string().nullable().optional(),
  vehicle_plate: z.string().nullable().optional(),
  location: coordSchema.nullable().optional(),
  heading: z.number().nullable().optional(),
  speed_kmh: z.number().nullable().optional(),
  battery_percent: z.number().nullable().optional(),
  rating: z.number().nullable().optional(),
  current_order_id: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
});

export const liveMapSnapshotSchema = z.object({
  generated_at: z.string(),
  default_center: coordSchema,
  drivers: z.array(liveMapDriverSchema),
  vehicles: z.array(
    z.object({
      id: z.string(),
      reference: z.string(),
      driver_id: z.string().nullable().optional(),
      driver_name: z.string().nullable().optional(),
      vehicle_class: z.string(),
      plate_number: z.string(),
      make_model: z.string().nullable().optional(),
      capacity_kg: z.number().nullable().optional(),
      status: z.string(),
      location: coordSchema.nullable().optional(),
      heading: z.number().nullable().optional(),
    })
  ),
  orders: z.array(
    z.object({
      order_id: z.string(),
      tracking_number: z.string(),
      order_number: z.string(),
      stop_type: z.enum(["pickup", "delivery"]),
      state: z.string(),
      priority: z.string(),
      eta: z.string().nullable().optional(),
      merchant: z.string().nullable().optional(),
      merchant_id: z.string().nullable().optional(),
      customer_name: z.string().nullable().optional(),
      package_count: z.number(),
      vehicle_required: z.string().nullable().optional(),
      location: coordSchema,
      amount_cents: z.number().optional(),
    })
  ),
  merchants: z.array(
    z.object({
      id: z.string(),
      reference: z.string(),
      name: z.string(),
      email: z.string().nullable().optional(),
      phone: z.string().nullable().optional(),
      location: coordSchema.nullable().optional(),
      city: z.string().nullable().optional(),
      status: z.string(),
    })
  ),
  customers: z.array(
    z.object({
      id: z.string(),
      name: z.string().nullable().optional(),
      email: z.string().nullable().optional(),
      phone: z.string().nullable().optional(),
      location: coordSchema.nullable().optional(),
    })
  ),
  warehouses: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      merchant_id: z.string().nullable().optional(),
      merchant_name: z.string().nullable().optional(),
      address_type: z.string(),
      location: coordSchema,
    })
  ),
  geofences: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      geofence_type: z.string(),
      bounds: z.record(z.string(), z.unknown()),
      is_active: z.boolean(),
    })
  ),
  alerts: z.array(
    z.object({
      id: z.string(),
      alert_type: z.string(),
      severity: z.enum(["critical", "warning", "info"]),
      title: z.string(),
      message: z.string(),
      entity_type: z.string().nullable().optional(),
      entity_id: z.string().nullable().optional(),
      location: coordSchema.nullable().optional(),
      created_at: z.string().nullable().optional(),
    })
  ),
  events: z.array(
    z.object({
      id: z.string(),
      event_type: z.string(),
      source: z.string(),
      title: z.string(),
      aggregate_type: z.string().nullable().optional(),
      aggregate_id: z.string().nullable().optional(),
      occurred_at: z.string().nullable().optional(),
    })
  ),
  command_center: z.object({
    orders_today: z.number(),
    drivers_online: z.number(),
    vehicles_active: z.number(),
    orders_waiting: z.number(),
    late_orders: z.number(),
    delayed_drivers: z.number(),
    support_tickets: z.number(),
    revenue_today_cents: z.number(),
    open_claims: z.number(),
    open_exceptions: z.number(),
  }),
  heat_maps: z.record(
    z.string(),
    z.array(z.object({ lat: z.number(), lng: z.number(), weight: z.number().optional() }))
  ),
  smart: z.object({
    nearest_drivers: z.array(liveMapDriverSchema),
    suggested_drivers: z.array(liveMapDriverSchema),
    delay_predictions: z.array(z.record(z.string(), z.unknown())),
    traffic_warnings: z.array(z.string()),
    route_risks: z.array(z.record(z.string(), z.unknown())),
    merchant_health: z.array(z.record(z.string(), z.unknown())),
    driver_health: z.array(z.record(z.string(), z.unknown())),
  }),
  weather: z.record(z.string(), z.unknown()),
});

export type LiveMapSnapshot = z.infer<typeof liveMapSnapshotSchema>;
export type LiveMapDriver = z.infer<typeof liveMapDriverSchema>;

export type LiveMapFilters = {
  driver_status?: string[];
  vehicle_type?: string[];
  merchant_id?: string;
  city?: string;
  region?: string;
  priority?: "high" | "normal" | "all";
  delivery_status?: string[];
  date?: string;
  online_only?: boolean;
};

export type MapLayers = {
  drivers: boolean;
  vehicles: boolean;
  orders: boolean;
  warehouses: boolean;
  merchants: boolean;
  customers: boolean;
  geofences: boolean;
  traffic: boolean;
  heatMap: boolean;
  routes: boolean;
  labels: boolean;
  cluster: boolean;
};

export const DEFAULT_LAYERS: MapLayers = {
  drivers: true,
  vehicles: true,
  orders: true,
  warehouses: true,
  merchants: false,
  customers: false,
  geofences: false,
  traffic: false,
  heatMap: false,
  routes: false,
  labels: true,
  cluster: true,
};

const B = "/v1/admin/operations/live-map";

/** Map marker ids for orders are `{uuid}-pickup|delivery`; detail API needs the full uuid. */
export function parseLiveMapEntityId(
  type: string,
  id: string
): { entityType: string; entityId: string } {
  if (type === "order") {
    return {
      entityType: "order",
      entityId: id.replace(/-(pickup|delivery)$/i, ""),
    };
  }
  return { entityType: type, entityId: id };
}

function qs(filters?: LiveMapFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  if (filters.driver_status?.length) p.set("driver_status", filters.driver_status.join(","));
  if (filters.vehicle_type?.length) p.set("vehicle_type", filters.vehicle_type.join(","));
  if (filters.merchant_id) p.set("merchant_id", filters.merchant_id);
  if (filters.city) p.set("city", filters.city);
  if (filters.region) p.set("region", filters.region);
  if (filters.priority) p.set("priority", filters.priority);
  if (filters.delivery_status?.length) p.set("delivery_status", filters.delivery_status.join(","));
  if (filters.date) p.set("date", filters.date);
  if (filters.online_only) p.set("online_only", "true");
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const liveMapApi = {
  snapshot: async (token: string, filters?: LiveMapFilters) => {
    const raw = await adminFetch<unknown>(`${B}${qs(filters)}`, token);
    return liveMapSnapshotSchema.parse(raw);
  },
  search: (token: string, q: string) =>
    adminFetch<
      Array<{
        type: string;
        id: string;
        label: string;
        subtitle?: string;
        location?: { lat: number; lng: number };
      }>
    >(`${B}/search?q=${encodeURIComponent(q)}`, token),
  detail: (token: string, entityType: string, entityId: string) =>
    adminFetch<Record<string, unknown>>(`${B}/detail/${entityType}/${entityId}`, token),
  playback: (token: string, date: string, driverId?: string) => {
    const p = new URLSearchParams({ date });
    if (driverId) p.set("driver_id", driverId);
    return adminFetch<Record<string, unknown>>(`${B}/playback?${p}`, token);
  },
  nearestDrivers: (token: string, lat: number, lng: number) =>
    adminFetch<LiveMapDriver[]>(`${B}/nearest-drivers?lat=${lat}&lng=${lng}`, token),
};
