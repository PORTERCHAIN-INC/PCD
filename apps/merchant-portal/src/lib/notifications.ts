import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type InboxNotification = {
  id: string;
  title: string;
  body: string;
  priority: string;
  category: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at: string;
};

async function notificationsFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (rest.body) headers["Content-Type"] = "application/json";
  if (orgId) headers["X-Merchant-Org-Id"] = orgId;
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: { ...headers, ...(rest.headers as Record<string, string>) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const notificationsApi = {
  markRead: (token: string, notificationId: string, orgId?: string) =>
    notificationsFetch<{ ok: boolean }>(`/v1/notifications/inbox/${notificationId}/read`, token, {
      method: "POST",
      orgId,
    }),

  markAllRead: (token: string, orgId?: string) =>
    notificationsFetch<{ ok: boolean; marked: number }>(
      "/v1/notifications/inbox/mark-all-read",
      token,
      { method: "POST", orgId }
    ),

  inbox: (token: string, orgId?: string, limit = 20) =>
    notificationsFetch<{ unread_count: number; items: InboxNotification[] }>(
      `/v1/notifications/inbox?limit=${limit}`,
      token,
      { orgId }
    ),
};
