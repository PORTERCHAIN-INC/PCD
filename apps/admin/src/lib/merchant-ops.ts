import { adminFetch } from "@/lib/api";
import { downloadOrderFile } from "@/lib/orders";

const B = "/v1/admin/merchant-ops";

export type HealthReason = { points: number; label: string };
export type Trend = {
  weekly: number[];
  change_pct: number | null;
  last_4w: number;
  prior_4w: number;
};
export type NeedKey =
  | "credit_hold"
  | "overdue"
  | "integration"
  | "churn_risk"
  | "onboarding_stuck"
  | "exceptions"
  | "at_risk";

export type BoardRow = {
  id: string;
  company_name: string;
  status: string;
  segment: string;
  segment_label: string;
  owner_id: string | null;
  owner_name: string | null;
  pricing_model: string;
  payment_terms: string;
  credit_hold: boolean;
  health: { score: number; band: "healthy" | "watch" | "at_risk"; top_reason: string | null };
  signals: string[];
  needs_action: NeedKey[];
  needs_labels: string[];
  next_action: string;
  trend: Trend;
  connections: "red" | "green" | "none";
  outstanding_cents: number;
  overdue_cents: number;
  days_since_last_order: number | null;
};

export type Board = {
  items: BoardRow[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  counts: {
    needs_action: number;
    all: number;
    segments: Record<string, number>;
    at_risk?: number;
    on_hold?: number;
    overdue_cents?: number;
    outstanding_cents?: number;
  };
  segments: { value: string; label: string }[];
};

export type CreditState = {
  mode: "none" | "manual" | "auto";
  blocked: boolean;
  reasons: string[];
  auto_hold_due: boolean;
  limit_cents: number | null;
  outstanding_cents: number;
  overdue_cents: number;
  headroom_cents: number | null;
  oldest_overdue_days: number;
  overdue_invoices: {
    invoice_id: string;
    amount_cents: number;
    days_overdue: number;
    due_at: string | null;
  }[];
  override_until: string | null;
  hold_since: string | null;
  policy: { auto_hold: boolean; grace_days: number };
  payment_method: string;
};

export type MerchantOps = {
  merchant_id: string;
  health: {
    score: number;
    band: "healthy" | "watch" | "at_risk";
    reasons: HealthReason[];
    signals: string[];
    needs_action: NeedKey[];
    next_action: string;
    trend: Trend;
    days_since_last_order: number | null;
    usual_gap_days: number | null;
    on_time_pct: number | null;
    connections: "red" | "green" | "none";
    open_tickets: number;
    open_claims: number;
    open_exceptions: number;
    outstanding_cents: number;
    overdue_cents: number;
  };
  needs_labels: string[];
  credit: CreditState;
  owner: { id: string | null; name: string | null };
  segment: { value: string; label: string; tags: string[] };
  can_edit_money: boolean;
};

export type Owner = { id: string; name: string; email: string; role: string };

export type ChangeRow = {
  id: string;
  at: string | null;
  action: string;
  area: string;
  actor: string | null;
  actor_role: string | null;
  reason: string | null;
  changes: Record<string, { old: unknown; new: unknown }>;
};

export type ConnectionItem = {
  kind: "shopify" | "api_key" | "webhook";
  id: string;
  name: string;
  environment?: string;
  light: "red" | "amber" | "green";
  problems: string[];
  warnings: string[];
  missing_scopes?: string[];
  last_webhook_at?: string | null;
  last_used_at?: string | null;
  dlq_open?: number;
  failed_24h?: number;
  fixes: string[];
};

export type Connections = {
  light: "red" | "amber" | "green" | "none";
  items: ConnectionItem[];
  checked_at: string;
};

export type QuotePreview = {
  price: {
    final_cents: number;
    subtotal_cents: number;
    tax_cents: number | null;
    lines: { code: string; label: string; amount_cents: number }[];
    pricing_model: string;
    refused: boolean;
    price_version?: string | null;
  };
  route: {
    pickup: string;
    dropoff: string;
    distance_km: number | null;
    drive_minutes: number | null;
  };
  driver_cost: { cents: number; mode: string; basis: string };
  margin: {
    margin_cents: number;
    margin_pct: number | null;
    status: "ok" | "below_floor" | "below_cost" | "no_price";
    floor_pct: number;
  };
  fsa_rows_below_floor: {
    origin_fsa: string | null;
    dest_fsa: string | null;
    flat_cents: number;
    margin_pct: number | null;
    status: string;
  }[];
};

export type MerchantDoc = {
  id: string;
  kind: string;
  kind_label: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  expires_on: string | null;
  expired: boolean;
  note: string | null;
  created_at: string | null;
};

export type SupportRollup = {
  tickets: {
    id: string;
    subject: string;
    status: string;
    priority: string;
    created_at: string | null;
  }[];
  claims: {
    id: string;
    type: string;
    status: string;
    order_id: string | null;
    created_at: string | null;
  }[];
  exceptions: {
    id: string;
    type: string;
    status: string;
    order_id: string;
    tracking_number: string | null;
    created_at: string | null;
  }[];
};

export type BoardQuery = {
  view: "needs_action" | "all";
  segment?: string;
  status?: string;
  owner_id?: string;
  search?: string;
  sort?: string;
  page?: number;
  page_size?: number;
};

const json = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const merchantOps = {
  board: (t: string, q: BoardQuery) => {
    const qs = new URLSearchParams();
    Object.entries(q).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return adminFetch<Board>(`${B}/board?${qs.toString()}`, t);
  },
  owners: (t: string) => adminFetch<Owner[]>(`${B}/owners`, t),
  overview: (t: string, id: string) => adminFetch<MerchantOps>(`${B}/${id}`, t),
  history: (t: string, id: string) => adminFetch<ChangeRow[]>(`${B}/${id}/change-history`, t),
  credit: (
    t: string,
    id: string,
    body: { action: string; reason?: string; limit_cents?: number | null; override_days?: number }
  ) => adminFetch<CreditState>(`${B}/${id}/credit`, t, json(body)),
  setOwner: (t: string, id: string, owner_id: string | null) =>
    adminFetch(`${B}/${id}/owner`, t, { method: "PUT", body: JSON.stringify({ owner_id }) }),
  setSegment: (t: string, id: string, segment: string | null) =>
    adminFetch(`${B}/${id}/segment`, t, { method: "PUT", body: JSON.stringify({ segment }) }),
  bulk: (
    t: string,
    body: { action: string; merchant_ids: string[]; value?: string | null; reason?: string }
  ) =>
    adminFetch<{ ok: string[]; failed: { id: string; error: string }[] }>(
      `${B}/bulk`,
      t,
      json(body)
    ),
  connections: (t: string, id: string) => adminFetch<Connections>(`${B}/${id}/connections`, t),
  rotateKey: (t: string, id: string, keyId: string, grace_days: number, reason: string) =>
    adminFetch<{ secret: string; key_prefix: string; old_key_retires_at: string | null }>(
      `${B}/${id}/api-keys/${keyId}/rotate`,
      t,
      json({ grace_days, reason })
    ),
  replayFailed: (t: string, id: string, hours = 24, webhook_id?: string) =>
    adminFetch<{ replayed: number; succeeded: number; failed: number }>(
      `${B}/${id}/webhooks/replay-failed`,
      t,
      json({ hours, webhook_id })
    ),
  backfill: (t: string, id: string, shopId: string) =>
    adminFetch<{ accepted?: number; rejected?: number }>(
      `${B}/${id}/shopify/${shopId}/backfill`,
      t,
      {
        method: "POST",
      }
    ),
  quotePreview: (
    t: string,
    id: string,
    body: {
      pickup?: { formatted?: string; postal?: string };
      dropoff: { formatted?: string; postal?: string };
      weight_kg?: number | null;
    }
  ) =>
    adminFetch<QuotePreview>(`${B}/${id}/quote-preview`, t, { ...json(body), timeoutMs: 30_000 }),
  documents: (t: string, id: string) =>
    adminFetch<{ items: MerchantDoc[]; kinds: Record<string, string>; max_bytes: number }>(
      `${B}/${id}/documents`,
      t
    ),
  async uploadDocument(
    t: string,
    id: string,
    file: File,
    kind: string,
    expires_on?: string,
    note?: string
  ): Promise<MerchantDoc> {
    const { isLocalDev } = await import("@/lib/env");
    const form = new FormData();
    form.append("file", file);
    form.append("kind", kind);
    if (expires_on) form.append("expires_on", expires_on);
    if (note) form.append("note", note);
    const res = await fetch(`/api/porterchain${B}/${id}/documents`, {
      method: "POST",
      credentials: "include",
      headers: {
        Authorization: `Bearer ${t}`,
        ...(isLocalDev() ? { "X-Admin-Role": "admin" } : {}),
      },
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = (body as { detail?: string }).detail;
      throw new Error(typeof detail === "string" ? detail : `Upload failed (${res.status})`);
    }
    return res.json() as Promise<MerchantDoc>;
  },
  downloadDocument: (t: string, id: string, doc: MerchantDoc) =>
    downloadOrderFile(t, `${B}/${id}/documents/${doc.id}/download`, doc.filename),
  deleteDocument: (t: string, id: string, docId: string, reason: string) =>
    adminFetch(`${B}/${id}/documents/${docId}`, t, {
      method: "DELETE",
      body: JSON.stringify({ reason }),
    }),
  support: (t: string, id: string) => adminFetch<SupportRollup>(`${B}/${id}/support`, t),
};

export const NEED_TAB: Record<NeedKey, { tab: string; panel?: string }> = {
  credit_hold: { tab: "money", panel: "credit" },
  overdue: { tab: "money", panel: "credit" },
  integration: { tab: "connections" },
  churn_risk: { tab: "people", panel: "contacts" },
  onboarding_stuck: { tab: "people", panel: "team" },
  exceptions: { tab: "orders" },
  at_risk: { tab: "overview" },
};

export function cad(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return (cents / 100).toLocaleString("en-CA", { style: "currency", currency: "CAD" });
}
