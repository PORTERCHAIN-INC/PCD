import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type TeamMember = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
};

export type ActivityLogEntry = {
  id: string;
  action: string;
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
};

export type PermissionsCatalog = {
  roles: RoleDefinition[];
  modules: Array<{ module: string; roles: string[] }>;
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

async function teamFetch<T>(
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

  invite: (token: string, email: string, role: string, orgId?: string) =>
    teamFetch<TeamMember>("/v1/merchant/team/invite", token, {
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
};
