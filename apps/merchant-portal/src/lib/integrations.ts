import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type ApiKeyRecord = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  environment: "sandbox" | "production";
  rate_limit_per_minute: number;
  is_active: boolean;
  created_at: string;
  secret?: string | null;
};

export type WebhookRecord = {
  id: string;
  url: string;
  events: string[];
  environment: "sandbox" | "production";
  is_active: boolean;
  created_at?: string | null;
  signing_secret?: string | null;
};

export type WebhookDelivery = {
  id: string;
  webhook_id: string;
  event_type: string;
  response_status: number | null;
  success: boolean;
  attempt: number;
  error_message: string | null;
  duration_ms: number;
  next_retry_at: string | null;
  created_at: string | null;
  request_body?: Record<string, unknown>;
  response_body?: string;
};

export type IntegrationsOverview = {
  sandbox_mode: boolean;
  booking_env_preference?: "sandbox" | "live";
  api_keys_count: number;
  sandbox_keys: number;
  production_keys: number;
  webhooks_count: number;
  active_webhooks: number;
  usage: ApiUsageSummary;
  rate_limits: RateLimitRow[];
  recent_webhook_deliveries: WebhookDelivery[];
  documentation_url: string;
  erp_platforms: string[];
  erp_marketplace?: boolean;
  available_integrations?: string[];
};

export type ApiUsageSummary = {
  total_requests: number;
  error_requests: number;
  by_day: Array<{ date: string; count: number }>;
  by_path: Array<{ path: string; count: number }>;
  by_environment: Record<string, number>;
  recent: Array<{
    method: string;
    path: string;
    status_code: number;
    duration_ms: number;
    environment: string;
    created_at: string | null;
  }>;
};

export type RateLimitRow = {
  api_key_id: string;
  name: string;
  environment: string;
  rate_limit_per_minute: number;
  requests_last_minute: number;
  remaining: number;
  throttled: boolean;
};

export type ApiDoc = {
  base_url: string;
  auth_header: string;
  auth_note: string;
  sandbox_prefix: string;
  production_prefix: string;
  default_rate_limit_per_minute: number;
  default_scopes: string[];
  endpoints: Array<{
    method: string;
    path: string;
    scope: string;
    description: string;
  }>;
  webhook_signature_header: string;
  webhook_timestamp_header: string;
};

export type EventCatalogItem = { event: string; description: string };

export type ErpPlatform = {
  id: string;
  name: string;
  status: string;
  capabilities: string[];
  notes: string;
};

export type ShopifyShopConnection = {
  id: string;
  shop_domain: string;
  connected: boolean;
  installed_at: string | null;
  uninstalled_at: string | null;
  default_pickup_address_id: string | null;
  default_pickup: string | null;
  has_webhook_secret: boolean;
  carrier_registered?: boolean;
  fulfillment_service_registered?: boolean;
};

export type ShopifyGoLive = {
  ready: boolean;
  one_click_available: boolean;
  checks: {
    oauth_configured?: boolean;
    shop_connected?: boolean;
    pickup_set?: boolean;
    merchant_active?: boolean;
    has_rate_card?: boolean;
    carrier_registered?: boolean;
  };
  blocking: string[];
  /** Non-blocking reminders, e.g. switch PorterChain rates on in Shopify shipping. */
  advisories?: string[];
};

/** Who holds the store named in `?shop=`, from this company's point of view. */
export type ShopifyShopLookup = {
  shop_domain: string;
  status: "not_linked" | "disconnected" | "linked_here" | "linked_elsewhere";
  can_link: boolean;
};

export type ShopifyConnection = {
  oauth_configured: boolean;
  webhook_url: string;
  carrier_rates_url?: string;
  fulfillment_service_url?: string;
  fulfillment_callback_url?: string;
  fulfillment_service_enabled?: boolean;
  service_area?: string;
  buyer_data_purpose?: string;
  app_url?: string;
  shops: ShopifyShopConnection[];
  go_live?: ShopifyGoLive;
  hooks?: {
    ok?: boolean;
    errors?: string[];
    carrier_registered?: boolean;
    carrier_error?: string | null;
  };
  shop_lookup?: ShopifyShopLookup | null;
};

export type OAuthProvider = {
  id: string;
  name: string;
  status: string;
  authorization_url: string | null;
  scopes: string[];
};

export type CsvTemplate = {
  id: string;
  name: string;
  description: string;
  required_columns: string[];
  optional_columns: string[];
};

async function integrationsFetch<T>(
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
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : `API error ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function downloadCsv(path: string, token: string, orgId?: string, filename?: string) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Porterchain-Portal": "merchant",
      ...(orgId ? { "X-Merchant-Id": orgId } : {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string" ? body.detail : "Could not download that file."
    );
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export const integrationsApi = {
  overview: (token: string, orgId?: string) =>
    integrationsFetch<IntegrationsOverview>("/v1/merchant/integrations/overview", token, { orgId }),

  documentation: (token: string, orgId?: string) =>
    integrationsFetch<ApiDoc>("/v1/merchant/integrations/documentation", token, { orgId }),

  events: (token: string, orgId?: string) =>
    integrationsFetch<{ events: EventCatalogItem[] }>("/v1/merchant/integrations/events", token, {
      orgId,
    }),

  usage: (token: string, orgId?: string, days = 7) =>
    integrationsFetch<ApiUsageSummary>(`/v1/merchant/integrations/usage?days=${days}`, token, {
      orgId,
    }),

  rateLimits: (token: string, orgId?: string) =>
    integrationsFetch<{ limits: RateLimitRow[] }>("/v1/merchant/integrations/rate-limits", token, {
      orgId,
    }),

  sandbox: (token: string, orgId?: string) =>
    integrationsFetch<{ sandbox_mode: boolean; booking_env_preference?: "sandbox" | "live" }>(
      "/v1/merchant/integrations/sandbox",
      token,
      {
        orgId,
      }
    ),

  setSandbox: (token: string, sandbox_mode: boolean, orgId?: string) =>
    integrationsFetch<{ sandbox_mode: boolean; booking_env_preference?: "sandbox" | "live" }>(
      "/v1/merchant/integrations/sandbox",
      token,
      {
        method: "PATCH",
        body: JSON.stringify({ sandbox_mode }),
        orgId,
      }
    ),

  purgeSandbox: (token: string, confirm: string, orgId?: string) =>
    integrationsFetch<{ cancelled: number; message: string }>(
      "/v1/merchant/integrations/sandbox/purge",
      token,
      {
        method: "POST",
        body: JSON.stringify({ confirm }),
        orgId,
      }
    ),

  simulateSandbox: (
    token: string,
    body: { order_id: string; deliver_webhooks?: boolean; until_state?: string },
    orgId?: string
  ) =>
    integrationsFetch<Record<string, unknown>>(
      "/v1/merchant/integrations/sandbox/simulate",
      token,
      {
        method: "POST",
        body: JSON.stringify(body),
        orgId,
      }
    ),

  webhookLogs: (token: string, orgId?: string, webhookId?: string) =>
    integrationsFetch<WebhookDelivery[]>(
      `/v1/merchant/integrations/webhooks/logs${webhookId ? `?webhook_id=${webhookId}` : ""}`,
      token,
      { orgId }
    ),

  webhookHistory: (token: string, webhookId: string, orgId?: string) =>
    integrationsFetch<WebhookDelivery[]>(
      `/v1/merchant/integrations/webhooks/${webhookId}/history`,
      token,
      { orgId }
    ),

  testWebhook: (token: string, webhookId: string, orgId?: string) =>
    integrationsFetch<WebhookDelivery>(
      `/v1/merchant/integrations/webhooks/${webhookId}/test`,
      token,
      {
        method: "POST",
        orgId,
      }
    ),

  retryDelivery: (token: string, deliveryId: string, orgId?: string) =>
    integrationsFetch<WebhookDelivery>(
      `/v1/merchant/integrations/webhooks/deliveries/${deliveryId}/retry`,
      token,
      { method: "POST", orgId }
    ),

  updateWebhook: (
    token: string,
    webhookId: string,
    body: { url?: string; events?: string[]; is_active?: boolean; environment?: string },
    orgId?: string
  ) =>
    integrationsFetch<WebhookRecord>(`/v1/merchant/integrations/webhooks/${webhookId}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  deleteWebhook: (token: string, webhookId: string, orgId?: string) =>
    integrationsFetch<void>(`/v1/merchant/integrations/webhooks/${webhookId}`, token, {
      method: "DELETE",
      orgId,
    }),

  rotateWebhookSecret: (token: string, webhookId: string, orgId?: string) =>
    integrationsFetch<WebhookRecord>(
      `/v1/merchant/integrations/webhooks/${webhookId}/rotate-secret`,
      token,
      { method: "POST", orgId }
    ),

  updateRateLimit: (token: string, keyId: string, rate_limit_per_minute: number, orgId?: string) =>
    integrationsFetch<{ api_key_id: string; rate_limit_per_minute: number }>(
      `/v1/merchant/integrations/api-keys/${keyId}/rate-limit`,
      token,
      { method: "PATCH", body: JSON.stringify({ rate_limit_per_minute }), orgId }
    ),

  erp: (token: string, orgId?: string) =>
    integrationsFetch<{ platforms: ErpPlatform[] }>("/v1/merchant/integrations/erp", token, {
      orgId,
    }),

  oauth: (token: string, orgId?: string) =>
    integrationsFetch<{ providers: OAuthProvider[]; enabled: boolean }>(
      "/v1/merchant/integrations/oauth",
      token,
      { orgId }
    ),

  csvTemplates: (token: string, orgId?: string) =>
    integrationsFetch<{ templates: CsvTemplate[] }>(
      "/v1/merchant/integrations/csv-templates",
      token,
      {
        orgId,
      }
    ),

  downloadTemplate: (token: string, templateId: string, orgId?: string) =>
    downloadCsv(
      `/v1/merchant/integrations/csv-templates/${templateId}.csv`,
      token,
      orgId,
      `${templateId}.csv`
    ),

  console: (token: string, action: string, payload: Record<string, unknown>, orgId?: string) =>
    integrationsFetch<Record<string, unknown>>("/v1/merchant/integrations/console", token, {
      method: "POST",
      body: JSON.stringify({ action, payload }),
      orgId,
    }),

  shopify: (token: string, orgId?: string, shop?: string) =>
    integrationsFetch<ShopifyConnection>(
      shop
        ? `/v1/merchant/shopify?${new URLSearchParams({ shop }).toString()}`
        : "/v1/merchant/shopify",
      token,
      { orgId }
    ),

  shopifyInstallUrl: (token: string, shop: string, orgId?: string, pickupAddressId?: string) => {
    const qs = new URLSearchParams({ shop });
    if (pickupAddressId) qs.set("pickup_address_id", pickupAddressId);
    return integrationsFetch<{ url: string; shop_domain: string }>(
      `/v1/merchant/shopify/install-url?${qs.toString()}`,
      token,
      { orgId }
    );
  },

  shopifyConnect: (
    token: string,
    body: {
      shop_domain: string;
      admin_access_token: string;
      webhook_secret?: string;
      default_pickup_address_id?: string;
    },
    orgId?: string
  ) =>
    integrationsFetch<ShopifyConnection>("/v1/merchant/shopify", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  shopifyGoLive: (
    token: string,
    body: { shop_id?: string; pickup_address_id?: string },
    orgId?: string
  ) =>
    integrationsFetch<ShopifyConnection>("/v1/merchant/shopify/go-live", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  shopifySetPickup: (token: string, shopId: string, address_id: string, orgId?: string) =>
    integrationsFetch<{ ok: boolean }>(`/v1/merchant/shopify/${shopId}/pickup`, token, {
      method: "PUT",
      body: JSON.stringify({ address_id }),
      orgId,
    }),

  shopifyDisconnect: (token: string, shopId: string, orgId?: string) =>
    integrationsFetch<void>(`/v1/merchant/shopify/${shopId}`, token, { method: "DELETE", orgId }),

  // Existing key/webhook endpoints
  listKeys: (token: string, orgId?: string) =>
    integrationsFetch<ApiKeyRecord[]>("/v1/merchant/api-keys", token, { orgId }),

  createKey: (
    token: string,
    body: { name: string; environment: string; scopes?: string[] },
    orgId?: string
  ) =>
    integrationsFetch<ApiKeyRecord>("/v1/merchant/api-keys", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  revokeKey: (token: string, keyId: string, orgId?: string) =>
    integrationsFetch<void>(`/v1/merchant/api-keys/${keyId}`, token, { method: "DELETE", orgId }),

  listWebhooks: (token: string, orgId?: string) =>
    integrationsFetch<WebhookRecord[]>("/v1/merchant/webhooks", token, { orgId }),

  createWebhook: (
    token: string,
    body: { url: string; events: string[]; environment?: string },
    orgId?: string
  ) =>
    integrationsFetch<WebhookRecord>("/v1/merchant/webhooks", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),
};

export const WEBHOOK_EVENT_PRESETS = [
  "order.booked",
  "order.driver_assigned",
  "order.pickup_completed",
  "order.delivered",
  "order.cancelled",
  "order.*",
];
