import { vehicleLabel as capacityVehicleLabel } from "@porterchain/types";

export function formatCents(cents: number | null | undefined, currency = "CAD"): string {
  if (cents == null || Number.isNaN(cents)) return "—";
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

export function formatEtaMinutes(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  if (minutes < 1) return "< 1 min";
  if (minutes < 60) return `${Math.round(minutes)} min`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${Math.round(minutes % 60)}m`;
}

export function formatKm(meters: number | null | undefined): string {
  if (meters == null) return "—";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("en-CA", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

const CLOSED_STATES = new Set([
  "DELIVERED",
  "POD_COMPLETED",
  "INVOICED",
  "CLOSED",
  "CANCELLED",
  "FAILED",
  "RETURN_TO_SENDER",
  "DAMAGED",
  "LOST",
  "REFUNDED",
]);

export function jobIsClosed(job: { state?: string; status?: string; bucket?: string }): boolean {
  if (job.bucket === "completed") return true;
  const state = (job.state || job.status || "").toUpperCase();
  return CLOSED_STATES.has(state);
}

export function formatDayLabel(isoOrDate: string | null | undefined): string {
  if (!isoOrDate) return "Earlier";
  const date = isoOrDate.length <= 10 ? new Date(`${isoOrDate}T12:00:00Z`) : new Date(isoOrDate);
  if (Number.isNaN(date.getTime())) return "Earlier";
  return date.toLocaleDateString("en-CA", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export function formatAccessLine(bits: {
  special_instructions?: string | null;
  access_unit?: string | null;
  access_buzzer?: string | null;
  access_dock?: string | null;
  call_on_arrival?: boolean | null;
  contact_phone_masked?: string | null;
}): string | null {
  const parts: string[] = [];
  if (bits.access_unit) parts.push(`Unit ${bits.access_unit}`);
  if (bits.access_buzzer) parts.push(`Buzzer ${bits.access_buzzer}`);
  if (bits.access_dock) parts.push(`Dock ${bits.access_dock}`);
  if (bits.call_on_arrival) parts.push("Call on arrival");
  if (bits.contact_phone_masked) parts.push(bits.contact_phone_masked);
  if (bits.special_instructions) parts.push(bits.special_instructions);
  return parts.length ? parts.join(" · ") : null;
}

export function vehicleLabel(id?: string | null): string {
  if (!id) return "vehicle";
  return capacityVehicleLabel(id, id.replace(/_/g, " "));
}

export function parcelScanLabel(job: {
  scan_pickup?: { scanned?: number; required?: number };
  scan_delivery?: { scanned?: number; required?: number };
}): string | null {
  const pickup = job.scan_pickup;
  const delivery = job.scan_delivery;
  const required = Math.max(pickup?.required ?? 0, delivery?.required ?? 0);
  if (required <= 0) return null;
  return `Parcels pickup ${pickup?.scanned ?? 0}/${pickup?.required ?? 0} · delivery ${delivery?.scanned ?? 0}/${delivery?.required ?? 0}`;
}
