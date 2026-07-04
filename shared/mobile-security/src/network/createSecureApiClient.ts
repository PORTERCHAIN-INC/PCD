import { ApiError, createApiClient, type ApiClient, type ApiClientConfig } from "@porterchain/mobile-api";
import { emitSecurityEvent } from "../audit/emitter";
import { refreshAndPersistDriverSession } from "../session/refresh";

export type SecureApiClientConfig = ApiClientConfig & {
  appKind: "customer" | "driver";
  getRefreshToken?: () => string | null | Promise<string | null>;
  onSessionRefreshed?: (accessToken: string, refreshToken?: string) => void;
};

export function createSecureApiClient(config: SecureApiClientConfig): ApiClient {
  let refreshing: Promise<string | null> | null = null;

  async function tryRefresh(): Promise<string | null> {
    if (config.appKind !== "driver" || !config.getRefreshToken) return null;
    if (refreshing) return refreshing;

    refreshing = (async () => {
      const refreshToken = await config.getRefreshToken?.();
      if (!refreshToken) return null;
      try {
        const session = await refreshAndPersistDriverSession(config.baseUrl, refreshToken);
        config.onSessionRefreshed?.(session.accessToken, session.refreshToken ?? undefined);
        await emitSecurityEvent("session_refresh");
        return session.accessToken;
      } catch {
        await emitSecurityEvent("session_refresh_failed");
        return null;
      } finally {
        refreshing = null;
      }
    })();

    return refreshing;
  }

  const baseClient = createApiClient(config);

  async function withUnauthorizedRetry<T>(fn: () => Promise<T>): Promise<T> {
    try {
      return await fn();
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;

      const nextToken = await tryRefresh();
      if (!nextToken) {
        config.onUnauthorized?.();
        throw error;
      }

      return fn();
    }
  }

  return {
    get: <T>(path: string, init?: RequestInit) => withUnauthorizedRetry(() => baseClient.get<T>(path, init)),
    post: <T>(path: string, body?: unknown, init?: RequestInit & { skipAuth?: boolean }) =>
      withUnauthorizedRetry(() => baseClient.post<T>(path, body, init)),
    put: <T>(path: string, body?: unknown, init?: RequestInit) =>
      withUnauthorizedRetry(() => baseClient.put<T>(path, body, init)),
    patch: <T>(path: string, body?: unknown, init?: RequestInit) =>
      withUnauthorizedRetry(() => baseClient.patch<T>(path, body, init)),
    delete: <T>(path: string, init?: RequestInit) =>
      withUnauthorizedRetry(() => baseClient.delete<T>(path, init)),
  };
}
