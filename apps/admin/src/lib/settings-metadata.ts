import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Building2,
  Car,
  CreditCard,
  FileText,
  Globe,
  Key,
  Lock,
  Mail,
  Map,
  Package,
  Plug,
  Server,
  Shield,
  Store,
  Tags,
  Truck,
  Users,
  Wrench,
  Zap,
} from "lucide-react";

export type SettingsGroupId =
  "overview" | "general" | "access" | "commercial" | "partners" | "connections" | "platform";

export const SETTINGS_GROUP_LABELS: Record<SettingsGroupId, string> = {
  overview: "Overview",
  general: "General",
  access: "Access",
  commercial: "Commercial",
  partners: "Partners",
  connections: "Connections",
  platform: "Platform",
};

export const SETTINGS_GROUP_ORDER: SettingsGroupId[] = [
  "overview",
  "general",
  "access",
  "commercial",
  "partners",
  "connections",
  "platform",
];

/** Old ?section= ids → canonical */
export const SECTION_ALIASES: Record<string, string> = {
  service_areas: "coverage",
  delivery_zones: "coverage",
  email: "channels",
  sms: "channels",
  push: "channels",
  notifications: "channels",
  api_keys: "dashboard",
  integrations: "dashboard",
  branding: "general",
  feature_flags: "dashboard",
  logs: "backup",
  developer: "backup",
  maintenance: "backup",
  operations: "dashboard",
  support: "dashboard",
  reports: "dashboard",
};

export const SECTION_ICONS: Record<string, LucideIcon> = {
  dashboard: Activity,
  general: Building2,
  users: Users,
  roles: Shield,
  authentication: Lock,
  security: Key,
  vehicles: Car,
  pricing: Tags,
  coverage: Globe,
  booking: Package,
  finance: CreditCard,
  documents: FileText,
  claims: Shield,
  merchant: Store,
  driver: Truck,
  customer: Users,
  fleetbase: Truck,
  google_maps: Map,
  stripe: CreditCard,
  firebase: Zap,
  storage: Server,
  channels: Mail,
  automation: Wrench,
  audit: FileText,
  backup: Server,
};

export const SECTION_DESCRIPTIONS: Record<string, string> = {
  dashboard: "Readiness of wired commercial settings and connection health.",
  general: "Company identity, timezone, and support contacts (ops reference).",
  users: "Staff, drivers, merchants, and customers — provisioning and Clerk status.",
  roles: "Staff role → module catalog (read-only). SpiceDB Checks are the authorization SoT.",
  authentication: "Owned by Clerk / staff IdP — MFA and sessions are not stored here.",
  security: "Rate limits and password policy come from environment / Clerk.",
  vehicles: "Quote vehicle catalog. Enabled flags gate retail quotes. Physical fleet is Fleetbase.",
  pricing: "GTA rate matrix, tax, and fuel — affects retail quotes immediately.",
  coverage: "Service areas and delivery zones (policy store).",
  booking: "Instant delivery SLA is wired. Quote/draft TTL are environment-owned.",
  merchant: "Partner defaults — not enforced in onboarding runtime yet.",
  driver: "Driver compliance policy — not enforced in runtime yet.",
  customer: "Customer portal policy — not enforced in runtime yet.",
  finance: "Invoice prefixes and billing defaults (policy).",
  documents: "Upload limits and retention (policy).",
  claims: "Investigation SLA and compensation caps (policy).",
  fleetbase: "Execution bridge — open console via staff SSO (adapter only).",
  google_maps: "Places autocomplete and map tiles only — not a routing engine.",
  stripe: "Payments — secrets never exposed in UI.",
  firebase: "Mobile push — project status only.",
  storage: "Document storage backend status.",
  channels: "Email / SMS / push status. Template ops live under Notifications.",
  automation: "Fleetbase sync retry policy (policy store).",
  audit: "Immutable trail of settings changes with actor and reason.",
  backup: "Export/import Settings-owned configuration.",
};

export type ConfigFieldType =
  "text" | "email" | "number" | "boolean" | "select" | "color" | "textarea" | "json";

export type ConfigFieldDef = {
  key: string;
  label: string;
  type: ConfigFieldType;
  hint?: string;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
  step?: number;
  /** Matches API binding effect */
  effect?: "wired" | "env" | "policy" | "decorative";
};

export const CONFIG_FIELD_SCHEMAS: Record<string, ConfigFieldDef[]> = {
  general: [
    { key: "company_name", label: "Company name", type: "text", effect: "policy" },
    { key: "legal_name", label: "Legal name", type: "text", effect: "policy" },
    {
      key: "timezone",
      label: "Timezone",
      type: "select",
      effect: "policy",
      options: [
        { value: "America/Toronto", label: "America/Toronto (ET)" },
        { value: "America/Vancouver", label: "America/Vancouver (PT)" },
        { value: "America/Chicago", label: "America/Chicago (CT)" },
        { value: "UTC", label: "UTC" },
      ],
    },
    { key: "support_email", label: "Support email", type: "email", effect: "policy" },
    {
      key: "business_hours.mon_fri",
      label: "Mon–Fri hours",
      type: "text",
      hint: "e.g. 08:00-18:00",
      effect: "policy",
    },
    {
      key: "business_hours.sat",
      label: "Saturday hours",
      type: "text",
      hint: "e.g. 09:00-14:00",
      effect: "policy",
    },
  ],
  booking: [
    {
      key: "instant_delivery_sla_hours",
      label: "Instant delivery SLA (hours)",
      type: "number",
      min: 0.25,
      max: 72,
      step: 0.25,
      hint: "Wired — used by Control Tower SLA",
      effect: "wired",
    },
    {
      key: "default_currency",
      label: "Default currency",
      type: "select",
      effect: "policy",
      options: [
        { value: "cad", label: "CAD" },
        { value: "usd", label: "USD" },
      ],
    },
    {
      key: "default_vehicle_class",
      label: "Default vehicle",
      type: "select",
      effect: "wired",
      options: [
        { value: "sedan", label: "Sedan" },
        { value: "suv", label: "SUV" },
        { value: "pickup", label: "Pickup" },
        { value: "cargo_van", label: "Cargo Van" },
        { value: "sprinter_van", label: "Sprinter Van" },
        { value: "box_truck", label: "Box Truck" },
      ],
    },
  ],
  merchant: [
    {
      key: "default_payment_terms",
      label: "Default payment terms",
      type: "select",
      effect: "policy",
      options: [
        { value: "NET_15", label: "Net 15" },
        { value: "NET_30", label: "Net 30" },
        { value: "NET_45", label: "Net 45" },
        { value: "PREPAID", label: "Prepaid" },
      ],
    },
    {
      key: "default_credit_limit_cents",
      label: "Default credit limit (¢)",
      type: "number",
      min: 0,
      effect: "policy",
    },
    {
      key: "approval_required",
      label: "Require admin approval",
      type: "boolean",
      effect: "policy",
    },
  ],
  driver: [
    {
      key: "background_check_required",
      label: "Background check required",
      type: "boolean",
      effect: "policy",
    },
    {
      key: "document_expiry_alert_days",
      label: "Document expiry alert (days)",
      type: "number",
      min: 1,
      max: 365,
      effect: "policy",
    },
  ],
  customer: [
    { key: "portal_enabled", label: "Customer portal enabled", type: "boolean", effect: "policy" },
    {
      key: "booking_self_service",
      label: "Self-service booking",
      type: "boolean",
      effect: "policy",
    },
    {
      key: "tracking_notifications",
      label: "Tracking notifications",
      type: "boolean",
      effect: "policy",
    },
  ],
  finance: [
    { key: "invoice_number_prefix", label: "Invoice prefix", type: "text", effect: "policy" },
    { key: "receipt_number_prefix", label: "Receipt prefix", type: "text", effect: "policy" },
    {
      key: "default_tax_percent",
      label: "Default tax %",
      type: "number",
      min: 0,
      max: 30,
      step: 0.1,
      effect: "policy",
    },
  ],
  documents: [
    {
      key: "max_file_size_mb",
      label: "Max file size (MB)",
      type: "number",
      min: 1,
      max: 100,
      effect: "policy",
    },
    {
      key: "retention_days",
      label: "Retention (days)",
      type: "number",
      min: 30,
      max: 3650,
      effect: "policy",
    },
  ],
  claims: [
    {
      key: "investigation_sla_hours",
      label: "Investigation SLA (hours)",
      type: "number",
      min: 1,
      max: 720,
      effect: "policy",
    },
    {
      key: "max_compensation_cents",
      label: "Max compensation (¢)",
      type: "number",
      min: 0,
      effect: "policy",
    },
  ],
  automation: [
    {
      key: "queue_retry_max",
      label: "Queue retry max",
      type: "number",
      min: 0,
      max: 20,
      effect: "policy",
    },
    {
      key: "dispatch_retry_seconds",
      label: "Dispatch retry (seconds)",
      type: "number",
      min: 10,
      max: 3600,
      effect: "policy",
    },
  ],
};

export function getNestedValue(obj: unknown, path: string): unknown {
  if (obj == null || typeof obj !== "object") return undefined;
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

export function setNestedValue(
  obj: Record<string, unknown>,
  path: string,
  value: unknown
): Record<string, unknown> {
  const parts = path.split(".");
  const root = { ...obj };
  let cur: Record<string, unknown> = root;
  for (let i = 0; i < parts.length - 1; i++) {
    const key = parts[i]!;
    const next = cur[key];
    const clone =
      typeof next === "object" && next !== null && !Array.isArray(next)
        ? { ...(next as Record<string, unknown>) }
        : {};
    cur[key] = clone;
    cur = clone;
  }
  cur[parts[parts.length - 1]!] = value;
  return root;
}
