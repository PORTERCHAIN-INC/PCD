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
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (init?.body) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
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

  inbox: (token: string, orgId?: string) =>
    notificationsFetch<{ unread_count: number; items: InboxNotification[] }>(
      "/v1/notifications/inbox",
      token,
      { orgId }
    ),
};
