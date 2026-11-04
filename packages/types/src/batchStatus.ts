/** Bulk batch / route status → label + tone, shared by merchant and admin portals. */
export type BatchTone = "neutral" | "info" | "success" | "warning" | "danger";

const BATCH_STATUS: Record<string, { label: string; tone: BatchTone }> = {
  planned: { label: "Planned", tone: "neutral" },
  locked: { label: "Waiting on upstream leg", tone: "info" },
  awaiting_handover: { label: "Awaiting handover", tone: "info" },
  pickup_confirmed: { label: "In delivery", tone: "info" },
  closed: { label: "Route closed", tone: "success" },
  completed: { label: "Completed", tone: "success" },
  pickup_failed: { label: "Pickup failed", tone: "danger" },
  cancelled: { label: "Cancelled", tone: "danger" },
};

export function batchStatusLabel(status: string | null | undefined): {
  label: string;
  tone: BatchTone;
} {
  const s = String(status ?? "").toLowerCase();
  return (
    BATCH_STATUS[s] ?? {
      label: s ? s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()) : "Unknown",
      tone: "neutral",
    }
  );
}

export const BATCH_TONE_CLASS: Record<BatchTone, string> = {
  neutral: "bg-gray-100 text-gray-800",
  info: "bg-blue-100 text-blue-800",
  success: "bg-green-100 text-green-800",
  warning: "bg-amber-100 text-amber-800",
  danger: "bg-red-100 text-red-800",
};
