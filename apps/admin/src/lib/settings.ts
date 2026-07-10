import { z } from "zod";
import { adminFetch } from "@/lib/api";

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

export type SettingsDashboard = {
  system_status: string;
  version: string;
  environment: string;
  health: Record<string, unknown>;
  recent_changes: Array<Record<string, unknown>>;
};

export type SettingsCenter = {
  dashboard: SettingsDashboard;
  sections: SettingsSection[];
  config: Record<string, unknown>;
  module_config: Record<string, unknown>;
  permissions: Record<string, string[]>;
  roles: string[];
  validation: {
    valid: boolean;
    issues: string[];
    warnings: string[];
    checked_at: string;
  };
};

export type AuditEntry = {
  action: string;
  actor_user_id: string | null;
  resource_type: string;
  resource_id: string | null;
  old_value: unknown;
  new_value: unknown;
  reason: string | null;
  created_at: string | null;
};

const B = "/v1/admin/settings";

export const CONFIG_SECTION_IDS = [
  "general",
  "branding",
  "authentication",
  "security",
  "notifications",
  "booking",
  "merchant",
  "driver",
  "customer",
  "finance",
  "documents",
  "claims",
  "automation",
  "feature_flags",
  "vehicles",
  "service_areas",
  "delivery_zones",
] as const;

export const INTEGRATION_SECTION_IDS = [
  "fleetbase",
  "stripe",
  "google_maps",
  "firebase",
  "email",
  "sms",
  "push",
  "storage",
] as const;

export const MODULE_SECTION_LINKS: Record<string, { href: string; label: string }> = {
  finance: { href: "/pricing", label: "Tax, fuel, and tariff defaults live in Pricing Center" },
  support: { href: "/support", label: "SLA, macros, and automation in Support Center" },
  pricing: { href: "/pricing", label: "Pricing rules and tariffs" },
  operations: { href: "/operations", label: "Operations control tower" },
};

export type RbacMatrixResponse = {
  matrix: {
    roles: Array<{ role: string; label: string; permissions: string[] }>;
    permissions: Array<{ permission: string; roles: string[] }>;
  };
};

export const settingsApi = {
  center: (token: string) => adminFetch<SettingsCenter>(`${B}/center`, token),
  dashboard: (token: string) => adminFetch<SettingsDashboard>(`${B}/dashboard`, token),
  health: (token: string) => adminFetch<Record<string, unknown>>(`${B}/health`, token),
  sections: (token: string) => adminFetch<SettingsSection[]>(`${B}/sections`, token),
  staff: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/staff`, token);
    return z.array(staffSchema).parse(raw);
  },
  users: async (token: string, userType: UserDirectoryTab, filters: UserDirectoryFilters = {}) => {
    const params = new URLSearchParams();
    if (filters.search) params.set("search", filters.search);
    if (filters.access_status) params.set("access_status", filters.access_status);
    if (filters.invite_status) params.set("invite_status", filters.invite_status);
    if (filters.identity_status) params.set("identity_status", filters.identity_status);
    if (filters.account_status) params.set("account_status", filters.account_status);
    if (filters.clerk_status) params.set("clerk_status", filters.clerk_status);
    const qs = params.toString();
    const raw = await adminFetch<unknown>(`${B}/users/${userType}${qs ? `?${qs}` : ""}`, token);
    return platformUsersResponseSchema.parse(raw);
  },
  createUser: (
    token: string,
    userType: UserDirectoryTab,
    body: {
      email: string;
      name?: string;
      role?: string;
      password?: string;
      send_invite?: boolean;
      merchant_id?: string;
    }
  ) =>
    adminFetch<Record<string, unknown>>(`${B}/users/${userType}`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateClerkUser: (
    token: string,
    userType: UserDirectoryTab,
    body: { clerk_user_id: string; name?: string; password?: string; banned?: boolean }
  ) =>
    adminFetch<Record<string, unknown>>(`${B}/users/${userType}/clerk`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteUser: (
    token: string,
    userType: UserDirectoryTab,
    body: { clerk_user_id?: string; platform_user_id?: string }
  ) =>
    adminFetch<void>(`${B}/users/${userType}/delete`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  authorizeUser: (
    token: string,
    userType: UserDirectoryTab,
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
  inviteStaff: (token: string, body: { email: string; role: string; name?: string }) =>
    adminFetch<StaffUser & { clerk_action: string; invitation_status: string }>(
      `${B}/staff/invite`,
      token,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),
  updateStaffRole: (token: string, userId: string, role: string, reason?: string) =>
    adminFetch<StaffUser>(`${B}/staff/${userId}/role`, token, {
      method: "PATCH",
      body: JSON.stringify({ role, reason }),
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
  permissions: (token: string) => adminFetch<Record<string, string[]>>(`${B}/permissions`, token),
  audit: (token: string) => adminFetch<AuditEntry[]>(`${B}/audit`, token),
  search: (token: string, q: string) =>
    adminFetch<Array<{ type: string; id: string; label: string }>>(
      `${B}/search?q=${encodeURIComponent(q)}`,
      token
    ),
  validate: (token: string) =>
    adminFetch<{ valid: boolean; issues: string[]; warnings: string[] }>(`${B}/validate`, token),
  exportConfig: (token: string) => adminFetch<Record<string, unknown>>(`${B}/export`, token),
  importConfig: (token: string, config: Record<string, unknown>, reason?: string) =>
    adminFetch<{ imported: number }>(`${B}/import`, token, {
      method: "POST",
      body: JSON.stringify({ config, reason }),
    }),
  rbac: (token: string) => adminFetch<RbacMatrixResponse>(`${B}/rbac`, token),
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

export function healthTone(status: string): "green" | "amber" | "red" | "gray" {
  const s = status.toLowerCase();
  if (
    s.includes("ok") ||
    s.includes("configured") ||
    s.includes("healthy") ||
    s.includes("enabled")
  )
    return "green";
  if (
    s.includes("mock") ||
    s.includes("degraded") ||
    s.includes("bypass") ||
    s.includes("disabled")
  )
    return "amber";
  if (s.includes("error") || s.includes("unconfigured") || s.includes("unavailable")) return "red";
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
