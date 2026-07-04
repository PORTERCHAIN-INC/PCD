import type { ApiClient } from "@porterchain/mobile-api";
import type { MobileSession } from "../types";
import { persistSession } from "./session-manager";

export async function refreshDriverSession(
  apiBaseUrl: string,
  refreshToken: string
): Promise<MobileSession> {
  const res = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/driver-api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) throw new Error("refresh_failed");
  const data = (await res.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
    driver_id: string;
  };
  const expiresAt = new Date(Date.now() + data.expires_in * 1000).toISOString();
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    userId: data.driver_id,
    expiresAt,
  };
}

export async function refreshAndPersistDriverSession(apiBaseUrl: string, refreshToken: string) {
  const session = await refreshDriverSession(apiBaseUrl, refreshToken);
  await persistSession(session, "driver");
  return session;
}

export function attachTokenRefresh(
  client: ApiClient,
  options: {
    apiBaseUrl: string;
    getRefreshToken: () => string | null;
    onSessionUpdated: (session: MobileSession) => void;
    onRefreshFailed: () => void;
    appKind: "customer" | "driver";
  }
) {
  return client;
}
