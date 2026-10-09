import type { DriverVehicle } from "./api";

export interface ShiftRoute {
  route_id: string;
  status: string;
  stops_count: number;
  earnings_cents: number;
  started_at: string | null;
}

export interface ShiftCapacity {
  max_kg: number | null;
  used_kg: number;
  remaining_kg: number | null;
  stops_count: number;
  utilization_percent: number | null;
}

export interface ShiftRecord {
  id: string;
  status: "active" | "on_break" | "ended";
  started_at: string | null;
  ended_at: string | null;
  break_minutes: number;
  mileage_km: number;
  vehicle_id: string | null;
  route_id: string | null;
  pretrip?: Record<string, unknown> | null;
}

export interface ShiftActivity {
  id: string;
  activity_type: string;
  label: string;
  payload: Record<string, unknown>;
  created_at: string | null;
}

export interface DriverShiftSnapshot {
  shift_active: boolean;
  shift: ShiftRecord | null;
  availability: string;
  is_online: boolean;
  working_minutes: number;
  working_hours_label: string;
  mileage_km: number;
  mileage_source?: string | null;
  current_vehicle: DriverVehicle | null;
  current_route: ShiftRoute | null;
  capacity: ShiftCapacity;
  timeline: ShiftActivity[];
  activity_log: ShiftActivity[];
  last_updated: string;
}

export function availabilityLabel(mode: string): string {
  const map: Record<string, string> = {
    available: "Online",
    online: "Online",
    offline: "Offline",
    busy: "Busy",
    idle: "Idle",
    on_break: "On Break",
  };
  return map[mode] ?? mode;
}

export function availabilityColor(mode: string): string {
  if (mode === "available" || mode === "online" || mode === "idle") return "bg-emerald-500";
  if (mode === "busy") return "bg-amber-500";
  if (mode === "on_break") return "bg-blue-500";
  return "bg-gray-400";
}

export function formatActivityTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
