import { adminFetch } from "@/lib/api";
import type { Activity, Contract, Invoice, Task } from "@/lib/crm";

export type MerchantRow = {
  id: string;
  company_name: string;
  legal_name: string | null;
  logo_url: string | null;
  status: string;
  status_label?: string;
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
  onboarding_phase_label?: string;
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
  parent_merchant_id?: string | null;
  support_tier?: string | null;
};

export type MerchantAi = {
  risk_score: string;
  payment_risk: string;
  revenue_trend: string;
  predicted_monthly_revenue_cents: number;
  renewal_risk: string;
  suggested_actions: string[];
  actions_source?: "heuristic" | "nvidia_nim" | string;
  actions_model?: string | null;
};

export const BILLING_CYCLES = ["WEEKLY", "BIWEEKLY", "MONTHLY", "CUSTOM"] as const;

/** Retail vehicle class IDs — must stay ⊆ Settings vehicle_types catalog (M-6). */
export const RETAIL_VEHICLE_OPTIONS = [
  "sedan_suv",
  "pickup",
  "cargo_van",
  "box_16",
  "box_20",
] as const;

const VEHICLE_CLASS_LABELS: Record<string, string> = {
  sedan: "Sedan / SUV",
  suv: "Sedan / SUV",
  sedan_suv: "Sedan / SUV",
  pickup: "Pickup",
  cargoVan: "Cargo van",
  cargo_van: "Cargo van",
  highRoof: "Sprinter / high-roof",
  sprinter_van: "Sprinter / high-roof",
  box16: "16 ft",
  box_16: "16 ft",
  box_truck: "16 ft",
  box20: "20 ft",
  box_20: "20 ft",
};

export function vehicleClassLabel(id: string): string {
  return VEHICLE_CLASS_LABELS[id] ?? id;
}

export type MerchantCoverage = {
  service_area: string;
  service_area_note: string;
  delivery_zones: Array<{ code: string; name: string }>;
  assigned_vehicles: Array<{ id: string; label: string }>;
  assigned_vehicle_ids: string[];
  coverage_note: string;
};

export type MerchantDetail = MerchantRow & {
  hst_number: string | null;
  business_number: string | null;
  tax_exempt?: boolean;
  tax_region?: string | null;
  tax_legal_meta?: {
    updated_by?: string;
    updated_at?: string;
    fields?: string[];
  } | null;
  identity_meta?: { updated_by?: string; updated_at?: string } | null;
  credit_limit_cents: number | null;
  available_credit_cents?: number | null;
  billing_cycle?: string;
  phone?: string | null;
  stripe_enabled?: boolean;
  cod_enabled?: boolean;
  stripe_connect_account_id?: string | null;
  documents?: Array<{
    id: string;
    name: string;
    type?: string;
    reference?: string | null;
    uploaded_at?: string;
  }>;
  billing_address: Record<string, unknown>;
  preferred_vehicles: string[];
  delivery_zones: unknown[];
  coverage?: MerchantCoverage | null;
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
    crm_outstanding_balance_cents?: number;
    api_connected: boolean;
    active_contract: boolean;
    last_activity_at: string | null;
  };
  counts: Record<string, number>;
};

export type MerchantPrivacyLog = {
  id: string;
  action: string;
  summary: string;
  created_at: string | null;
};

export type MerchantPrivacyFile = {
  status: "none" | "pending" | "erased";
  delete_requested_at: string | null;
  delete_reference: string | null;
  delete_reason: string | null;
  erased_at: string | null;
  erased_by: string | null;
  sla_days: number | null;
  message: string;
  recent_logs?: MerchantPrivacyLog[];
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

export type MerchantStandingOrder = {
  id: string;
  merchant_id: string;
  booking_template_id: string;
  template_name?: string | null;
  recurrence_rule: string;
  next_run_at: string;
  last_run_at?: string | null;
  last_order_id?: string | null;
  last_error?: string | null;
  is_active: boolean;
  created_at: string;
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
  order_source?: string | null;
  route_import_job_id?: string | null;
};

export type MerchantLocations = {
  addresses: Array<{
    id: string;
    label: string;
    address_type: string;
    formatted: string;
    postal?: string | null;
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

export type MerchantOrgContact = {
  id: string;
  first_name: string;
  last_name: string | null;
  designation: string | null;
  department: string | null;
  phone: string | null;
  mobile: string | null;
  email: string | null;
  roles: string[];
  is_primary: boolean;
  source?: string | null;
  can_delete?: boolean;
  created_at?: string | null;
};

export type MerchantBillingContact = {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  role?: string | null;
  is_primary?: boolean;
};

export type MerchantTeamUser = {
  id: string;
  email: string;
  role: string;
  role_label?: string;
  is_active: boolean;
  seat_status?: string;
  seat_status_label?: string;
  created_at: string;
  clerk_linked?: boolean;
  invite_status?: string;
  invite_status_label?: string;
};

export type MerchantOnboarding = {
  merchant_id: string;
  merchant_status: string;
  merchant_status_label?: string;
  company_name: string;
  company_email: string;
  owner_email: string;
  owner_invite_status: string;
  owner_invite_status_label?: string;
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
  shopify_shops?: Array<{
    id: string;
    shop_domain: string;
    installed: boolean;
    installed_at: string | null;
    last_webhook_at: string | null;
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

export type DimensionUnit = "cm" | "in" | "ft";
export type WeightUnit = "kg" | "lb";
export type PricingModel = "distance" | "fsa";

/** One row of a merchant's size / weight surcharge table. Null limit = unbounded. */
export type MerchantSizeTier = {
  label: string;
  surcharge_cents: number;
  max_length: number | null;
  max_width: number | null;
  max_height: number | null;
  dimension_unit: DimensionUnit;
  max_weight: number | null;
  weight_unit: WeightUnit;
};

export type MerchantGtaVehicleRates = {
  base_price: number;
  extra_km_rate: number;
  extra_pick_fee: number;
  extra_drop_fee: number;
};

export type MerchantGtaRate = {
  base_km_limit?: number;
  downtown_fee_cad?: number;
  upper_zone_fee_cad?: number;
  vehicles?: Record<string, MerchantGtaVehicleRates>;
};

export type MerchantScheduleCompact = {
  enabled: boolean;
  vehicle_classes: string[];
  max_packed_inches: number[];
  parcels_per_stop: number;
  stop_rates_cents: Array<{ max_stops: number | null; cents: number }>;
  route_minimum_cents: number;
};

export type MerchantSchedule = {
  fuel_surcharge_percent: number | null;
  fsa_miss: "fallback_distance" | "refuse";
  origin_pickup_cents: number;
  origin_pickup_vehicle_classes: string[];
  route_minimums_cents: Record<string, number>;
  compact: MerchantScheduleCompact;
  size_match: "all" | "any";
};

export const DEFAULT_MERCHANT_SCHEDULE: MerchantSchedule = {
  fuel_surcharge_percent: null,
  fsa_miss: "fallback_distance",
  origin_pickup_cents: 0,
  origin_pickup_vehicle_classes: ["cargo_van"],
  route_minimums_cents: {},
  compact: {
    enabled: false,
    vehicle_classes: ["sedan_suv", "sedan", "suv"],
    max_packed_inches: [10, 10],
    parcels_per_stop: 3,
    stop_rates_cents: [
      { max_stops: 4, cents: 1000 },
      { max_stops: null, cents: 600 },
    ],
    route_minimum_cents: 5000,
  },
  size_match: "all",
};

export type MerchantPricing = {
  pricing_model: PricingModel;
  surcharges: { downtown: boolean; upper_zone: boolean };
  size_tiers: MerchantSizeTier[];
  /** Distance overlay — omit / null means platform GTA. */
  gta_rate?: MerchantGtaRate | null;
  /** Commercial schedule knobs (fuel, pickup, mins, compact). */
  schedule?: MerchantSchedule | null;
};

/** Form shell only — GTA downtown/upper-zone fees live on the API catalog, not in this UI. */
export const DEFAULT_MERCHANT_PRICING: MerchantPricing = {
  pricing_model: "distance",
  surcharges: { downtown: false, upper_zone: false },
  size_tiers: [],
  gta_rate: null,
  schedule: { ...DEFAULT_MERCHANT_SCHEDULE },
};

export const BLANK_SIZE_TIER: MerchantSizeTier = {
  label: "",
  surcharge_cents: 0,
  max_length: null,
  max_width: null,
  max_height: null,
  dimension_unit: "cm",
  max_weight: null,
  weight_unit: "kg",
};

export type MerchantRateCardVehicle = {
  id: string;
  label: string;
  base_cents: number;
  extra_km_cents: number;
  extra_pickup_cents: number;
  extra_drop_cents: number;
};

export type MerchantRateCard = {
  pricing_model: string;
  what_wins: string;
  vehicles: MerchantRateCardVehicle[];
  included_km: number;
  size_tiers: Array<{
    label?: string;
    surcharge_cents: number;
    max_length?: number | null;
    max_width?: number | null;
    max_height?: number | null;
    dimension_unit?: string;
    max_weight?: number | null;
    weight_unit?: string;
  }>;
  surcharges: {
    downtown: boolean;
    upper_zone: boolean;
    downtown_cents?: number;
    upper_zone_cents?: number;
  };
  liftgate_cents: number;
  fuel_surcharge_percent: number;
  schedule?: MerchantSchedule;
  tax: { hst_percent: number; tax_included: boolean };
  weight: { threshold_kg: number; cents_per_kg: number };
  fsa_rate_count: number;
  platform_fsa_rate_count: number;
  currency: string;
};

export function pricingModelLabel(model: string): string {
  if (model === "fsa") return "Ontario FSA flat rates";
  if (model === "distance") return "Distance and vehicle";
  return "Distance and vehicle";
}

export type MerchantPricingDetail = MerchantPricing & {
  merchant_id: string;
  /** FSA rates targeting this merchant specifically. */
  fsa_rate_count: number;
  /** FSA rates that apply to every merchant. */
  platform_fsa_rate_count: number;
  card?: MerchantRateCard | null;
  has_custom_gta?: boolean;
  platform_gta_rate?: MerchantGtaRate | null;
};

export const merchants = {
  list: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<MerchantRow[]>(`${B}${qs(params)}`, t),
  create: (
    t: string,
    body: {
      email: string;
      company_name: string;
      auto_activate?: boolean;
      send_invite?: boolean;
      pricing?: MerchantPricing;
    }
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
  unprovisionedSignups: (t: string) =>
    adminFetch<
      Array<{
        email: string;
        name: string;
        clerk_user_id: string;
        clerk_status: string | null;
        last_sign_in_at: string | null;
        suggested_company_name: string;
      }>
    >(`${B}/unprovisioned-signups`, t),
  detail: (t: string, id: string) => adminFetch<MerchantDetail>(`${B}/${id}`, t),
  approve: (t: string, id: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/approve`, t, { method: "POST" }),
  suspend: (t: string, id: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/suspend`, t, { method: "POST" }),
  unsuspend: (t: string, id: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/unsuspend`, t, { method: "POST" }),
  reopen: (t: string, id: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/reopen`, t, { method: "POST" }),
  close: (t: string, id: string, reason: string) =>
    adminFetch<MerchantDetail>(`${B}/${id}/close`, t, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  convertToCustomer: (
    t: string,
    id: string,
    body: { owner_email?: string; write_off_ar?: boolean } = {}
  ) =>
    adminFetch<{
      customer_id: string;
      merchant_id: string;
      status: string;
      ar_written_off_cents?: number;
    }>(`${B}/${id}/convert-to-customer`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  executePrivacy: (t: string, id: string) =>
    adminFetch<{ merchant_id: string; status: string; erased_at?: string; message?: string }>(
      `${B}/${id}/privacy/execute`,
      t,
      { method: "POST" }
    ),
  privacy: (t: string, id: string) => adminFetch<MerchantPrivacyFile>(`${B}/${id}/privacy`, t),
  update: (
    t: string,
    id: string,
    body: {
      payment_terms?: string;
      credit_limit_cents?: number;
      pricing_config?: Record<string, unknown>;
      billing_cycle?: string;
      preferred_vehicles?: string[];
      delivery_zones?: string[];
      service_area?: string;
      company_name?: string;
      legal_name?: string;
      email?: string;
      website?: string;
      industry?: string;
      phone?: string;
      hst_number?: string;
      business_number?: string;
      tax_exempt?: boolean;
      tax_region?: string;
      billing_address?: Record<string, unknown>;
      stripe_enabled?: boolean;
      cod_enabled?: boolean;
      support_tier?: "standard" | "priority" | "enterprise";
      parent_merchant_id?: string | null;
    }
  ) => adminFetch<MerchantDetail>(`${B}/${id}`, t, { method: "PATCH", body: JSON.stringify(body) }),
  pricing: (t: string, id: string) => adminFetch<MerchantPricingDetail>(`${B}/${id}/pricing`, t),
  savePricing: (t: string, id: string, body: MerchantPricing) =>
    adminFetch<MerchantPricingDetail>(`${B}/${id}/pricing`, t, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  standingOrders: (t: string, id: string) =>
    adminFetch<MerchantStandingOrder[]>(`${B}/${id}/standing-orders`, t),
  deactivateStandingOrder: (t: string, id: string, standingOrderId: string) =>
    adminFetch<{ ok: boolean; id: string; is_active: boolean }>(
      `${B}/${id}/standing-orders/${standingOrderId}/deactivate`,
      t,
      { method: "POST" }
    ),
  orders: (t: string, id: string, params: Record<string, string | number | undefined> = {}) =>
    adminFetch<{ items: MerchantOrder[]; total: number; limit: number; offset: number }>(
      `${B}/${id}/orders${qs(params)}`,
      t
    ),
  locations: (t: string, id: string) => adminFetch<MerchantLocations>(`${B}/${id}/locations`, t),
  createAddress: (
    t: string,
    id: string,
    body: {
      label: string;
      address_type?: string;
      formatted: string;
      postal?: string | null;
      lat?: number | null;
      lng?: number | null;
      place_id?: string | null;
      is_default?: boolean;
    }
  ) =>
    adminFetch<MerchantLocations["addresses"][number]>(`${B}/${id}/addresses`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateAddress: (
    t: string,
    id: string,
    addressId: string,
    body: {
      label?: string;
      address_type?: string;
      formatted?: string;
      postal?: string | null;
      lat?: number | null;
      lng?: number | null;
      place_id?: string | null;
      is_default?: boolean;
    }
  ) =>
    adminFetch<MerchantLocations["addresses"][number]>(`${B}/${id}/addresses/${addressId}`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  setDefaultAddress: (t: string, id: string, addressId: string) =>
    adminFetch<MerchantLocations["addresses"][number]>(
      `${B}/${id}/addresses/${addressId}/default`,
      t,
      {
        method: "POST",
      }
    ),
  deleteAddress: (t: string, id: string, addressId: string) =>
    adminFetch<void>(`${B}/${id}/addresses/${addressId}`, t, { method: "DELETE" }),
  createRecipient: (
    t: string,
    id: string,
    body: { name: string; email?: string; phone?: string; company?: string }
  ) =>
    adminFetch<MerchantLocations["recipients"][number]>(`${B}/${id}/recipients`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateRecipient: (
    t: string,
    id: string,
    recipientId: string,
    body: { name?: string; email?: string; phone?: string; company?: string }
  ) =>
    adminFetch<MerchantLocations["recipients"][number]>(`${B}/${id}/recipients/${recipientId}`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteRecipient: (t: string, id: string, recipientId: string) =>
    adminFetch<void>(`${B}/${id}/recipients/${recipientId}`, t, { method: "DELETE" }),
  billingContacts: (t: string, id: string) =>
    adminFetch<MerchantBillingContact[]>(`${B}/${id}/billing-contacts`, t),
  createBillingContact: (
    t: string,
    id: string,
    body: { name: string; email: string; phone?: string; role?: string; is_primary?: boolean }
  ) =>
    adminFetch<MerchantBillingContact>(`${B}/${id}/billing-contacts`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  patchBillingContact: (
    t: string,
    id: string,
    contactId: string,
    body: { name?: string; email?: string; phone?: string; role?: string; is_primary?: boolean }
  ) =>
    adminFetch<MerchantBillingContact>(`${B}/${id}/billing-contacts/${contactId}`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteBillingContact: (t: string, id: string, contactId: string) =>
    adminFetch<void>(`${B}/${id}/billing-contacts/${contactId}`, t, { method: "DELETE" }),
  team: (t: string, id: string) => adminFetch<MerchantTeamUser[]>(`${B}/${id}/team`, t),
  onboarding: (t: string, id: string) => adminFetch<MerchantOnboarding>(`${B}/${id}/onboarding`, t),
  inviteOwner: (t: string, id: string, email: string) =>
    adminFetch<{
      merchant_user_id: string;
      email: string;
      role: string;
      invitation_status: string;
    }>(`${B}/${id}/owner-seat`, t, { method: "POST", body: JSON.stringify({ email }) }),
  inviteTeamMember: (t: string, id: string, email: string, role: string) =>
    adminFetch<{
      merchant_user_id: string;
      email: string;
      role: string;
      invitation_status: string;
    }>(`${B}/${id}/team/seats`, t, { method: "POST", body: JSON.stringify({ email, role }) }),
  updateTeamRole: (t: string, id: string, userId: string, role: string) =>
    adminFetch<{ id: string; email: string; role: string; is_active: boolean }>(
      `${B}/${id}/team/${userId}`,
      t,
      { method: "PATCH", body: JSON.stringify({ role }) }
    ),
  setTeamActive: (t: string, id: string, userId: string, isActive: boolean) =>
    adminFetch<{ id: string; email: string; role: string; is_active: boolean }>(
      `${B}/${id}/team/${userId}`,
      t,
      { method: "PATCH", body: JSON.stringify({ is_active: isActive }) }
    ),
  removeTeamMember: (t: string, id: string, userId: string) =>
    adminFetch<void>(`${B}/${id}/team/${userId}`, t, { method: "DELETE" }),
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
  revokeApiKey: (t: string, id: string, keyId: string) =>
    adminFetch<void>(`${B}/${id}/api-keys/${keyId}`, t, { method: "DELETE" }),
  disableWebhook: (t: string, id: string, webhookId: string) =>
    adminFetch<void>(`${B}/${id}/webhooks/${webhookId}`, t, { method: "DELETE" }),
  arPreview: (t: string, id: string) =>
    adminFetch<{
      merchant_id: string;
      merchant_name: string | null;
      payment_terms: string | null;
      billing_cycle: string | null;
      period_start: string;
      period_end: string;
      order_count: number;
      uninvoiced_cents: number;
    }>(`${B}/${id}/ar/preview`, t),
  arGenerate: (t: string, id: string) =>
    adminFetch<{
      merchant_id: string;
      period_start: string;
      period_end: string;
      created_count: number;
      skipped_count: number;
    }>(`${B}/${id}/ar/generate`, t, { method: "POST", body: "{}" }),
  subsidiaries: (t: string, id: string) =>
    adminFetch<
      Array<{
        merchant_id: string;
        company_name: string;
        status: string;
        payment_terms: string;
        parent_merchant_id: string | null;
      }>
    >(`${B}/${id}/subsidiaries`, t),
  analytics: (t: string, id: string) => adminFetch<MerchantAnalytics>(`${B}/${id}/analytics`, t),
  timeline: (t: string, id: string) => adminFetch<TimelineEvent[]>(`${B}/${id}/timeline`, t),
  contacts: (t: string, id: string) => adminFetch<MerchantOrgContact[]>(`${B}/${id}/contacts`, t),
  createContact: (
    t: string,
    id: string,
    body: {
      first_name: string;
      last_name?: string;
      email?: string;
      phone?: string;
      designation?: string;
      department?: string;
      roles?: string[];
      is_primary?: boolean;
    }
  ) =>
    adminFetch<MerchantOrgContact>(`${B}/${id}/contacts`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateContact: (
    t: string,
    id: string,
    contactId: string,
    body: {
      first_name?: string;
      last_name?: string;
      email?: string;
      phone?: string;
      designation?: string;
      department?: string;
      roles?: string[];
      is_primary?: boolean;
    }
  ) =>
    adminFetch<MerchantOrgContact>(`${B}/${id}/contacts/${contactId}`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteContact: (t: string, id: string, contactId: string) =>
    adminFetch<void>(`${B}/${id}/contacts/${contactId}`, t, { method: "DELETE" }),
  contracts: (t: string, id: string) => adminFetch<Contract[]>(`${B}/${id}/contracts`, t),
  createContract: (
    t: string,
    id: string,
    body: { net_terms?: string; value_cents?: number; status?: string } = {}
  ) =>
    adminFetch<Contract>(`${B}/${id}/contracts`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  invoices: (t: string, id: string) => adminFetch<Invoice[]>(`${B}/${id}/invoices`, t),
  creditNotes: (t: string, id: string) =>
    adminFetch<
      Array<{
        credit_note_id: string;
        order_id: string | null;
        order_number: string | null;
        tracking_number: string | null;
        amount_cents: number;
        currency: string;
        reason: string | null;
        status: string;
        created_at: string | null;
      }>
    >(`${B}/${id}/credit-notes`, t),
  statement: (t: string, id: string) =>
    adminFetch<{
      payment_terms: string;
      billing_cycle: string;
      net_terms_days: number;
      stripe_enabled: boolean;
      outstanding_balance_cents: number;
      outstanding_invoices_cents: number;
      uninvoiced_orders_cents: number;
      credit_notes_cents: number;
      monthly_orders: number;
      monthly_spend_cents: number;
      period_start: string;
      period_end: string;
    }>(`${B}/${id}/statement`, t),
  webhookDeliveries: (t: string, id: string, webhookId: string) =>
    adminFetch<
      Array<{
        id: string;
        webhook_id: string;
        status: string;
        attempt: number;
        http_status: number | null;
        error: string | null;
        created_at: string | null;
      }>
    >(`${B}/${id}/webhooks/${webhookId}/deliveries`, t),
  retryWebhookDelivery: (t: string, id: string, deliveryId: string) =>
    adminFetch<Record<string, unknown>>(`${B}/${id}/webhooks/deliveries/${deliveryId}/retry`, t, {
      method: "POST",
    }),
  updateApiKeyRateLimit: (t: string, id: string, keyId: string, rate_limit_per_minute: number) =>
    adminFetch<{ api_key_id: string; rate_limit_per_minute: number }>(
      `${B}/${id}/api-keys/${keyId}/rate-limit`,
      t,
      { method: "PATCH", body: JSON.stringify({ rate_limit_per_minute }) }
    ),
  updateContract: (
    t: string,
    id: string,
    contractId: string,
    body: { status?: string; net_terms?: string; value_cents?: number }
  ) =>
    adminFetch<Contract>(`${B}/${id}/contracts/${contractId}`, t, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  activities: (t: string, id: string) => adminFetch<Activity[]>(`${B}/${id}/activities`, t),
  tasks: (t: string, id: string) => adminFetch<Task[]>(`${B}/${id}/tasks`, t),
};

export function healthTone(score: number): string {
  if (score >= 70) return "green";
  if (score >= 40) return "amber";
  return "red";
}

/** Operator-facing copy for lifecycle / org snake_case codes (API also maps these). */
const MERCHANT_ACTION_MESSAGES: Record<string, string> = {
  close_blocked_live_orders: "Close blocked — this company still has live orders.",
  close_blocked_outstanding_ar: "Close blocked — outstanding invoices must be cleared first.",
  unsuspend_requires_suspended: "Unsuspend only works when the company is suspended.",
  reopen_requires_closed: "Reopen only works when the company is closed.",
  approve_requires_pending_or_onboarding: "Approve only works for pending or onboarding companies.",
  merchant_already_closed: "This company is already closed.",
  cannot_suspend_closed: "Closed companies cannot be suspended — use Reopen first.",
  already_suspended: "This company is already suspended.",
  suspend_requires_active: "Only active companies can be suspended.",
  parent_cannot_be_self: "A company cannot be its own parent.",
  parent_merchant_not_found: "That parent company was not found.",
  standing_order_not_found: "That standing order was not found.",
  business_number_invalid: "Enter a valid Canadian business number (9 digits, optional RTxxxx).",
  hst_number_invalid: "Enter a valid GST/HST number (BN or BN+RTxxxx).",
  tax_region_invalid: "Tax region must be a Canadian province or territory code (e.g. ON).",
  rate_limit_invalid: "Rate limit must be at least 10 requests per minute.",
  contract_not_found: "That contract was not found for this company.",
  merchant_has_no_crm_company: "Link a CRM company before managing contracts.",
  delivery_not_found: "That webhook delivery was not found.",
  api_key_not_found: "That API key was not found.",
  webhook_not_found: "That webhook was not found.",
  nothing_to_update: "Nothing to update.",
};

export function merchantActionMessage(raw: unknown, fallback = "Action failed"): string {
  const msg = raw instanceof Error ? raw.message : typeof raw === "string" ? raw : "";
  if (!msg) return fallback;
  return MERCHANT_ACTION_MESSAGES[msg] ?? msg;
}
