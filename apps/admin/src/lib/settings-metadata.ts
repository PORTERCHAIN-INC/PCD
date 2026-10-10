import type { LucideIcon } from "lucide-react";
import {
  MapPin,
  Route,
  ScrollText,
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
  carriage: ScrollText,
  route_pricing: Route,
  driver_gps: MapPin,
  admin_access: Shield,
  booking: Package,
  finance: CreditCard,
  documents: FileText,
  claims: Shield,
  merchant: Store,
  driver: Truck,
  customer: Users,
  dispatch: Truck,
  google_maps: Map,
  stripe: CreditCard,
  firebase: Zap,
  storage: Server,
  channels: Mail,
  lead_ingest: Plug,
  automation: Wrench,
  audit: FileText,
  backup: Server,
};

export const SECTION_DESCRIPTIONS: Record<string, string> = {
  dashboard: "Readiness of wired commercial settings and connection health.",
  general: "Company name and support email are wired into invoice events and driver statements.",
  users: "Every PorterChain persona in the DB — Staff IdP for staff; Clerk identity for others.",
  roles: "Staff role → module catalog (read-only). SpiceDB Checks are the authorization SoT.",
  authentication:
    "Staff: first-party IdP (magic link + passkeys). Driver/merchant/customer: Clerk apps.",
  security:
    "API rate limits from Doppler/env. Staff sessions from IdP; portal passwords from Clerk.",
  vehicles:
    "Quote vehicle catalog. Enabled flags gate retail quotes. Physical fleet is PorterChain.",
  carriage: "Conditions of Carriage — waiting, returns, claims, coverage; contracts override.",
  driver_gps: "Live driver GPS — global switch and per-driver overrides.",
  admin_access: "Optional IP allowlist for Admin (off by default).",
  route_pricing: "Smart route coefficients with a live current-vs-new preview.",
  pricing: "GTA matrix, FSA, liftgate/weight card, tax, and fuel — quotes use these immediately.",
  coverage:
    "Active service cities gate retail quotes (empty = unrestricted). Zones remain ops notes.",
  booking: "Instant delivery SLA is wired. Quote/draft TTL are environment-owned.",
  merchant:
    "Approval gates are wired into onboarding. Payment terms and credit limit remain policy until billing reads them.",
  driver:
    "Document expiry alert days and background-check required are wired into Driver 360 / verification.",
  customer: "portal_enabled and booking_self_service gate customer access and self-serve booking.",
  finance:
    "Invoice/receipt prefixes and default tax percent apply when invoices and tax estimates are created.",
  documents:
    "Upload size and allowed types gate blog media and POD downloads. Retention remains policy.",
  claims: "Investigation SLA stamps due-at on open; max compensation caps approved payouts.",
  dispatch: "Dispatch is the PorterChain day plan.",
  google_maps: "Places autocomplete and map tiles only — not a routing engine.",
  stripe: "Payments — secrets never exposed in UI.",
  firebase: "Mobile push — project status only.",
  storage: "Document storage backend status.",
  channels:
    "Email / SMS / push health plus the locked staff push alert budget. Template ops under Notifications.",
  lead_ingest:
    "Lead webhook secrets, Meta/LinkedIn CAPI, territory map, and referral credits — saved to Doppler on write.",
  automation: "Dispatch retry settings stay on the PorterChain worker.",
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
  /** Stored as cents; staff edit dollars. */
  moneyCents?: boolean;
};

export const CONFIG_FIELD_SCHEMAS: Record<string, ConfigFieldDef[]> = {
  general: [
    { key: "company_name", label: "Company name", type: "text", effect: "wired" },
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
    { key: "support_email", label: "Support email", type: "email", effect: "wired" },
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
      label: "Default credit limit ($)",
      type: "number",
      min: 0,
      step: 0.01,
      moneyCents: true,
      effect: "policy",
    },
    {
      key: "approval_required",
      label: "Require admin approval",
      type: "boolean",
      hint: "Wired — portal walk-ins stay ONBOARDING until an admin activates",
      effect: "wired",
    },
    {
      key: "auto_activate_trusted_channels",
      label: "Auto-activate verified integration installs",
      type: "boolean",
      hint: "Wired — Shopify OAuth (and other trusted channels) skip the wait when on",
      effect: "wired",
    },
  ],
  driver: [
    {
      key: "background_check_required",
      label: "Background check required",
      type: "boolean",
      hint: "Wired — shown on driver verification status",
      effect: "wired",
    },
    {
      key: "document_expiry_alert_days",
      label: "Document expiry alert (days)",
      type: "number",
      min: 1,
      max: 365,
      hint: "Wired — Driver 360 maintenance risk window",
      effect: "wired",
    },
  ],
  customer: [
    {
      key: "portal_enabled",
      label: "Customer portal enabled",
      type: "boolean",
      hint: "Wired — blocks portal onboarding when off",
      effect: "wired",
    },
    {
      key: "booking_self_service",
      label: "Self-service booking",
      type: "boolean",
      hint: "Wired — blocks draft/booking create when off",
      effect: "wired",
    },
    {
      key: "tracking_notifications",
      label: "Tracking notifications",
      type: "boolean",
      effect: "policy",
    },
  ],
  finance: [
    {
      key: "invoice_number_prefix",
      label: "Invoice prefix",
      type: "text",
      hint: "Wired — applied on invoice create",
      effect: "wired",
    },
    {
      key: "receipt_number_prefix",
      label: "Receipt prefix",
      type: "text",
      hint: "Wired — applied on receipt create",
      effect: "wired",
    },
    {
      key: "default_tax_percent",
      label: "Default tax %",
      type: "number",
      min: 0,
      max: 30,
      step: 0.1,
      hint: "Wired — applied on invoice create and driver tax estimates",
      effect: "wired",
    },
    {
      key: "tax_name",
      label: "Tax name on invoices",
      type: "text",
      hint: "Wired — e.g. HST (Ontario) or GST",
      effect: "wired",
    },
    {
      key: "gst_hst_number",
      label: "GST/HST registration number",
      type: "text",
      hint: "One source for invoices, statements, quotes, receipts and tax reports (CRA). Format 123456789 RT0001; blank = not printed",
      effect: "wired",
    },
    {
      key: "etransfer_email",
      label: "Interac e-Transfer email",
      type: "text",
      hint: "Wired — where merchants send e-Transfers (printed on invoices)",
      effect: "wired",
    },
    {
      key: "etransfer_autodeposit",
      label: "Autodeposit on",
      type: "boolean",
      hint: "Wired — invoices say no security question is needed",
      effect: "wired",
    },
    {
      key: "merchant_cycle_invoicing",
      label: "One invoice per billing cycle",
      type: "boolean",
      hint: "Wired — net-terms merchants get one weekly/monthly invoice instead of one per delivery",
      effect: "wired",
    },
    {
      key: "tax_mode",
      label: "Prices and tax",
      type: "select",
      effect: "wired",
      hint: "Wired — Exclusive: rates are before tax and GST/HST is added on top (B2B norm). Confirm with your accountant.",
      options: [
        { value: "exclusive", label: "Exclusive — tax added on top" },
        { value: "inclusive", label: "Inclusive — prices already include tax" },
      ],
    },
    {
      key: "default_tax_province",
      label: "Default tax province",
      type: "select",
      effect: "wired",
      hint: "Wired — used when a delivery address has no province or postal code",
      options: ["ON", "QC", "BC", "AB", "MB", "SK", "NS", "NB", "NL", "PE", "YT", "NT", "NU"].map(
        (p) => ({
          value: p,
          label: p,
        })
      ),
    },
    {
      key: "collect_qst",
      label: "Collect Quebec QST",
      type: "boolean",
      hint: "Wired — only if PorterChain is registered for QST",
      effect: "wired",
    },
    {
      key: "margin_floor_pct",
      label: "Margin floor (%)",
      type: "number",
      min: 0,
      hint: "Wired — stops and routes under this margin are flagged red",
      effect: "wired",
    },
    {
      key: "margin_minutes_per_stop",
      label: "Driver minutes per stop (estimate)",
      type: "number",
      min: 1,
      hint: "Wired — used for driver cost only when no actual pay is recorded",
      effect: "wired",
    },
    {
      key: "target_stops_per_route",
      label: "Route capacity (stops per route)",
      type: "number",
      min: 1,
      hint: "Wired — Analytics fill % = stops per route ÷ this",
      effect: "wired",
    },
    {
      key: "interac_retention_years",
      label: "Keep e-Transfer records (years)",
      type: "number",
      min: 7,
      hint: "Wired — CRA books and records: at least 6 years; we keep 7",
      effect: "wired",
    },
  ],
  documents: [
    {
      key: "max_file_size_mb",
      label: "Max file size (MB)",
      type: "number",
      min: 1,
      max: 100,
      hint: "Wired — blog uploads and POD downloads",
      effect: "wired",
    },
    {
      key: "allowed_types",
      label: "Allowed types",
      type: "json",
      hint: "Wired — blog image extensions (jpg, png, …)",
      effect: "wired",
    },
    {
      key: "retention_days",
      label: "Retention (days)",
      type: "number",
      min: 30,
      max: 3650,
      hint: "Policy — no purge job yet",
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
      hint: "Wired — stamps investigation_due_at on claim open",
      effect: "wired",
    },
    {
      key: "max_compensation_cents",
      label: "Max compensation ($)",
      type: "number",
      min: 0,
      step: 0.01,
      moneyCents: true,
      hint: "Wired — rejects payouts above this cap",
      effect: "wired",
    },
  ],
  automation: [
    {
      key: "queue_retry_max",
      label: "Queue retry max",
      type: "number",
      min: 1,
      max: 20,
      hint: "Wired — worker retry max",
      effect: "wired",
    },
    {
      key: "dispatch_retry_seconds",
      label: "Dispatch retry (seconds)",
      type: "number",
      min: 5,
      max: 3600,
      hint: "Wired — first backoff delay on sync failure",
      effect: "wired",
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
