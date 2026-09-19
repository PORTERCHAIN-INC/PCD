import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type TeamMember = {
  id: string;
  email: string;
  role: string;
  role_label?: string;
  is_active: boolean;
  seat_status?: "pending" | "active" | "off";
  seat_status_label?: string;
  created_at: string;
};

export type ActivityLogEntry = {
  id: string;
  action: string;
  summary?: string;
  resource_type: string;
  resource_id: string | null;
  actor_user_id: string | null;
  payload: Record<string, unknown>;
  created_at: string | null;
};

export type RoleDefinition = {
  role: string;
  label: string;
  modules: string[];
  module_labels?: string[];
};

export type PermissionsCatalog = {
  roles: RoleDefinition[];
  modules: Array<{
    module: string;
    label?: string;
    roles: string[];
    role_labels?: string[];
  }>;
};

export type TwoFactorStatus = {
  enabled: boolean;
  method: string;
  enforced_org_wide: boolean;
  note: string;
};

export type TeamOverview = {
  member_count: number;
  roles: PermissionsCatalog;
  two_factor: TwoFactorStatus;
  recent_activity: ActivityLogEntry[];
};

export const ROLE_OPTIONS = [
  { value: "merchant_owner", label: "Owner" },
  { value: "merchant_admin", label: "Manager" },
  { value: "merchant_ops", label: "Dispatcher" },
  { value: "merchant_finance", label: "Accounting" },
  { value: "merchant_readonly", label: "Viewer" },
] as const;

export function merchantRoleLabel(role?: string | null): string {
  if (!role) return "";
  return ROLE_OPTIONS.find((r) => r.value === role)?.label ?? role.replace(/_/g, " ");
}

async function teamFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
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
    throw new Error(body.detail || `API error ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const teamApi = {
  overview: (token: string, orgId?: string) =>
    teamFetch<TeamOverview>("/v1/merchant/team/overview", token, { orgId }),

  members: (token: string, orgId?: string) =>
    teamFetch<TeamMember[]>("/v1/merchant/team", token, { orgId }),

  activity: (token: string, orgId?: string) =>
    teamFetch<ActivityLogEntry[]>("/v1/merchant/team/activity", token, { orgId }),

  roles: (token: string, orgId?: string) =>
    teamFetch<PermissionsCatalog>("/v1/merchant/team/roles", token, { orgId }),

  twoFactor: (token: string, orgId?: string) =>
    teamFetch<TwoFactorStatus>("/v1/merchant/team/two-factor", token, { orgId }),

  setTwoFactor: (token: string, enabled: boolean, orgId?: string) =>
    teamFetch<TwoFactorStatus>("/v1/merchant/team/two-factor", token, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
      orgId,
    }),

  addSeat: (token: string, email: string, role: string, orgId?: string) =>
    teamFetch<TeamMember>("/v1/merchant/team/seats", token, {
      method: "POST",
      body: JSON.stringify({ email, role }),
      orgId,
    }),

  remove: (token: string, userId: string, orgId?: string) =>
    teamFetch<void>(`/v1/merchant/team/${userId}`, token, { method: "DELETE", orgId }),

  updateRole: (token: string, userId: string, role: string, orgId?: string) =>
    teamFetch<TeamMember>(`/v1/merchant/team/${userId}/role`, token, {
      method: "PATCH",
      body: JSON.stringify({ role }),
      orgId,
    }),

  setActive: (token: string, userId: string, isActive: boolean, orgId?: string) =>
    teamFetch<TeamMember>(`/v1/merchant/team/${userId}`, token, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
      orgId,
    }),
};
