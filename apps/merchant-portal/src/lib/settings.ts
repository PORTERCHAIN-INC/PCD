import type {
  CustomerExperienceResponse,
  CustomerExperienceSettings,
} from "@/lib/customerExperience";
import { publicEnv } from "@/lib/env";
import type { ContractPricing } from "@/lib/billing";

const API_BASE = publicEnv.porterchainApiUrl;

export type SettingsCoverageZone = {
  code: string;
  name: string;
};

export type SettingsAssignedVehicle = {
  id: string;
  label: string;
};

export type SettingsCoverage = {
  service_area: string;
  service_area_note: string;
  delivery_zones: SettingsCoverageZone[];
  assigned_vehicles: SettingsAssignedVehicle[];
  assigned_vehicle_ids: string[];
  coverage_note: string;
};

export type SettingsProfile = {
  id: string;
  status: string;
  company_name: string;
  legal_name: string | null;
  email: string;
  phone: string | null;
  website: string | null;
  industry: string | null;
  payment_terms: string;
  billing_cycle: string | null;
  hst_number: string | null;
  business_number: string | null;
  billing_address: Record<string, unknown> | null;
  preferred_vehicles: string[] | null;
  delivery_zones: string[] | null;
  identity_meta?: { updated_by?: string; updated_at?: string } | null;
  coverage?: SettingsCoverage | null;
};

export type NotificationPrefs = {
  order_booked: boolean;
  order_delivered: boolean;
  order_failed: boolean;
  invoice_generated: boolean;
  payment_received: boolean;
  claim_updates: boolean;
  support_replies: boolean;
  weekly_summary: boolean;
  channels: { email: boolean; in_app: boolean };
};

export type BrandingPrefs = {
  logo_url: string | null;
  primary_color: string;
  accent_color: string;
  tracking_page_message: string | null;
};

export type BillingContact = {
  id: string;
  name: string;
  email: string;
  phone?: string | null;
  role?: string;
  is_primary?: boolean;
};

export type Warehouse = {
  id: string;
  name: string;
  formatted: string;
  lat?: number | null;
  lng?: number | null;
  postal?: string | null;
  is_default?: boolean;
};

export type PickupLocation = {
  id: string;
  label: string;
  address_type: string;
  formatted: string;
  is_default: boolean;
};

export type BusinessDocument = {
  id: string;
  name: string;
  type: string;
  reference?: string | null;
  uploaded_at: string;
};

export type TaxLegalMeta = {
  updated_by?: string;
  updated_at?: string;
  actor_id?: string | null;
  fields?: string[];
};

export type TaxInfo = {
  hst_number: string | null;
  business_number: string | null;
  legal_name: string | null;
  tax_exempt: boolean;
  tax_region: string;
  billing_address: Record<string, unknown> | null;
  tax_legal_meta?: TaxLegalMeta | null;
};

export type PrivacyAuditLog = {
  id: string;
  action: string;
  summary: string;
  created_at: string | null;
};

export type PrivacyStatus = {
  status: "none" | "pending" | "erased";
  delete_requested_at: string | null;
  delete_reference: string | null;
  delete_reason: string | null;
  erased_at: string | null;
  erased_by: string | null;
  sla_days: number | null;
  message: string;
  recent_logs?: PrivacyAuditLog[];
};

export type ShopifyPrivacyRequest = {
  id: string;
  topic: string;
  status: string;
  received_at: string | null;
  due_at: string | null;
  orders_touched: number;
  hold_reason: string | null;
  download: boolean;
};

export type PrivacyDeleteResponse = {
  reference: string;
  status: string;
  sla_days: number;
  message: string;
};

export type QuietHours = {
  quiet_hours_enabled: boolean;
  quiet_start_hour: number;
  quiet_end_hour: number;
  timezone: string;
};

export type SettingsOverview = {
  profile: SettingsProfile;
  notifications: NotificationPrefs;
  branding: BrandingPrefs;
  billing_contacts: BillingContact[];
  warehouses: Warehouse[];
  pickup_locations: PickupLocation[];
  documents: BusinessDocument[];
  tax: TaxInfo;
  contract: ContractPricing;
  privacy?: PrivacyStatus;
  quiet_hours?: QuietHours;
  completeness?: {
    complete: boolean;
    missing: string[];
    missing_labels: string[];
    can_edit: boolean;
  } | null;
};

export type TimelineEntry = {
  label?: string;
  at?: string;
  created_at?: string;
  occurred_at?: string;
  actor_type?: string;
};

export type SupportTicket = {
  ticket_id: string;
  ticket_number?: string;
  subject?: string;
  description?: string | null;
  status?: string;
  priority?: string;
  category?: string;
  order_number?: string;
  created_at?: string;
  timeline?: TimelineEntry[];
};

export type ClaimRow = {
  claim_id: string;
  claim_number?: string;
  claim_type?: string;
  status?: string;
  description?: string | null;
  order_id?: string;
  order_number?: string;
  tracking_number?: string;
  created_at?: string;
  timeline?: TimelineEntry[];
};

export type AuditLogRow = {
  id: string;
  action: string;
  summary: string;
  created_at: string | null;
};

export type AuditSnapshot = {
  merchant_id: string;
  audit_log_count: number;
  recent_audit_logs: AuditLogRow[];
};

export type KbArticle = {
  id: string;
  title: string;
  body: string;
  category_id: string;
};

async function settingsFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Porterchain-Portal": "merchant",
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  if (rest.body && !(rest.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
    });
  } catch {
    throw new Error(
      "Could not reach PorterChain settings. Check your connection and try again — if this continues, contact PorterChain support."
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    throw new Error(
      typeof detail === "string" ? detail : `Could not load settings (${response.status})`
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const settingsApi = {
  overview: (token: string, orgId?: string) =>
    settingsFetch<SettingsOverview>("/v1/merchant/settings/overview", token, { orgId }),

  updateProfile: (token: string, body: Partial<SettingsProfile>, orgId?: string) =>
    settingsFetch<SettingsProfile>("/v1/merchant/profile", token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  updateNotifications: (token: string, body: Partial<NotificationPrefs>, orgId?: string) =>
    settingsFetch<NotificationPrefs>("/v1/merchant/settings/notifications", token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  customerExperience: (token: string, orgId?: string) =>
    settingsFetch<CustomerExperienceResponse>("/v1/merchant/settings/customer-experience", token, {
      orgId,
    }),

  updateCustomerExperience: (
    token: string,
    body: Partial<CustomerExperienceSettings> & { preset?: string },
    orgId?: string
  ) =>
    settingsFetch<CustomerExperienceResponse>("/v1/merchant/settings/customer-experience", token, {
      method: "PUT",
      body: JSON.stringify(body),
      orgId,
    }),

  updateBranding: (token: string, body: Partial<BrandingPrefs>, orgId?: string) =>
    settingsFetch<BrandingPrefs>("/v1/merchant/settings/branding", token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  addBillingContact: (
    token: string,
    body: { name: string; email: string; phone?: string },
    orgId?: string
  ) =>
    settingsFetch<BillingContact>("/v1/merchant/settings/billing-contacts", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  listBillingContacts: (token: string, orgId?: string) =>
    settingsFetch<BillingContact[]>("/v1/merchant/settings/billing-contacts", token, { orgId }),

  deleteBillingContact: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/settings/billing-contacts/${id}`, token, {
      method: "DELETE",
      orgId,
    }),

  patchBillingContact: (
    token: string,
    id: string,
    body: { name?: string; email?: string; phone?: string; is_primary?: boolean },
    orgId?: string
  ) =>
    settingsFetch<BillingContact>(`/v1/merchant/settings/billing-contacts/${id}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  addWarehouse: (
    token: string,
    body: { name: string; formatted: string; postal?: string; is_default?: boolean },
    orgId?: string
  ) =>
    settingsFetch<Warehouse>("/v1/merchant/settings/warehouses", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  deleteWarehouse: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/settings/warehouses/${id}`, token, {
      method: "DELETE",
      orgId,
    }),

  addPickup: (
    token: string,
    body: {
      label: string;
      formatted: string;
      postal?: string;
      address_type?: string;
      is_default?: boolean;
      lat?: number;
      lng?: number;
      place_id?: string;
    },
    orgId?: string
  ) =>
    settingsFetch<PickupLocation>("/v1/merchant/addresses", token, {
      method: "POST",
      body: JSON.stringify({ ...body, address_type: body.address_type || "pickup" }),
      orgId,
    }),

  deletePickup: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/addresses/${id}`, token, { method: "DELETE", orgId }),

  setDefaultPickup: (token: string, id: string, orgId?: string) =>
    settingsFetch<PickupLocation>(`/v1/merchant/addresses/${id}/default`, token, {
      method: "POST",
      orgId,
    }),

  addDocument: (
    token: string,
    body: { name: string; doc_type: string; reference?: string },
    orgId?: string
  ) =>
    settingsFetch<BusinessDocument>("/v1/merchant/settings/documents", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  deleteDocument: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/settings/documents/${id}`, token, {
      method: "DELETE",
      orgId,
    }),

  updateTax: (
    token: string,
    body: {
      hst_number?: string | null;
      business_number?: string | null;
      tax_exempt?: boolean;
      tax_region?: string;
    },
    orgId?: string
  ) =>
    settingsFetch<TaxInfo>("/v1/merchant/settings/tax", token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  supportTickets: (token: string, orgId?: string) =>
    settingsFetch<SupportTicket[]>("/v1/merchant/support/tickets", token, { orgId }),

  getTicket: (token: string, ticketId: string, orgId?: string) =>
    settingsFetch<SupportTicket>(`/v1/merchant/support/tickets/${ticketId}`, token, { orgId }),

  createTicket: (
    token: string,
    body: { subject: string; description?: string; category?: string; order_id?: string },
    orgId?: string
  ) =>
    settingsFetch<SupportTicket>("/v1/merchant/support/tickets", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  knowledgeBase: (token: string, orgId?: string) =>
    settingsFetch<{ articles: KbArticle[]; faq: Array<{ question: string; answer: string }> }>(
      "/v1/merchant/support/knowledge-base",
      token,
      { orgId }
    ),

  claims: (token: string, orgId?: string) =>
    settingsFetch<ClaimRow[]>("/v1/merchant/claims", token, { orgId }),

  getClaim: (token: string, claimId: string, orgId?: string) =>
    settingsFetch<ClaimRow>(`/v1/merchant/claims/${claimId}`, token, { orgId }),

  openClaim: (
    token: string,
    body: { order_id?: string; order_number?: string; claim_type: string; description?: string },
    orgId?: string
  ) =>
    settingsFetch<ClaimRow>("/v1/merchant/claims", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  auditLogs: (token: string, orgId?: string, limit = 50) =>
    settingsFetch<AuditSnapshot>(`/v1/merchant/audit-logs?limit=${limit}`, token, { orgId }),

  recipients: (token: string, orgId?: string) =>
    settingsFetch<
      Array<{
        id: string;
        name: string;
        email?: string | null;
        phone?: string | null;
        company?: string | null;
      }>
    >("/v1/merchant/recipients", token, { orgId }),

  addRecipient: (
    token: string,
    body: { name: string; email?: string; phone?: string; company?: string },
    orgId?: string
  ) =>
    settingsFetch<{ id: string; name: string }>("/v1/merchant/recipients", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  deleteRecipient: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/recipients/${id}`, token, { method: "DELETE", orgId }),

  privacyStatus: (token: string, orgId?: string) =>
    settingsFetch<PrivacyStatus>("/v1/merchant/privacy", token, { orgId }),

  exportPrivacy: (token: string, orgId?: string) =>
    settingsFetch<Record<string, unknown>>("/v1/merchant/privacy/export", token, { orgId }),

  requestDeletion: (token: string, reason?: string, orgId?: string) =>
    settingsFetch<PrivacyDeleteResponse>("/v1/merchant/privacy/delete-request", token, {
      method: "POST",
      body: JSON.stringify({ reason: reason || null }),
      orgId,
    }),

  shopifyPrivacyRequests: (token: string, orgId?: string) =>
    settingsFetch<{ requests: ShopifyPrivacyRequest[] }>(
      "/v1/merchant/shopify/privacy/requests",
      token,
      { orgId }
    ),

  shopifyPrivacyExport: (token: string, requestId: string, orgId?: string) =>
    settingsFetch<Record<string, unknown>>(
      `/v1/merchant/shopify/privacy/requests/${requestId}/export`,
      token,
      { orgId }
    ),
};
