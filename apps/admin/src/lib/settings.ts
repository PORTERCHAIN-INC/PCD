import { z } from "zod";
import { adminFetch } from "@/lib/api";
import { healthStatus, integrationHealthSchema, type IntegrationHealth } from "@/lib/health";

const staffSchema = z.object({
  id: z.string(),
  email: z.string(),
  name: z.string().nullable().optional(),
  role: z.string(),
  created_at: z.string(),
});

export const platformUserSchema = z.object({
  id: z.string(),
  user_type: z.enum(["staff", "driver", "customer", "merchant"]),
  email: z.string(),
  name: z.string().nullable().optional(),
  role: z.string().nullable().optional(),
  status: z.string().nullable().optional(),
  organization: z.string().nullable().optional(),
  access_status: z.string(),
  invite_status: z.string(),
  identity_status: z.string(),
  status_label: z.string(),
  clerk_linked: z.boolean(),
  clerk_user_id: z.string().nullable().optional(),
  provisioned: z.boolean().default(true),
  clerk_status: z.string().nullable().optional(),
  clerk_email_verified: z.boolean().default(false),
  clerk_password_set: z.boolean().default(false),
  clerk_last_sign_in_at: z.string().nullable().optional(),
  detail_href: z.string().nullable().optional(),
  created_at: z.string(),
});

export const platformUsersFacetsSchema = z.object({
  access_status: z.record(z.string(), z.number()),
  invite_status: z.record(z.string(), z.number()),
  identity_status: z.record(z.string(), z.number()),
  account_status: z.record(z.string(), z.number()),
  clerk_status: z.record(z.string(), z.number()),
});

export const platformUsersResponseSchema = z.object({
  items: z.array(platformUserSchema),
  total: z.number(),
  facets: platformUsersFacetsSchema,
  clerk_synced: z.boolean().default(false),
  clerk_total: z.number().nullable().optional(),
});

export type StaffUser = z.infer<typeof staffSchema>;
export type PlatformUser = z.infer<typeof platformUserSchema>;
export type PlatformUsersFacets = z.infer<typeof platformUsersFacetsSchema>;
export type PlatformUsersResponse = z.infer<typeof platformUsersResponseSchema>;

export type UserDirectoryTab = "staff" | "driver" | "customer" | "merchant";

export type UserDirectoryFilters = {
  search?: string;
  access_status?: string;
  invite_status?: string;
  identity_status?: string;
  account_status?: string;
  clerk_status?: string;
};

export const CLERK_STATUS_OPTIONS = [
  { value: "", label: "All Clerk status" },
  { value: "active", label: "Active" },
  { value: "never_signed_in", label: "Never signed in" },
  { value: "banned", label: "Banned" },
  { value: "locked", label: "Locked" },
] as const;

export const ACCESS_STATUS_OPTIONS = [
  { value: "", label: "All access" },
  { value: "authorized", label: "Authorized" },
  { value: "pending_review", label: "Pending review" },
  { value: "suspended", label: "Suspended" },
  { value: "inactive", label: "Inactive" },
  { value: "not_authorized", label: "Not authorized" },
  { value: "merchant_inactive", label: "Merchant inactive" },
] as const;

export const INVITE_STATUS_OPTIONS = [
  { value: "", label: "All invites" },
  { value: "not_invited", label: "Not invited" },
  { value: "invite_pending", label: "Invite pending" },
  { value: "accepted", label: "Invite accepted" },
  { value: "revoked", label: "Invite revoked" },
  { value: "invite_failed", label: "Invite failed" },
] as const;

export const IDENTITY_STATUS_OPTIONS = [
  { value: "", label: "All Clerk" },
  { value: "registered", label: "Clerk registered" },
  { value: "invite_pending", label: "Clerk pending" },
  { value: "not_registered", label: "No Clerk account" },
] as const;

export type SettingsSection = {
  id: string;
  label: string;
  group: string;
};

export type RuntimePosture = {
  mode: "development" | "testing" | "production";
  app_env: string;
  auth_bypass_allowed: boolean;
  stripe_mock_allowed: boolean;
  requires_live_clerk: boolean;
  cookie_domain_mode: string;
  restart_required_to_change: boolean;
  change_control: string;
};

export type SettingsDashboard = {
  system_status: string;
  version: string;
  environment: string;
  project_mode?: RuntimePosture;
  health: IntegrationHealth | Record<string, unknown>;
  recent_changes: Array<Record<string, unknown>>;
};

export type RoleCatalogEntry = {
  role: string;
  label: string;
  modules: string[];
};

export type RoleCatalog = {
  roles: RoleCatalogEntry[];
  modules: Array<{ module: string; roles: string[] }>;
};

export type SettingsBinding = {
  id: string;
  storage_key: string | null;
  effect: "wired" | "env" | "policy" | "decorative" | "identity" | "status";
  readers: string[];
  ui_editable: boolean;
  summary: string;
  fields?: Array<{ key: string; effect: string }>;
  related_keys?: string[];
};

export type SettingsCenter = {
  dashboard: SettingsDashboard;
  sections: SettingsSection[];
  config: Record<string, unknown>;
  module_config: Record<string, unknown>;
  bindings?: {
    bindings: SettingsBinding[];
    aliases: Record<string, string>;
    writable: string[];
  };
  env_runtime?: {
    quote_ttl_minutes?: number;
    booking_draft_ttl_minutes?: number | null;
  };
  /** module → roles that include it (catalog, not Check SoT) */
  permissions: Record<string, string[]>;
  /** Admin role catalog entries from MODULE_PERMISSIONS */
  roles: RoleCatalogEntry[];
  role_catalog?: RoleCatalog;
  authz?: {
    engine: string;
    docs: string;
    schema: string;
  };
  validation: {
    valid: boolean;
    issues: string[];
    warnings: string[];
    commercial_ok?: boolean;
    checked_at: string;
  };
};

export type AuditEntry = {
  id?: string;
  action: string;
  actor_user_id: string | null;
  resource_type: string;
  resource_id: string | null;
  old_value: unknown;
  new_value: unknown;
  reason: string | null;
  created_at: string | null;
  restorable?: boolean;
};

const B = "/v1/admin/settings";

export const CONFIG_SECTION_IDS = [
  "general",
  "booking",
  "merchant",
  "driver",
  "customer",
  "finance",
  "documents",
  "claims",
  "automation",
] as const;

export const INTEGRATION_SECTION_IDS = [
  "fleetbase",
  "stripe",
  "google_maps",
  "firebase",
  "storage",
  "channels",
] as const;

export const ENV_OWNED_SECTION_IDS = ["authentication", "security"] as const;

export type LeadIngestSettings = {
  doppler: { configured: boolean; project: string; config: string };
  secrets: Record<string, { configured: boolean; in_runtime: boolean; in_doppler: boolean }>;
  visible: {
    META_PIXEL_ID: string;
    LINKEDIN_CONVERSION_URN: string;
    LEAD_TERRITORY_MAP_JSON: string;
    LEAD_ROUND_ROBIN_JSON: string;
    LEAD_SLA_MINUTES_JSON: string;
    REFERRAL_CREDIT_CENTS: number;
  };
  note?: string;
  save?: { ok?: boolean; written?: string[]; skipped?: string };
};

/** @deprecated stubs removed — kept empty for any residual imports */
export const MODULE_SECTION_LINKS: Record<string, { href: string; label: string }> = {};

export const settingsApi = {
  center: (token: string) => adminFetch<SettingsCenter>(`${B}/center`, token),
  dashboard: (token: string) => adminFetch<SettingsDashboard>(`${B}/dashboard`, token),
  health: async (token: string) => {
    const raw = await adminFetch<unknown>(`${B}/health`, token);
    const parsed = integrationHealthSchema.safeParse(raw);
    return parsed.success ? parsed.data : (raw as Record<string, unknown>);
  },
  sections: (token: string) => adminFetch<SettingsSection[]>(`${B}/sections`, token),
  staff: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/staff`, token);
    return z.array(staffSchema).parse(raw);
  },
  users: async (token: string, userType: UserDirectoryTab, filters: UserDirectoryFilters = {}) => {
    const params = new URLSearchParams();
    params.set("limit", "5000");
    if (filters.search) params.set("search", filters.search);
    if (filters.access_status) params.set("access_status", filters.access_status);
    if (filters.invite_status) params.set("invite_status", filters.invite_status);
    if (filters.identity_status) params.set("identity_status", filters.identity_status);
    if (filters.account_status) params.set("account_status", filters.account_status);
    if (filters.clerk_status) params.set("clerk_status", filters.clerk_status);
    const qs = params.toString();
    const raw = await adminFetch<unknown>(`${B}/users/${userType}?${qs}`, token);
    return platformUsersResponseSchema.parse(raw);
  },
  /** Driver-only create (Clerk invite and/or password). */
  createDriver: (
    token: string,
    body: {
      email: string;
      name?: string;
      password?: string;
      send_invite?: boolean;
    }
  ) =>
    adminFetch<Record<string, unknown>>(`${B}/users/driver`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Merchant seat reserve — no password / Clerk invite. */
  addMerchantSeat: (
    token: string,
    body: {
      email: string;
      name?: string;
      merchant_id: string;
      role?: string;
    }
  ) =>
    adminFetch<Record<string, unknown>>(`${B}/users/merchant`, token, {
      method: "POST",
      body: JSON.stringify({
        email: body.email,
        name: body.name,
        merchant_id: body.merchant_id,
        role: body.role ?? "merchant_ops",
      }),
    }),
  updateDriverClerk: (
    token: string,
    body: { clerk_user_id: string; name?: string; password?: string; banned?: boolean }
  ) =>
    adminFetch<Record<string, unknown>>(`${B}/users/driver/clerk`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteDriver: (token: string, body: { clerk_user_id?: string; platform_user_id?: string }) =>
    adminFetch<void>(`${B}/users/driver/delete`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  authorizeDriver: (
    token: string,
    body: {
      platform_user_id?: string;
      clerk_user_id?: string;
      email?: string;
      name?: string;
      reason?: string;
    }
  ) =>
    adminFetch<{
      platform_user_id: string;
      user_type: string;
      email: string;
      role: string | null;
      access_status: string;
      modules: string[];
      actions_taken: string[];
    }>(`${B}/users/driver/authorize`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Approve / activate portal access (driver or merchant). Staff use enroll; customers invite. */
  authorizeUser: (
    token: string,
    userType: "driver" | "merchant",
    body: {
      platform_user_id?: string;
      clerk_user_id?: string;
      email?: string;
      name?: string;
      reason?: string;
    }
  ) =>
    adminFetch<{
      platform_user_id: string;
      user_type: string;
      email: string;
      role: string | null;
      access_status: string;
      modules: string[];
      actions_taken: string[];
    }>(`${B}/users/${userType}/authorize`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  /** Re-send Clerk invite for an existing driver or customer. */
  inviteUser: (token: string, userType: "driver" | "customer", platformUserId: string) =>
    adminFetch<Record<string, unknown>>(`${B}/users/${userType}/invite`, token, {
      method: "POST",
      body: JSON.stringify({ platform_user_id: platformUserId }),
    }),
  enrollStaff: (token: string, body: { email: string; role: string; name?: string }) =>
    adminFetch<{
      admin_user_id: string;
      email: string;
      role: string;
      enrollment_token?: string | null;
      expires_at: number;
      clerk_invite: boolean;
      email_sent?: boolean;
    }>(`${B}/staff/enroll`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  reissueStaffEnrollment: (token: string, userId: string) =>
    adminFetch<{
      admin_user_id: string;
      email: string;
      role: string;
      enrollment_token?: string | null;
      expires_at: number;
      clerk_invite: boolean;
      email_sent?: boolean;
    }>(`${B}/staff/${userId}/enroll-reissue`, token, { method: "POST" }),
  recoverStaffDevice: (token: string, userId: string, reason?: string) => {
    const qs = reason ? `?reason=${encodeURIComponent(reason)}` : "";
    return adminFetch<{
      admin_user_id: string;
      email: string;
      role: string;
      enrollment_token?: string | null;
      expires_at: number;
      clerk_invite: boolean;
      email_sent?: boolean;
      passkeys_removed?: number;
      sessions_revoked?: number;
    }>(`${B}/staff/${userId}/recover-device${qs}`, token, { method: "POST" });
  },
  updateStaffRole: (token: string, userId: string, role: string, reason?: string) =>
    adminFetch<StaffUser>(`${B}/staff/${userId}/role`, token, {
      method: "PATCH",
      body: JSON.stringify({ role, reason }),
    }),
  /** Super Admin break-glass — opens portal as target for 15 minutes (audited). */
  startImpersonation: (
    token: string,
    body: { target_type: "driver" | "merchant" | "customer"; target_id: string; reason: string }
  ) =>
    adminFetch<{
      session_id: string;
      actor_email: string;
      target_type: string;
      target_id: string;
      target_email: string;
      target_label: string;
      reason: string;
      expires_at: number;
      seconds_remaining: number;
      bearer_token?: string | null;
      portal_bootstrap_url?: string | null;
    }>("/v1/admin/impersonation/start", token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  stopImpersonation: (token: string, sessionId: string) =>
    adminFetch<{ ok: boolean }>("/v1/admin/impersonation/stop", token, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),
  config: (token: string) =>
    adminFetch<{ config: Record<string, unknown>; module_config: Record<string, unknown> }>(
      `${B}/config`,
      token
    ),
  updateConfig: (token: string, key: string, value: unknown, reason?: string) =>
    adminFetch<{ key: string; value: unknown }>(`${B}/config/${key}`, token, {
      method: "PUT",
      body: JSON.stringify({ value, reason }),
    }),
  leadIngest: (token: string) => adminFetch<LeadIngestSettings>(`${B}/lead-ingest`, token),
  updateLeadIngest: (
    token: string,
    body: {
      secrets?: Record<string, string>;
      visible?: Partial<LeadIngestSettings["visible"]>;
      generate?: string[];
    }
  ) =>
    adminFetch<LeadIngestSettings>(`${B}/lead-ingest`, token, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  audit: (token: string) => adminFetch<AuditEntry[]>(`${B}/audit`, token),
  restoreAudit: (token: string, auditId: string, reason?: string) =>
    adminFetch<{ key: string; value: unknown }>(
      `${B}/audit/${encodeURIComponent(auditId)}/restore${reason ? `?reason=${encodeURIComponent(reason)}` : ""}`,
      token,
      { method: "POST" }
    ),
  search: (token: string, q: string) =>
    adminFetch<Array<{ type: string; id: string; label: string }>>(
      `${B}/search?q=${encodeURIComponent(q)}`,
      token
    ),
  validate: (token: string) =>
    adminFetch<{ valid: boolean; issues: string[]; warnings: string[] }>(`${B}/validate`, token),
  exportConfig: (token: string) => adminFetch<Record<string, unknown>>(`${B}/export`, token),
  importConfig: (token: string, config: Record<string, unknown>, reason?: string, dryRun = false) =>
    adminFetch<{
      imported?: number;
      dry_run?: boolean;
      added?: string[];
      changed?: string[];
      blocked?: string[];
      would_write?: number;
    }>(`${B}/import`, token, {
      method: "POST",
      body: JSON.stringify({ config, reason, dry_run: dryRun }),
    }),
  vehiclesOverview: (token: string) =>
    adminFetch<VehiclesOverview>(`${B}/vehicles/overview`, token),
};

export type VehicleClassConfig = {
  id: string;
  label: string;
  capacity_kg: number;
  max_length_cm?: number;
  max_width_cm?: number;
  max_height_cm?: number;
  booking_enabled?: boolean;
  retail_enabled?: boolean;
  merchant_enabled?: boolean;
  whole_vehicle_enabled?: boolean;
  allowed_presets?: string[];
  description?: string;
  sort_order?: number;
};

export type VehiclesOverview = {
  fleet_total: number;
  fleet_assigned: number;
  fleet_available: number;
  default_vehicle_class: string;
  by_class: Array<{
    vehicle_class: string;
    fleet_count: number;
    assigned_count: number;
  }>;
};

export const ADMIN_ROLES = [
  "super_admin",
  "admin",
  "dispatcher",
  "support",
  "support_lead",
  "sales",
  "sales_manager",
  "finance",
  "compliance",
  "developer",
  "marketing",
  "read_only",
  "fleet_manager",
] as const;

/** Merchant seat / team roles (aligned with SpiceDB org relations). */
export const MERCHANT_SEAT_ROLES = [
  { value: "merchant_owner", label: "Owner" },
  { value: "merchant_admin", label: "Admin" },
  { value: "merchant_ops", label: "Operations" },
  { value: "merchant_finance", label: "Finance" },
  { value: "merchant_readonly", label: "Read only" },
] as const;

export function healthTone(status: string): "green" | "amber" | "red" | "gray" {
  const tone = healthStatus(status);
  if (tone === "healthy") return "green";
  if (tone === "warning") return "amber";
  if (tone === "critical") return "red";
  return "gray";
}

export function exportSettingsJson(
  data: Record<string, unknown>,
  filename = "porterchain-settings.json"
) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
