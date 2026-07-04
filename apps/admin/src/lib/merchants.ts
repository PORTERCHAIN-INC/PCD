import { adminFetch } from "@/lib/api";
import type { Activity, Contact, Contract, Invoice, Task } from "@/lib/crm";

export type MerchantRow = {
  id: string;
  company_name: string;
  legal_name: string | null;
  logo_url: string | null;
  status: string;
  industry: string | null;
  city: string | null;
  province: string | null;
  country: string | null;
  email: string;
  phone: string | null;
  primary_contact: string | null;
  payment_terms: string;
  contract_status: string;
  monthly_deliveries: number;
  monthly_revenue_cents: number;
  outstanding_balance_cents: number;
  health_score: number;
  api_connected: boolean;
  service_area: string | null;
  owner_id: string | null;
  tags: string[];
  last_activity_at: string | null;
  created_at: string;
  company_id: string | null;
  portal_ready?: boolean;
  onboarding_phase?: string;
  onboarding_progress?: number;
  owner_email?: string;
  owner_invite_status?: string;
  owner_clerk_linked?: boolean;
  owner_active?: boolean;
  team_count?: number;
  blockers_count?: number;
  can_approve?: boolean;
  can_invite_owner?: boolean;
  can_activate_user?: boolean;
};

export type MerchantAi = {
  risk_score: string;
  payment_risk: string;
  revenue_trend: string;
  predicted_monthly_revenue_cents: number;
  renewal_risk: string;
  suggested_actions: string[];
};

export type MerchantDetail = MerchantRow & {
  hst_number: string | null;
  business_number: string | null;
  credit_limit_cents: number | null;
  billing_address: Record<string, unknown>;
  preferred_vehicles: string[];
  delivery_zones: unknown[];
  pricing_config: Record<string, unknown>;
  profile: Record<string, unknown>;
  activated_at: string | null;
  website: string | null;
  health: number;
  ai: MerchantAi;
  metrics: {
    monthly_orders: number;
    monthly_revenue_cents: number;
    lifetime_orders: number;
    lifetime_revenue_cents: number;
    open_orders: number;
    outstanding_balance_cents: number;
    overdue_balance_cents: number;
    api_connected: boolean;
    active_contract: boolean;
    last_activity_at: string | null;
  };
  counts: Record<string, number>;
};

export type MerchantStats = {
  total: number;
  active: number;
  pending: number;
  suspended: number;
  onboarding_pending?: number;
  monthly_revenue_cents: number;
  outstanding_balance_cents: number;
};

export type MerchantOrder = {
  id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  scheduled_at: string | null;
  created_at: string | null;
  pickup: Record<string, unknown>;
  dropoff: Record<string, unknown>;
  assigned_driver_id: string | null;
};

export type MerchantLocations = {
  addresses: Array<{
    id: string;
    label: string;
    address_type: string;
    formatted: string;
    lat: number | null;
    lng: number | null;
    is_default: boolean;
  }>;
  recipients: Array<{
    id: string;
    name: string;
    email: string | null;
    phone: string | null;
    company: string | null;
  }>;
};

export type MerchantTeamUser = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  clerk_linked?: boolean;
  invite_status?: string;
};

export type MerchantOnboarding = {
  merchant_id: string;
  merchant_status: string;
  company_name: string;
  company_email: string;
  owner_email: string;
  owner_invite_status: string;
  owner_clerk_linked: boolean;
  team_count: number;
  steps: Array<{ id: string; label: string; complete: boolean }>;
  blockers: string[];
  ready: boolean;
  can_approve: boolean;
  can_invite_owner: boolean;
};

export type MerchantApi = {
  api_keys: Array<{
    id: string;
    name: string;
    key_prefix: string;
    environment: string;
    scopes: string[];
    rate_limit_per_minute: number;
    is_active: boolean;
    last_used_at: string | null;
    created_at: string;
  }>;
  webhooks: Array<{
    id: string;
    url: string;
    events: string[];
    is_active: boolean;
    created_at: string;
  }>;
};

export type MerchantAnalytics = {
  revenue_by_month: Array<{ month: string; orders: number; revenue_cents: number }>;
  top_destinations: Array<{ city: string; orders: number }>;
  lifetime_orders: number;
  lifetime_revenue_cents: number;
};

export type TimelineEvent = { kind: string; type: string; title: string; at: string | null };

const qs = (params: Record<string, string | number | boolean | undefined | null>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") s.set(k, String(v));
  }
  const out = s.toString();
  return out ? `?${out}` : "";
};

const B = "/v1/admin/merchants";

export const merchants = {
  list: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<MerchantRow[]>(`${B}${qs(params)}`, t),
  create: (
    t: string,
    body: { email: string; company_name: string; auto_activate?: boolean; send_invite?: boolean }
  ) =>
    adminFetch<MerchantDetail & { onboarding: MerchantOnboarding }>(`${B}`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  facets: (t: string) =>
    adminFetch<{
      statuses: Array<{ value: string; count: number }>;
      payment_terms: Array<{ value: string; count: number }>;
    }>(`${B}/facets`, t),
  stats: (t: string) => adminFetch<MerchantStats>(`${B}/stats`, t),
  detail: (t: string, id: string) => adminFetch<MerchantDetail>(`${B}/${id}`, t),
  approve: (t: string, id: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/approve`, t, { method: "POST" }),
  suspend: (t: string, id: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/suspend`, t, { method: "POST" }),
  update: (
    t: string,
    id: string,
    body: {
      payment_terms?: string;
      credit_limit_cents?: number;
      pricing_config?: Record<string, unknown>;
    }
  ) => adminFetch<MerchantDetail>(`${B}/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  orders: (t: string, id: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<MerchantOrder[]>(`${B}/${id}/orders${qs(params)}`, t),
  locations: (t: string, id: string) => adminFetch<MerchantLocations>(`${B}/${id}/locations`, t),
  team: (t: string, id: string) => adminFetch<MerchantTeamUser[]>(`${B}/${id}/team`, t),
  onboarding: (t: string, id: string) => adminFetch<MerchantOnboarding>(`${B}/${id}/onboarding`, t),
  inviteOwner: (t: string, id: string, email: string) =>
    adminFetch<{
      merchant_user_id: string;
      email: string;
      role: string;
      invitation_status: string;
    }>(`${B}/${id}/invite-owner`, t, { method: "POST", body: JSON.stringify({ email }) }),
  inviteTeamMember: (t: string, id: string, email: string, role: string) =>
    adminFetch<{
      merchant_user_id: string;
      email: string;
      role: string;
      invitation_status: string;
    }>(`${B}/${id}/team/invite`, t, { method: "POST", body: JSON.stringify({ email, role }) }),
  activateUsers: (t: string, id: string, email?: string) =>
    adminFetch<{ activated: number; emails: string[] }>(`${B}/${id}/activate-users`, t, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  completeOnboarding: (t: string, id: string, email?: string) =>
    adminFetch<{ merchant_id: string; status: string; onboarding: MerchantOnboarding }>(
      `${B}/${id}/complete-onboarding`,
      t,
      { method: "POST", body: JSON.stringify({ email }) }
    ),
  api: (t: string, id: string) => adminFetch<MerchantApi>(`${B}/${id}/api`, t),
  analytics: (t: string, id: string) => adminFetch<MerchantAnalytics>(`${B}/${id}/analytics`, t),
  timeline: (t: string, id: string) => adminFetch<TimelineEvent[]>(`${B}/${id}/timeline`, t),
  contacts: (t: string, id: string) => adminFetch<Contact[]>(`${B}/${id}/contacts`, t),
  contracts: (t: string, id: string) => adminFetch<Contract[]>(`${B}/${id}/contracts`, t),
  invoices: (t: string, id: string) => adminFetch<Invoice[]>(`${B}/${id}/invoices`, t),
  activities: (t: string, id: string) => adminFetch<Activity[]>(`${B}/${id}/activities`, t),
  tasks: (t: string, id: string) => adminFetch<Task[]>(`${B}/${id}/tasks`, t),
};

export function healthTone(score: number): string {
  if (score >= 70) return "green";
  if (score >= 40) return "amber";
  return "red";
}
