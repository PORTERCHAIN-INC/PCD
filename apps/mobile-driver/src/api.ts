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
      const d = detail as { code?: string; error?: string; message?: string; field?: string };
      // Field validation (422): keep field + code so the form can mark the right input.
      if (d.field && d.code) return JSON.stringify({ field: d.field, code: d.code });
      if (d.code === "sequence_version_conflict") return "sequence_version_conflict";
      if (
        (d.code === "pod_required" ||
          d.code === "driver_off_duty" ||
          d.code === "pickup_document_not_shown") &&
        d.message
      )
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

export type ServerOfflineAction = {
  id: string;
  action_type: string;
  payload: Record<string, unknown> | null;
  status: string;
  error: string | null;
  created_at: string | null;
};

export function retryServerAction(id: string): Promise<ServerOfflineAction> {
  return driverFetch<ServerOfflineAction>(
    `${DRIVER_API}/communications/offline/${encodeURIComponent(id)}/retry`,
    { method: "POST" }
  );
}

export function discardServerAction(id: string): Promise<ServerOfflineAction> {
  return driverFetch<ServerOfflineAction>(
    `${DRIVER_API}/communications/offline/${encodeURIComponent(id)}/discard`,
    { method: "POST" }
  );
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

/** Customer phone for one stop, released per tap and logged on the server (not cached). */
export function fetchStopContact(
  orderId: string,
  kind: "drop" | "pickup"
): Promise<{ phone: string }> {
  return driverFetch(
    `${DRIVER_API}/dispatch/orders/${encodeURIComponent(orderId)}/contact?kind=${kind}`
  );
}

// ---------- Documents, vehicle, settings, privacy ----------
export type DriverDocument = {
  type: string;
  label: string;
  status: string; // missing | pending_review | verified | rejected | expired
  verified: boolean;
  has_file?: boolean;
  url: string | null;
  uploaded_at: string | null;
  expires_at: string | null;
  rejection_reason: string | null;
};

export function fetchDocuments(): Promise<{ documents: DriverDocument[] }> {
  return driverFetch(`${DRIVER_API}/documents?include_files=false`);
}

export function uploadDocument(body: {
  doc_type: string;
  file_url: string;
  metadata?: Record<string, unknown>;
}): Promise<DriverDocument> {
  return driverFetch(`${DRIVER_API}/documents`, { method: "POST", body: JSON.stringify(body) });
}

export type DriverVehicle = {
  id?: string;
  make?: string | null;
  model?: string | null;
  year?: number | null;
  color?: string | null;
  plate?: string | null;
  license_plate?: string | null;
  vehicle_class?: string | null;
  capacity_kg?: number | null;
  capabilities?: string[] | null;
};

export function fetchVehicle(): Promise<{
  vehicle: DriverVehicle | null;
  vehicles: DriverVehicle[];
}> {
  return driverFetch(`${DRIVER_API}/vehicle`);
}

export function fetchAppSettings(): Promise<{ settings: Record<string, unknown> }> {
  return driverFetch(`${DRIVER_API}/settings`);
}

export function saveAppSettings(
  settings: Record<string, unknown>
): Promise<{ settings: Record<string, unknown> }> {
  return driverFetch(`${DRIVER_API}/settings`, {
    method: "PUT",
    body: JSON.stringify({ settings }),
  });
}

export function requestPrivacy(
  kind: "access" | "correction" | "deletion",
  note?: string
): Promise<{
  status: string;
  reference: string | null;
  sla_days: number;
}> {
  return driverFetch(`${DRIVER_API}/privacy/request`, {
    method: "POST",
    body: JSON.stringify({ kind, ...(note ? { note } : {}) }),
  });
}

// ---------- Profile, pay, time, alerts, help ----------
export type Address = {
  line1: string;
  line2?: string | null;
  city: string;
  province: string;
  postal_code: string;
  country?: string;
};
export type EmergencyContact = { name: string; relationship: string; phone: string };
export type MeProfile = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  address: Address | null;
  emergency_contact: EmergencyContact | null;
  photo_url: string | null;
  updated_at: string | null;
};
export type ProfilePatch = Partial<{
  full_name: string;
  address: Address | null;
  emergency_contact: EmergencyContact | null;
  photo: string | null;
}>;

export function fetchMyProfile(): Promise<MeProfile> {
  return driverFetch(`${DRIVER_API}/me/profile`);
}
export function patchMyProfile(
  body: ProfilePatch
): Promise<{ profile: MeProfile; changed: string[] }> {
  return driverFetch(`${DRIVER_API}/me/profile`, { method: "PATCH", body: JSON.stringify(body) });
}
export function syncMyIdentity(): Promise<{ profile: MeProfile; changed: string[] }> {
  return driverFetch(`${DRIVER_API}/me/profile/sync-identity`, { method: "POST" });
}

export type Statement = {
  id: string;
  period_label: string;
  period_start: string;
  period_end: string;
  gross_cents: number;
  deductions_cents: number;
  net_cents: number;
  deliveries: number;
};
export type Payout = {
  id: string;
  amount_cents: number;
  status: string;
  reference: string | null;
  created_at: string | null;
};
export type EarningsFull = {
  today_cents: number;
  week_cents: number;
  month_cents: number;
  completed_deliveries_week?: number;
  wallet_balance_cents?: number;
  payout_history?: Payout[];
  payment_schedule?: {
    frequency: string;
    next_payout_date: string;
    deposit_delay_business_days: number;
  };
  taxes?: { ytd_gross_cents: number };
};
export function fetchEarnings(): Promise<EarningsFull> {
  return driverFetch(`${DRIVER_API}/earnings`);
}
export function fetchStatements(): Promise<{ statements: Statement[] }> {
  return driverFetch(`${DRIVER_API}/earnings/statements`);
}

export type TimesheetShift = {
  id: string;
  date: string;
  started_at: string;
  ended_at: string | null;
  worked_minutes: number;
  break_minutes: number;
  km: number;
  status: string;
};
export type TimesheetWeek = {
  week_start: string;
  worked_minutes: number;
  break_minutes: number;
  km: number;
  shifts: TimesheetShift[];
};
export function fetchTimesheets(
  weeks = 4
): Promise<{ weeks: TimesheetWeek[]; total_worked_minutes: number }> {
  return driverFetch(`${DRIVER_API}/timesheets?weeks=${weeks}`);
}

export type DayKey = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun";
export type Schedule = Record<DayKey, { start: string; end: string }[]>;
export function fetchSchedule(): Promise<{ schedule: Schedule; weekly_hours: number }> {
  return driverFetch(`${DRIVER_API}/availability/schedule`);
}
export function saveSchedule(
  schedule: Schedule
): Promise<{ schedule: Schedule; weekly_hours: number }> {
  return driverFetch(`${DRIVER_API}/availability/schedule`, {
    method: "PUT",
    body: JSON.stringify({ schedule }),
  });
}

export type InboxItem = {
  id: string;
  title: string;
  body: string;
  priority: string;
  category: string;
  is_read: boolean;
  created_at: string | null;
};
export function fetchInbox(): Promise<{ unread_count: number; items: InboxItem[] }> {
  return driverFetch(`${DRIVER_API}/communications/notifications/history?limit=100`);
}
export function markAllRead(): Promise<{ ok: boolean; marked: number }> {
  return driverFetch(`${DRIVER_API}/communications/notifications/mark-all-read`, {
    method: "POST",
  });
}

export type Ticket = {
  id: string;
  ticket_number?: string;
  subject: string;
  status: string;
  priority?: string;
  description?: string | null;
  created_at?: string | null;
};
export function fetchTickets(): Promise<{ tickets: Ticket[] }> {
  return driverFetch(`${DRIVER_API}/support`);
}
export function createTicket(body: {
  subject: string;
  description?: string;
  order_id?: string;
}): Promise<Ticket> {
  return driverFetch(`${DRIVER_API}/support`, {
    method: "POST",
    body: JSON.stringify({ ...body, category: "driver_support" }),
  });
}

// ── Booking documents (pickup authorization etc.) ─────────────────────────
export type StopDocument = {
  id: string;
  stop: "pickup" | "dropoff";
  kind_label: string;
  filename: string;
  content_type: string;
  note: string | null;
  required_at_stop: boolean;
  shown_at: string | null;
};

export function fetchStopDocuments(orderId: string): Promise<{ items: StopDocument[] }> {
  return driverFetch(`/driver-api/v1/orders/${orderId}/attachments`);
}

/** Raw bytes for the on-device copy (works offline once fetched). */
export async function downloadStopDocument(id: string): Promise<ArrayBuffer> {
  const token = await requireBearer(false);
  const res = await fetchWithTimeout(`${apiBaseUrl}/driver-api/v1/attachments/${id}/file`, {
    headers: { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "driver" },
  });
  if (!res.ok) throw new ApiError(`http_${res.status}`, res.status);
  return res.arrayBuffer();
}

/** 5-minute single-use link so the phone's own viewer can show a PDF full-screen. */
export async function stopDocumentLink(id: string): Promise<string> {
  const r = await driverFetch<{ path: string }>(`/driver-api/v1/attachments/${id}/link`, {
    method: "POST",
  });
  return `${apiBaseUrl}${r.path}`;
}

export async function markStopDocumentShown(
  id: string,
  proofUri?: string | null
): Promise<unknown> {
  const token = await requireBearer(false);
  const fd = new FormData();
  if (proofUri)
    fd.append("proof", { uri: proofUri, name: "proof.jpg", type: "image/jpeg" } as unknown as Blob);
  const res = await fetchWithTimeout(`${apiBaseUrl}/driver-api/v1/attachments/${id}/shown`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "driver" },
    body: fd,
  });
  if (!res.ok) throw new ApiError(`http_${res.status}`, res.status);
  return res.json();
}
