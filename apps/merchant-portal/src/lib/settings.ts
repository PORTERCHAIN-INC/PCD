import { publicEnv } from "@/lib/env";
import type { ContractPricing } from "@/lib/billing";

const API_BASE = publicEnv.porterchainApiUrl;

export type SettingsProfile = {
  id: string;
  status: string;
  company_name: string;
  legal_name: string | null;
  email: string;
  phone: string | null;
  payment_terms: string;
  billing_cycle: string;
  hst_number: string | null;
  business_number: string | null;
  billing_address: Record<string, unknown> | null;
  preferred_vehicles: string[] | null;
  delivery_zones: string[] | null;
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

export type TaxInfo = {
  hst_number: string | null;
  business_number: string | null;
  legal_name: string | null;
  tax_exempt: boolean;
  tax_region: string;
  billing_address: Record<string, unknown> | null;
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
};

export type SupportTicket = {
  ticket_id: string;
  ticket_number?: string;
  subject?: string;
  status?: string;
  priority?: string;
  category?: string;
  order_number?: string;
  created_at?: string;
};

export type ClaimRow = {
  claim_id: string;
  claim_number?: string;
  claim_type?: string;
  status?: string;
  order_number?: string;
  created_at?: string;
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
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (init?.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
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

  deleteBillingContact: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/settings/billing-contacts/${id}`, token, {
      method: "DELETE",
      orgId,
    }),

  addWarehouse: (
    token: string,
    body: { name: string; formatted: string; is_default?: boolean },
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
    body: { label: string; formatted: string; address_type?: string; is_default?: boolean },
    orgId?: string
  ) =>
    settingsFetch<PickupLocation>("/v1/merchant/addresses", token, {
      method: "POST",
      body: JSON.stringify({ ...body, address_type: body.address_type || "pickup" }),
      orgId,
    }),

  deletePickup: (token: string, id: string, orgId?: string) =>
    settingsFetch<void>(`/v1/merchant/addresses/${id}`, token, { method: "DELETE", orgId }),

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
      hst_number?: string;
      business_number?: string;
      legal_name?: string;
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

  openClaim: (
    token: string,
    body: { order_id: string; claim_type: string; description?: string },
    orgId?: string
  ) =>
    settingsFetch<ClaimRow>("/v1/merchant/claims", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

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
};
