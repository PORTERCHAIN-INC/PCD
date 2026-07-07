import type { ApiClient } from "./client";
import { createNotificationApi } from "./notifications";
import type { NotificationInboxResponse } from "./notifications";
import type {
  DriverCommunicationsSnapshot,
  DriverDashboard,
  DriverEarningsSnapshot,
  DriverEarningsStatement,
  DriverJobDetail,
  DriverJobsList,
  DriverNavigationSession,
  DriverProfile,
  DriverRoute,
  DriverShiftSnapshot,
  DriverTokenResponse,
} from "./driver-types";

/** Driver API — Porterchain only (`/driver-api/v1/*`). Fleetbase via server adapter. */
export function createDriverApi(client: ApiClient) {
  const base = "/driver-api/v1";

  return {
    login: (email: string, clerkToken = "dev") =>
      client.post<DriverTokenResponse>(
        `${base}/auth/login`,
        { email },
        { skipAuth: true, headers: { Authorization: `Bearer ${clerkToken}` } }
      ),

    refreshSession: (refreshToken: string) =>
      client.post<DriverTokenResponse>(
        `${base}/auth/refresh`,
        { refresh_token: refreshToken },
        { skipAuth: true }
      ),

    me: () => client.get<DriverProfile>(`${base}/me`),
    dashboard: () => client.get<DriverDashboard>(`${base}/dashboard`),

    jobs: () => client.get<DriverJobsList>(`${base}/jobs`),
    job: (orderId: string) =>
      client.get<DriverJobDetail>(`${base}/jobs/${encodeURIComponent(orderId)}`),
    jobsHistory: () => client.get<{ history: DriverJobsList["jobs"] }>(`${base}/jobs/history`),

    acceptOrder: (orderId: string) =>
      client.post<Record<string, unknown>>(`${base}/orders/${encodeURIComponent(orderId)}/accept`),
    rejectOrder: (orderId: string, reason?: string) =>
      client.post<Record<string, unknown>>(`${base}/orders/${encodeURIComponent(orderId)}/reject`, {
        reason: reason ?? "",
      }),

    route: () => client.get<DriverRoute | null>(`${base}/routes/assigned`),
    startRoute: (routeId: string) =>
      client.post<DriverRoute>(`${base}/routes/${encodeURIComponent(routeId)}/start`),
    arriveStop: (routeId: string, stopId: string) =>
      client.post(
        `${base}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/arrive`
      ),
    deliverStop: (routeId: string, stopId: string) =>
      client.post(
        `${base}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/deliver`
      ),
    stopException: (
      routeId: string,
      stopId: string,
      body: { exception_type: string; notes?: string }
    ) =>
      client.post(
        `${base}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/exception`,
        body
      ),

    navigationSession: (orderId?: string) =>
      client.get<DriverNavigationSession>(
        orderId
          ? `${base}/navigation/session?order_id=${encodeURIComponent(orderId)}`
          : `${base}/navigation/session`
      ),

    postLocation: (body: {
      lat: number;
      lng: number;
      accuracy_m?: number;
      heading?: number;
      speed_mps?: number;
    }) => client.post(`${base}/location`, body),

    podPhoto: (routeId: string, stopId: string, fileUrl: string) =>
      client.post(
        `${base}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-photo`,
        {
          file_url: fileUrl,
        }
      ),
    podSignature: (routeId: string, stopId: string, signatureData: string) =>
      client.post(
        `${base}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-signature`,
        { signature_data: signatureData }
      ),
    podComplete: (routeId: string, stopId: string, otp?: string) =>
      client.post(
        `${base}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-complete`,
        {
          otp: otp ?? "",
        }
      ),
    generateOtp: (orderId: string) =>
      client.post<{ otp: string }>(`${base}/orders/${encodeURIComponent(orderId)}/otp`),

    earningsSnapshot: () => client.get<DriverEarningsSnapshot>(`${base}/earnings`),
    earningsStatements: () =>
      client.get<{ statements: DriverEarningsStatement[] }>(`${base}/earnings/statements`),
    earningsToday: () =>
      client.get<{ today_cents: number; week_cents: number; month_cents: number }>(
        `${base}/earnings/today`
      ),
    wallet: () =>
      client.get<{ balance_cents: number; transactions: unknown[]; payouts: unknown[] }>(
        `${base}/wallet`
      ),

    shift: () => client.get<DriverShiftSnapshot>(`${base}/shift`),
    shiftStart: (routeId?: string) =>
      client.post<DriverShiftSnapshot>(`${base}/shift/start`, { route_id: routeId ?? null }),
    shiftEnd: () => client.post<DriverShiftSnapshot>(`${base}/shift/end`),
    shiftBreak: () => client.post<DriverShiftSnapshot>(`${base}/shift/break`),
    shiftResume: () => client.post<DriverShiftSnapshot>(`${base}/shift/resume`),
    setAvailability: (mode: "online" | "offline" | "busy" | "idle") =>
      client.post<DriverShiftSnapshot>(`${base}/availability`, { mode }),

    incidents: () =>
      client.get<{
        incidents: Array<{
          id: string;
          status: string;
          incident_type: string;
          description: string;
        }>;
      }>(`${base}/incidents`),
    reportIncident: (body: {
      incident_type: string;
      description: string;
      order_id?: string;
      location?: { lat: number; lng: number };
    }) => client.post(`${base}/incidents`, body),
    emergency: (body?: { message?: string; location?: { lat: number; lng: number } }) =>
      client.post(`${base}/emergency`, body ?? { message: "SOS from driver mobile" }),

    communicationsHub: () => client.get<DriverCommunicationsSnapshot>(`${base}/communications`),
    driverNotificationInbox: () =>
      client.get<NotificationInboxResponse>(`${base}/communications/notifications`),
    driverNotificationHistory: () =>
      client.get<NotificationInboxResponse>(`${base}/communications/notifications/history`),
    markNotificationRead: (id: string) =>
      client.post(`${base}/communications/notifications/${encodeURIComponent(id)}/read`),
    markNotificationArchive: (id: string) =>
      client.post(`${base}/communications/notifications/${encodeURIComponent(id)}/archive`),
    markAllNotificationsRead: () =>
      client.post<{ ok: boolean; marked: number }>(
        `${base}/communications/notifications/mark-all-read`
      ),

    notificationPreferences: () => createNotificationApi(client, "/v1").getPreferences(),
    updateNotificationPreference: (body: {
      category: string;
      email_enabled?: boolean;
      push_enabled?: boolean;
      sms_enabled?: boolean;
      in_app_enabled?: boolean;
    }) => createNotificationApi(client, "/v1").updatePreference(body),

    supportHub: () => client.get<Record<string, unknown>>(`${base}/support/hub`),
    createSupport: (body: { subject: string; description?: string; order_id?: string }) =>
      client.post(`${base}/support`, { ...body, category: "driver_support" }),

    registerPush: (deviceToken: string, platform: string) =>
      client.post(`${base}/push/register`, { device_token: deviceToken, platform }),

    queueOffline: (actionType: string, payload: Record<string, unknown>, clientId?: string) =>
      client.post<{ action_id: string; status: string; deduplicated?: boolean }>(
        `${base}/offline/queue`,
        {
          action_type: actionType,
          payload,
          client_id: clientId,
        }
      ),
    offlinePending: () =>
      client.get<{ actions: import("./offline").OfflineActionRow[] }>(`${base}/offline/pending`),
    offlineStatus: () =>
      client.get<import("./offline").OfflineStatus>(`${base}/communications/offline`),
    syncOffline: () =>
      client.post<{
        synced: number;
        failed: number;
        conflicts_resolved?: number;
        synced_at?: string;
      }>(`${base}/offline/sync`),
    retryOffline: () =>
      client.post<{ synced: number; failed: number; retried: number; conflicts_resolved?: number }>(
        `${base}/communications/offline/retry`
      ),
  };
}

export type DriverApi = ReturnType<typeof createDriverApi>;
