import { adminFetch } from "@/lib/api";

/** Entity keys the API registry accepts (see soft_delete_service.REGISTRY). */
export type DeletableEntity =
  | "booking_draft" | "lead" | "order" | "parcel" | "merchant" | "customer" | "driver" | "vehicle"
  | "route" | "dispatch_plan" | "claim" | "support_ticket" | "crm_company" | "crm_contact" | "crm_deal"
  | "crm_quotation" | "promotion" | "pricing_zone" | "pricing_tariff" | "standing_order"
  | "booking_template" | "recipient" | "blog_post";

export type DeleteCheck = {
  entity: DeletableEntity;
  id: string;
  label: string;
  allowed: boolean;
  reason: string | null;
  cascade: Record<string, number>;
  can_delete: boolean;
};

export type DeletedItem = {
  id: string;
  entity: string;
  entity_title: string;
  root_id: string;
  label: string;
  reason: string | null;
  deleted_by: string | null;
  deleted_at: string | null;
  purge_after: string | null;
  children: number;
  state: "deleted" | "restored" | "purged";
  outcome: { mode?: string; reason?: string };
};

export type DeletedMeta = {
  entities: { key: string; title: string }[];
  retention_days: number;
  can_delete: boolean;
  can_purge: boolean;
};

const BASE = "/v1/admin/deleted-items";

export const deletedItemsApi = {
  meta: (t: string) => adminFetch<DeletedMeta>(`${BASE}/meta`, t),
  list: (t: string, p: { entity?: string; q?: string; state?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(p).filter(([, v]) => v) as [string, string][]);
    return adminFetch<{ items: DeletedItem[]; retention_days: number }>(`${BASE}?${qs}`, t);
  },
  check: (t: string, entity: DeletableEntity, id: string) =>
    adminFetch<DeleteCheck>(`${BASE}/check/${entity}/${encodeURIComponent(id)}`, t),
  remove: (t: string, entity: DeletableEntity, id: string, reason?: string) =>
    adminFetch<DeletedItem>(`${BASE}/${entity}/${encodeURIComponent(id)}/delete`, t, {
      method: "POST",
      body: JSON.stringify({ reason: reason || null }),
    }),
  restore: (t: string, batchId: string) =>
    adminFetch<DeletedItem>(`${BASE}/${batchId}/restore`, t, { method: "POST" }),
  purge: (t: string, batchId: string, confirm: string) =>
    adminFetch<DeletedItem>(`${BASE}/${batchId}/purge`, t, {
      method: "POST",
      body: JSON.stringify({ confirm }),
    }),
  setRetention: (t: string, days: number) =>
    adminFetch<{ retention_days: number }>(`${BASE}/settings`, t, {
      method: "PUT",
      body: JSON.stringify({ retention_days: days }),
    }),
};

/** "3 orders, 6 parcels" */
export function cascadeSummary(c: Record<string, number>): string {
  return Object.entries(c)
    .map(([k, n]) => `${n} ${k.replace(/_/g, " ")}${n === 1 ? "" : "s"}`)
    .join(", ");
}

export function daysLeft(iso: string | null, now = Date.now()): number | null {
  if (!iso) return null;
  return Math.max(0, Math.ceil((new Date(iso).getTime() - now) / 86_400_000));
}

/** Purge needs the exact label typed back. */
export function confirmMatches(typed: string, label: string): boolean {
  return typed.trim() === label.trim() && label.trim().length > 0;
}
