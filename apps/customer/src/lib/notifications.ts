import { publicEnv } from "./env";

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

const API_BASE = publicEnv.porterchainApiUrl;

async function notificationsFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Porterchain-Portal": "customer",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...(init?.headers as Record<string, string>),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const notificationsApi = {
  inbox: (token: string, limit = 20) =>
    notificationsFetch<{ unread_count: number; items: InboxNotification[] }>(
      `/v1/notifications/inbox?limit=${limit}`,
      token
    ),
  markRead: (token: string, id: string) =>
    notificationsFetch<{ ok: boolean }>(`/v1/notifications/inbox/${id}/read`, token, {
      method: "POST",
    }),
  markAllRead: (token: string) =>
    notificationsFetch<{ ok: boolean; marked: number }>(
      "/v1/notifications/inbox/mark-all-read",
      token,
      { method: "POST" }
    ),
};
