import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bell,
  BookOpen,
  Building2,
  Car,
  CreditCard,
  FileText,
  Flag,
  Globe,
  Headphones,
  Key,
  Layers,
  Lock,
  Mail,
  Map,
  MapPin,
  MessageSquare,
  Package,
  Palette,
  Plug,
  Server,
  Shield,
  Smartphone,
  Store,
  Truck,
  UserCog,
  Users,
  Wrench,
  Zap,
  Code,
} from "lucide-react";

export type SettingsGroupId =
  | "overview"
  | "company"
  | "access"
  | "communications"
  | "integrations"
  | "operations"
  | "modules"
  | "platform";

export const SETTINGS_GROUP_LABELS: Record<SettingsGroupId, string> = {
  overview: "Overview",
  company: "Company",
  access: "Access & Security",
  communications: "Communications",
  integrations: "Integrations",
  operations: "Operations",
  modules: "Business Modules",
  platform: "Platform",
};

export const SECTION_ICONS: Record<string, LucideIcon> = {
  dashboard: Activity,
  general: Building2,
  branding: Palette,
  users: Users,
  roles: Shield,
  authentication: Lock,
  security: Key,
  notifications: Bell,
  email: Mail,
  sms: MessageSquare,
  push: Smartphone,
  fleetbase: Truck,
  google_maps: Map,
  stripe: CreditCard,
  firebase: Zap,
  storage: Server,
  api_keys: Key,
  integrations: Plug,
  vehicles: Car,
  service_areas: Globe,
  delivery_zones: MapPin,
  booking: BookOpen,
  merchant: Store,
  driver: Truck,
  customer: Users,
  operations: Layers,
  finance: CreditCard,
  documents: FileText,
  claims: Shield,
  support: Headphones,
  reports: Activity,
  automation: Wrench,
  feature_flags: Flag,
  audit: FileText,
  backup: Server,
  logs: FileText,
  maintenance: Wrench,
  developer: Code,
};

export const SECTION_DESCRIPTIONS: Record<string, string> = {
  dashboard: "System health, integration status, and recent configuration activity.",
  general: "Company identity, timezone, support contacts, and business hours.",
  branding: "Portal colors, typography, and customer-facing brand tokens.",
  users: "Staff, drivers, merchants, and customers — Porterchain provisioning and Clerk identity status.",
  roles: "Enterprise RBAC matrix — Porterchain owns permissions, not Clerk.",
  authentication: "Session policy, MFA requirements, and allowed email domains.",
  security: "Rate limits, IP allow lists, and password policy thresholds.",
  notifications: "Template catalog and channel defaults for the Notification Engine.",
  email: "SMTP delivery status — credentials remain in environment variables.",
  sms: "SMS provider status — phone verification is handled by Clerk.",
  push: "Firebase push notification status for driver and customer apps.",
  fleetbase: "Logistics execution bridge — dispatch, GPS, routes, POD (adapter only).",
  google_maps: "Geocoding and routing engine configuration status.",
  stripe: "Payments and checkout — Stripe secrets are never exposed in UI.",
  firebase: "Mobile push and realtime — project ID status only.",
  storage: "Document and media storage backend status.",
  api_keys: "Merchant API keys and webhook signing — managed per merchant.",
  integrations: "Cross-integration overview and adapter health.",
  vehicles: "Fleet vehicle classes, capacity limits, booking channels, and catalog management.",
  service_areas: "Geographic service coverage and active regions.",
  delivery_zones: "Zone-based pricing and SLA overrides.",
  booking: "Quote TTL, draft retention, currency, and default vehicle class.",
  merchant: "Default payment terms, credit limits, and onboarding policy.",
  driver: "Background checks, document expiry alerts, and fleet compliance.",
  customer: "Customer portal, self-service booking, and tracking notifications.",
  operations: "Dispatch control tower — link to live operations module.",
  finance: "Invoice prefixes, tax defaults — tariffs live in Pricing Center.",
  documents: "Upload limits, allowed MIME types, and retention policy.",
  claims: "Investigation SLA and compensation caps.",
  support: "SLA tiers and macros — owned by Support Center module.",
  reports: "Scheduled and saved reports — owned by Reports module.",
  automation: "Queue retries and dispatch sync intervals.",
  feature_flags: "Gradual rollout toggles for beta and experimental features.",
  audit: "Immutable trail of settings changes with actor and reason.",
  backup: "Export/import runtime configuration — DB backups are infra-managed.",
  logs: "Application log retention and observability pointers.",
  maintenance: "Environment, version, and maintenance window policy.",
  developer: "API docs, webhooks, and developer portal configuration.",
};

export type ConfigFieldType = "text" | "email" | "number" | "boolean" | "select" | "color" | "textarea" | "json";

export type ConfigFieldDef = {
  key: string;
  label: string;
  type: ConfigFieldType;
  hint?: string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  step?: number;
};

export const CONFIG_FIELD_SCHEMAS: Record<string, ConfigFieldDef[]> = {
  general: [
    { key: "company_name", label: "Company name", type: "text" },
    { key: "legal_name", label: "Legal name", type: "text" },
    { key: "timezone", label: "Timezone", type: "select", options: [
      { value: "America/Toronto", label: "America/Toronto (ET)" },
      { value: "America/Vancouver", label: "America/Vancouver (PT)" },
      { value: "America/Chicago", label: "America/Chicago (CT)" },
      { value: "UTC", label: "UTC" },
    ]},
    { key: "support_email", label: "Support email", type: "email" },
    { key: "business_hours.mon_fri", label: "Mon–Fri hours", type: "text", hint: "e.g. 08:00-18:00" },
    { key: "business_hours.sat", label: "Saturday hours", type: "text", hint: "e.g. 09:00-14:00" },
  ],
  branding: [
    { key: "primary_color", label: "Primary color", type: "color" },
    { key: "secondary_color", label: "Secondary color", type: "color" },
    { key: "typography", label: "Font family", type: "select", options: [
      { value: "Inter", label: "Inter" },
      { value: "DM Sans", label: "DM Sans" },
      { value: "Plus Jakarta Sans", label: "Plus Jakarta Sans" },
    ]},
  ],
  authentication: [
    { key: "session_timeout_minutes", label: "Session timeout (minutes)", type: "number", min: 15, max: 1440 },
    { key: "mfa_required", label: "Require MFA for staff", type: "boolean" },
    { key: "allowed_domains", label: "Allowed email domains", type: "json", hint: "JSON array, e.g. [\"porterchain.com\"]" },
  ],
  security: [
    { key: "rate_limit_per_minute", label: "API rate limit / minute", type: "number", min: 10, max: 10000 },
    { key: "password_min_length", label: "Minimum password length", type: "number", min: 8, max: 128 },
    { key: "ip_allow_list", label: "IP allow list", type: "json", hint: "Empty array = no restriction" },
  ],
  booking: [
    { key: "quote_ttl_minutes", label: "Quote TTL (minutes)", type: "number", min: 5, max: 1440 },
    { key: "booking_draft_ttl_minutes", label: "Draft TTL (minutes)", type: "number", min: 60, max: 10080 },
    { key: "default_currency", label: "Default currency", type: "select", options: [
      { value: "cad", label: "CAD" },
      { value: "usd", label: "USD" },
    ]},
    { key: "default_vehicle_class", label: "Default vehicle", type: "select", options: [
      { value: "sedan", label: "Sedan" },
      { value: "suv", label: "SUV" },
      { value: "cargo_van", label: "Cargo Van" },
      { value: "box_truck", label: "Box Truck" },
    ]},
  ],
  merchant: [
    { key: "default_payment_terms", label: "Default payment terms", type: "select", options: [
      { value: "NET_15", label: "Net 15" },
      { value: "NET_30", label: "Net 30" },
      { value: "NET_45", label: "Net 45" },
      { value: "PREPAID", label: "Prepaid" },
    ]},
    { key: "default_credit_limit_cents", label: "Default credit limit (¢)", type: "number", min: 0 },
    { key: "approval_required", label: "Require admin approval", type: "boolean" },
  ],
  driver: [
    { key: "background_check_required", label: "Background check required", type: "boolean" },
    { key: "document_expiry_alert_days", label: "Document expiry alert (days)", type: "number", min: 1, max: 365 },
  ],
  customer: [
    { key: "portal_enabled", label: "Customer portal enabled", type: "boolean" },
    { key: "booking_self_service", label: "Self-service booking", type: "boolean" },
    { key: "tracking_notifications", label: "Tracking notifications", type: "boolean" },
  ],
  finance: [
    { key: "invoice_number_prefix", label: "Invoice prefix", type: "text" },
    { key: "receipt_number_prefix", label: "Receipt prefix", type: "text" },
    { key: "default_tax_percent", label: "Default tax %", type: "number", min: 0, max: 100, step: 0.1 },
  ],
  documents: [
    { key: "max_file_size_mb", label: "Max file size (MB)", type: "number", min: 1, max: 500 },
    { key: "retention_days", label: "Retention (days)", type: "number", min: 30, max: 3650 },
    { key: "allowed_types", label: "Allowed file types", type: "json", hint: 'e.g. ["pdf","jpg","png"]' },
  ],
  claims: [
    { key: "investigation_sla_hours", label: "Investigation SLA (hours)", type: "number", min: 1, max: 720 },
    { key: "max_compensation_cents", label: "Max compensation (¢)", type: "number", min: 0 },
  ],
  automation: [
    { key: "queue_retry_max", label: "Max queue retries", type: "number", min: 0, max: 20 },
    { key: "dispatch_retry_seconds", label: "Dispatch retry interval (s)", type: "number", min: 5, max: 3600 },
  ],
};

export const FEATURE_FLAG_LABELS: Record<string, string> = {
  beta_live_map: "Live Map (beta)",
  beta_order_360: "Order 360 view (beta)",
  experimental_ai_summary: "AI summary (experimental)",
};

/** Nested get/set helpers for dotted field keys */
export function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

export function setNestedValue(obj: Record<string, unknown>, path: string, value: unknown): Record<string, unknown> {
  const parts = path.split(".");
  const next = { ...obj };
  let cur: Record<string, unknown> = next;
  for (let i = 0; i < parts.length - 1; i++) {
    const p = parts[i];
    const child = cur[p];
    cur[p] = typeof child === "object" && child !== null ? { ...(child as Record<string, unknown>) } : {};
    cur = cur[p] as Record<string, unknown>;
  }
  cur[parts[parts.length - 1]] = value;
  return next;
}
