import { apiBaseUrl, fetchTimeoutMs } from "./config";
import { ApiError, NetworkError } from "./netErrors";
import { requireBearer } from "./session";
import type {
  DriverDashboard,
  DriverJobs,
  DriverJobDetail,
  DriverMe,
  DriverOnboarding,
  NavigationSession,
  OfflineStatus,
  OfflineSyncResult,
  PublicHealthStatus,
  ScanProgress,
  ShiftSnapshot,
  SupportHub,
} from "./types";

const DRIVER_API = "/driver-api/v1";

async function fetchWithTimeout(url: string, init: RequestInit = {}): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), fetchTimeoutMs);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } catch (err) {
    // fetch only rejects when there is no HTTP response (offline, DNS, abort/timeout).
    throw new NetworkError(
      err instanceof Error && err.name === "AbortError" ? "network_timeout" : "network_unavailable"
    );
  } finally {
    clearTimeout(timer);
  }
}

function detailFromBody(body: unknown, status: number): string {
  if (typeof body === "object" && body && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (typeof detail === "object" && detail) {
      const d = detail as { code?: string; error?: string; message?: string };
      if (d.code === "sequence_version_conflict") return "sequence_version_conflict";
      if ((d.code === "pod_required" || d.code === "driver_off_duty") && d.message)
        return d.message;
      return d.error || d.code || JSON.stringify(detail);
    }
  }
  return `http_${status}`;
}

async function driverFetch<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const token = await requireBearer(retried);
  const res = await fetchWithTimeout(`${apiBaseUrl}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-Porterchain-Portal": "driver",
      ...(init?.headers ?? {}),
    },
  });
  // A cached session JWT can expire between calls (same bug the merchant portal had):
  // get a fresh one and retry exactly once before telling the driver anything.
  if (res.status === 401 && !retried) return driverFetch<T>(path, init, true);
  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    throw new ApiError(detailFromBody(body, res.status), res.status);
  }
  return body as T;
}

export async function probeApi(): Promise<boolean> {
  try {
    const res = await fetchWithTimeout(`${apiBaseUrl}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export function fetchPublicHealth(): Promise<PublicHealthStatus> {
  return fetchWithTimeout(`${apiBaseUrl}/health/status`, { method: "GET" }).then(async (res) => {
    if (!res.ok) throw new Error(`http_${res.status}`);
    return (await res.json()) as PublicHealthStatus;
  });
}

export function fetchMe(): Promise<DriverMe> {
  return driverFetch<DriverMe>(`${DRIVER_API}/me`);
}

export function fetchDashboard(): Promise<DriverDashboard> {
  return driverFetch<DriverDashboard>(`${DRIVER_API}/dashboard`);
}

export function fetchJobs(): Promise<DriverJobs> {
  return driverFetch<DriverJobs>(`${DRIVER_API}/jobs`);
}

export function registerPush(
  deviceToken: string,
  platform: string
): Promise<{ registered: boolean }> {
  return driverFetch(`${DRIVER_API}/push/register`, {
    method: "POST",
    body: JSON.stringify({ device_token: deviceToken, platform }),
  });
}

export function unregisterPush(deviceToken?: string | null): Promise<{ unregistered: boolean }> {
  return driverFetch(`${DRIVER_API}/push/unregister`, {
    method: "POST",
    body: JSON.stringify(deviceToken ? { device_token: deviceToken } : {}),
  });
}

export function startShift(
  routeId?: string | null,
  pretrip?: Record<string, boolean>
): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/shift/start`, {
    method: "POST",
    body: JSON.stringify({ route_id: routeId ?? null, pretrip: pretrip ?? null }),
  });
}

export function endShift(): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/shift/end`, { method: "POST" });
}

export function arriveStop(routeId: string, stopId: string): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/arrive`,
    {
      method: "POST",
    }
  );
}

export function deliverStop(routeId: string, stopId: string): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/deliver`,
    {
      method: "POST",
    }
  );
}

export function acceptOrder(orderId: string): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/orders/${encodeURIComponent(orderId)}/accept`, {
    method: "POST",
  });
}

export function rejectOrder(orderId: string, reason = "unavailable"): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/orders/${encodeURIComponent(orderId)}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function pingLocation(
  lat: number,
  lng: number,
  accuracyM?: number | null,
  extras?: {
    heading?: number | null;
    speed_mps?: number | null;
    recorded_at?: string;
  }
): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/location`, {
    method: "POST",
    body: JSON.stringify({
      lat,
      lng,
      accuracy_m: accuracyM ?? null,
      heading: extras?.heading ?? null,
      speed_mps: extras?.speed_mps ?? null,
      recorded_at: extras?.recorded_at ?? new Date().toISOString(),
    }),
  });
}

export function fetchNavigationSession(orderId?: string | null): Promise<NavigationSession> {
  const q = orderId ? `?order_id=${encodeURIComponent(orderId)}` : "";
  return driverFetch<NavigationSession>(`${DRIVER_API}/navigation/session${q}`);
}

export function sendEmergency(
  message?: string,
  location?: { lat: number; lng: number; accuracy_m?: number | null } | null
): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/emergency`, {
    method: "POST",
    body: JSON.stringify({
      message: message ?? "Driver SOS from mobile app",
      location: location ?? null,
    }),
  });
}

export function podPhoto(routeId: string, stopId: string, fileUrl: string): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-photo`,
    { method: "POST", body: JSON.stringify({ file_url: fileUrl }) }
  );
}

export function podSignature(
  routeId: string,
  stopId: string,
  signatureData: string
): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-signature`,
    { method: "POST", body: JSON.stringify({ signature_data: signatureData }) }
  );
}

export function podIdCheck(
  routeId: string,
  stopId: string,
  body: { id_type: string; name_matches: boolean; age_verified?: boolean | null }
): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-id-check`,
    { method: "POST", body: JSON.stringify(body) }
  );
}

export function podComplete(routeId: string, stopId: string, otp?: string): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-complete`,
    { method: "POST", body: JSON.stringify({ otp: otp ?? null }) }
  );
}

export function queueOffline(
  actionType: string,
  payload: Record<string, unknown>,
  clientId?: string
): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/offline/queue`, {
    method: "POST",
    body: JSON.stringify({
      action_type: actionType,
      payload,
      client_id: clientId ?? null,
    }),
  });
}

export function syncOffline(): Promise<OfflineSyncResult> {
  return driverFetch<OfflineSyncResult>(`${DRIVER_API}/offline/sync`, { method: "POST" });
}

export function fetchOfflineStatus(): Promise<OfflineStatus> {
  return driverFetch<OfflineStatus>(`${DRIVER_API}/communications/offline`);
}

export function reportException(
  routeId: string,
  stopId: string,
  exceptionType: string,
  notes?: string,
  photoUrl?: string
): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/exception`,
    {
      method: "POST",
      body: JSON.stringify({
        exception_type: exceptionType,
        notes: notes ?? null,
        photo_url: photoUrl ?? null,
      }),
    }
  );
}

export function fetchOnboarding(): Promise<DriverOnboarding> {
  return driverFetch<DriverOnboarding>(`${DRIVER_API}/onboarding`);
}

export function fetchJob(orderId: string): Promise<DriverJobDetail> {
  return driverFetch<DriverJobDetail>(`${DRIVER_API}/jobs/${encodeURIComponent(orderId)}`);
}

export function scanPackage(
  orderId: string,
  qrPayload: string,
  phase: "pickup" | "delivery"
): Promise<ScanProgress & { package_id?: string; tracking_suffix?: string; status?: string }> {
  return driverFetch(`${DRIVER_API}/orders/${encodeURIComponent(orderId)}/packages/scan`, {
    method: "POST",
    body: JSON.stringify({ qr_payload: qrPayload, phase }),
  });
}

export function codCheckout(orderId: string): Promise<{
  checkout_url: string;
  session_id: string;
  amount_cents: number;
  mock?: boolean;
}> {
  return driverFetch(`${DRIVER_API}/orders/${encodeURIComponent(orderId)}/cod-checkout`, {
    method: "POST",
  });
}

export function fetchSupportHub(): Promise<SupportHub> {
  return driverFetch<SupportHub>(`${DRIVER_API}/support/hub`);
}

export function setAvailability(
  mode: "online" | "offline" | "busy" | "idle"
): Promise<ShiftSnapshot> {
  return driverFetch(`${DRIVER_API}/availability`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

// ---------- GPS policy + Ontario electronic monitoring policy ----------
export type GpsStatus = {
  enabled: boolean;
  message: string;
  consent_required?: boolean;
  consent_text?: string;
};

/** Is live location sharing on for this driver? (PorterChain admin switch) */
export function fetchGpsStatus(): Promise<GpsStatus> {
  return driverFetch(`${DRIVER_API}/gps-status`) as Promise<GpsStatus>;
}

export function sendGpsConsent(accepted: boolean): Promise<GpsStatus> {
  return driverFetch(`${DRIVER_API}/gps-consent`, {
    method: "POST",
    body: JSON.stringify({ accepted, source: "app" }),
  }) as Promise<GpsStatus>;
}

export type MonitoringPolicy = {
  title: string;
  version: string;
  date: string;
  sections: Array<{ heading: string; body?: string; items?: string[] }>;
  acknowledged: boolean;
};

/** Ontario ESA electronic monitoring policy (view anytime; acknowledge per version). */
export function fetchMonitoringPolicy(): Promise<MonitoringPolicy> {
  return driverFetch(`${DRIVER_API}/monitoring-policy`) as Promise<MonitoringPolicy>;
}

export function ackMonitoringPolicy(): Promise<MonitoringPolicy> {
  return driverFetch(`${DRIVER_API}/monitoring-policy/ack`, {
    method: "POST",
    body: JSON.stringify({ source: "app" }),
  }) as Promise<MonitoringPolicy>;
}

// ---------- Dispatch route (committed plan) + stop check-ins ----------
import type { CheckinEvent, DispatchRoute, StopChecklist } from "./dispatchRoute";

export function fetchDispatchRoute(): Promise<{ route: DispatchRoute | null }> {
  return driverFetch(`${DRIVER_API}/dispatch/route`);
}

export function dispatchCheckin(body: {
  keys: string[];
  event: CheckinEvent;
  lat?: number;
  lng?: number;
  accuracy_m?: number;
  note?: string;
  pod_photo?: string;
  short_reason?: string;
  /** Same id online and in the offline queue: a replay is a no-op on the server. */
  client_id?: string;
}): Promise<{ ok: boolean; order_state: string; route: DispatchRoute | null }> {
  return driverFetch(`${DRIVER_API}/dispatch/stops/checkin`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchDispatchChecklist(orderId: string): Promise<StopChecklist> {
  return driverFetch(`${DRIVER_API}/dispatch/orders/${encodeURIComponent(orderId)}/checklist`);
}

export type EarningsToday = { today_cents?: number; week_cents?: number; month_cents?: number };

export function fetchEarningsToday(): Promise<EarningsToday> {
  return driverFetch(`${DRIVER_API}/earnings/today`);
}
