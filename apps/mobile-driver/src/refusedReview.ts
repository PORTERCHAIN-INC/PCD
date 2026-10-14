/**
 * Refused-actions review: one list of everything the server would not accept, whether it was
 * parked on this phone or failed during a server-side replay. Retry / Discard per item.
 */
import { discardServerAction, fetchOfflineStatus, retryServerAction } from "./api";
import { humanError } from "./errorCopy";
import { discardRejected, flushOfflineQueues, readRejected, unparkRejected } from "./offline";

export type RefusedItem = {
  key: string;
  source: "device" | "server";
  id: string;
  action: string;
  where: string | null;
  at: string | null;
  reason: string;
};

const ACTION_LABEL: Record<string, string> = {
  shift_start: "Start shift",
  shift_end: "End shift",
  stop_arrive: "Arrived at stop",
  stop_complete: "Completed stop",
  stop_fail: "Failed stop",
  stop_exception: "Stop problem",
  pod_photo: "Proof photo",
  pod_signature: "Signature",
  pod_barcode: "Barcode scan",
  pod_id_check: "ID check",
  camera_upload: "Photo upload",
  document_upload: "Document upload",
  location: "Location update",
  job_accept: "Accept job",
  job_decline: "Decline job",
  status_update: "Status update",
};

export function actionLabel(t: string): string {
  return ACTION_LABEL[t] ?? t.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function whereLabel(p: Record<string, unknown> | null | undefined): string | null {
  if (!p) return null;
  const parts: string[] = [];
  const job = p.order_id ?? p.job_id ?? p.route_id;
  const stop = p.stop_id;
  if (typeof job === "string" && job) parts.push(`Job ${job.slice(0, 8)}`);
  if (typeof stop === "string" && stop) parts.push(`Stop ${stop.slice(0, 8)}`);
  return parts.length ? parts.join(" · ") : null;
}

export function reasonLabel(raw: string | null | undefined): string {
  if (!raw) return "The server did not say why.";
  return humanError(raw) || raw;
}

export async function loadRefused(): Promise<RefusedItem[]> {
  const local = (await readRejected()).map<RefusedItem>((a) => ({
    key: `device:${a.client_id}`,
    source: "device",
    id: a.client_id,
    action: actionLabel(a.action_type),
    where: whereLabel(a.payload),
    at: a.created_at ?? null,
    reason: reasonLabel(a.rejected_reason),
  }));
  let server: RefusedItem[] = [];
  try {
    const st = await fetchOfflineStatus();
    server = (st.failed ?? []).map((r) => ({
      key: `server:${r.id}`,
      source: "server" as const,
      id: r.id,
      action: actionLabel(r.action_type),
      where: whereLabel(r.payload),
      at: r.created_at,
      reason: reasonLabel(r.error),
    }));
  } catch {
    /* offline: show the device list only */
  }
  return [...local, ...server].sort((a, b) => (b.at ?? "").localeCompare(a.at ?? ""));
}

/** Returns null on success, or a driver-readable reason if it was refused again. */
export async function retryRefused(item: RefusedItem): Promise<string | null> {
  if (item.source === "device") {
    await unparkRejected(item.id);
    await flushOfflineQueues();
    const still = (await readRejected()).some((a) => a.client_id === item.id);
    return still ? "Refused again. Call dispatch." : null;
  }
  const row = await retryServerAction(item.id);
  return row.status === "failed" ? reasonLabel(row.error) : null;
}

export async function discardRefused(item: RefusedItem): Promise<void> {
  if (item.source === "device") await discardRejected(item.id);
  else await discardServerAction(item.id);
}

type Listener = () => void;
const openers = new Set<Listener>();
const changed = new Set<Listener>();
export function openRefusedReview(): void {
  openers.forEach((f) => f());
}
export function onOpenRefusedReview(f: Listener): () => void {
  openers.add(f);
  return () => openers.delete(f);
}
export function notifyRefusedChanged(): void {
  changed.forEach((f) => f());
}
export function onRefusedChanged(f: Listener): () => void {
  changed.add(f);
  return () => changed.delete(f);
}
