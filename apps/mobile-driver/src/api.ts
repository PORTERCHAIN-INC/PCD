import { apiBaseUrl, fetchTimeoutMs } from "./config";
import { requireBearer } from "./session";
import type {
  AssignedRoute,
  BonusRow,
  DriverDashboard,
  DriverDocument,
  DriverJobs,
  DriverJobDetail,
  DriverJobSummary,
  DriverMe,
  DriverOnboarding,
  DriverPerformance,
  DriverProfile,
  DriverVehicle,
  EarningsSnapshot,
  EmergencyContact,
  InboxSnapshot,
  InsuranceStatus,
  MissingReason,
  NavigationSession,
  NavigationRoute,
  OfflineActionRow,
  OfflineStatus,
  OfflineSyncResult,
  OptimizeResult,
  PickupChecklist,
  PublicHealthStatus,
  RatingsSummary,
  RouteStopRow,
  ScanProgress,
  ShiftSnapshot,
  StatementDetail,
  StatementRow,
  SupportHub,
  TrainingModule,
  WalletSnapshot,
} from "./types";

const DRIVER_API = "/driver-api/v1";

async function fetchWithTimeout(url: string, init: RequestInit = {}): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), fetchTimeoutMs);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
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

async function driverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await requireBearer();
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
    throw new Error(detailFromBody(body, res.status));
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

export function fetchNavigationRoute(routeId?: string | null): Promise<NavigationRoute> {
  const q = routeId ? `?route_id=${encodeURIComponent(routeId)}` : "";
  return driverFetch<NavigationRoute>(`${DRIVER_API}/navigation/route${q}`);
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

/** Is live location sharing on for this driver? (PorterChain admin switch) */
export function fetchGpsStatus(): Promise<{ enabled: boolean; message: string }> {
  return driverFetch(`${DRIVER_API}/gps-status`) as Promise<{ enabled: boolean; message: string }>;
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

export function fetchWallet(): Promise<WalletSnapshot> {
  return driverFetch<WalletSnapshot>(`${DRIVER_API}/wallet`);
}

export function fetchEarnings(): Promise<EarningsSnapshot> {
  return driverFetch<EarningsSnapshot>(`${DRIVER_API}/earnings`);
}

export function fetchStatements(): Promise<{ statements: StatementRow[] }> {
  return driverFetch(`${DRIVER_API}/earnings/statements`);
}

export function fetchDocuments(): Promise<{ documents: DriverDocument[] }> {
  return driverFetch(`${DRIVER_API}/documents`);
}

export function fetchPerformance(): Promise<DriverPerformance> {
  return driverFetch<DriverPerformance>(`${DRIVER_API}/performance`);
}

export function fetchNavigationSession(orderId?: string | null): Promise<NavigationSession> {
  const q = orderId ? `?order_id=${encodeURIComponent(orderId)}` : "";
  return driverFetch<NavigationSession>(`${DRIVER_API}/navigation/session${q}`);
}

export function sendEmergency(message?: string): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/emergency`, {
    method: "POST",
    body: JSON.stringify({ message: message ?? "Driver SOS from mobile app" }),
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

export function podBarcode(routeId: string, stopId: string, barcode: string): Promise<unknown> {
  return driverFetch(
    `${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops/${encodeURIComponent(stopId)}/pod-barcode`,
    { method: "POST", body: JSON.stringify({ barcode }) }
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

export function generateOtp(orderId: string): Promise<{ otp: string }> {
  return driverFetch(`${DRIVER_API}/orders/${encodeURIComponent(orderId)}/otp`, {
    method: "POST",
  });
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

export function shiftBreak(): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/shift/break`, { method: "POST" });
}

export function shiftResume(): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/shift/resume`, { method: "POST" });
}

export function fetchOnboarding(): Promise<DriverOnboarding> {
  return driverFetch<DriverOnboarding>(`${DRIVER_API}/onboarding`);
}

export function uploadDocument(
  docType: string,
  fileUrl: string,
  metadata?: Record<string, string>
): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/documents`, {
    method: "POST",
    body: JSON.stringify({ doc_type: docType, file_url: fileUrl, metadata: metadata ?? null }),
  });
}

export function uploadVehiclePhoto(
  fileUrl: string,
  metadata?: Record<string, string>
): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/profile/vehicle-photos`, {
    method: "POST",
    body: JSON.stringify({
      doc_type: "vehicle_photo",
      file_url: fileUrl,
      metadata: metadata ?? null,
    }),
  });
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

export function fetchPickupChecklist(orderId: string): Promise<PickupChecklist> {
  return driverFetch<PickupChecklist>(
    `${DRIVER_API}/orders/${encodeURIComponent(orderId)}/pickup-checklist`
  );
}

/** Box not at pickup: photo (camera data URL) + reason. Accounts for the box. */
export function reportPackageMissing(
  orderId: string,
  packageId: string,
  body: { photo_url: string; reason: MissingReason; notes?: string }
): Promise<{
  exception_id: string;
  package_id: string;
  status: string;
  checklist: PickupChecklist;
}> {
  return driverFetch(
    `${DRIVER_API}/orders/${encodeURIComponent(orderId)}/packages/${encodeURIComponent(packageId)}/missing`,
    { method: "POST", body: JSON.stringify(body) }
  );
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

export function fetchInbox(): Promise<InboxSnapshot> {
  return driverFetch<InboxSnapshot>(`${DRIVER_API}/communications/notifications`);
}

export function fetchInboxHistory(limit = 100): Promise<InboxSnapshot> {
  return driverFetch<InboxSnapshot>(
    `${DRIVER_API}/communications/notifications/history?limit=${encodeURIComponent(String(limit))}`
  );
}

export function retryOfflineFailed(): Promise<
  { retried?: number; failed?: number } | OfflineSyncResult
> {
  return driverFetch(`${DRIVER_API}/communications/offline/retry`, { method: "POST" });
}

export function markNotificationRead(notificationId: string): Promise<{ ok: boolean }> {
  return driverFetch(
    `${DRIVER_API}/communications/notifications/${encodeURIComponent(notificationId)}/read`,
    {
      method: "POST",
    }
  );
}

export function markNotificationArchived(notificationId: string): Promise<{ ok: boolean }> {
  return driverFetch(
    `${DRIVER_API}/communications/notifications/${encodeURIComponent(notificationId)}/archive`,
    { method: "POST" }
  );
}

export function markAllNotificationsRead(): Promise<{ ok: boolean; marked?: number }> {
  return driverFetch(`${DRIVER_API}/communications/notifications/mark-all-read`, {
    method: "POST",
  });
}

export function fetchSupportHub(): Promise<SupportHub> {
  return driverFetch<SupportHub>(`${DRIVER_API}/support/hub`);
}

export function fetchKnowledgeBase(): Promise<SupportHub["knowledge_base"]> {
  return driverFetch(`${DRIVER_API}/support/knowledge-base`);
}

export function createSupportTicket(body: {
  subject: string;
  description?: string;
  order_id?: string;
  priority?: string;
}): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/support`, {
    method: "POST",
    body: JSON.stringify({ ...body, category: "driver_support" }),
  });
}

export function openClaim(body: {
  order_id: string;
  claim_type: string;
  description?: string;
}): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/support/claims`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateEmergencyContact(body: {
  name: string;
  phone: string;
  relationship?: string;
}): Promise<EmergencyContact> {
  return driverFetch(`${DRIVER_API}/support/emergency-contact`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function fetchShift(): Promise<ShiftSnapshot> {
  return driverFetch<ShiftSnapshot>(`${DRIVER_API}/shift`);
}

export function setAvailability(
  mode: "online" | "offline" | "busy" | "idle"
): Promise<ShiftSnapshot> {
  return driverFetch(`${DRIVER_API}/availability`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

export function reportIncident(body: {
  incident_type: string;
  description: string;
  order_id?: string;
}): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/incidents`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchJobsHistory(): Promise<{ history: DriverJobSummary[] }> {
  return driverFetch(`${DRIVER_API}/jobs/history`);
}

export function optimizeJobs(): Promise<OptimizeResult> {
  return driverFetch(`${DRIVER_API}/jobs/optimize`, { method: "POST" });
}

export function optimizeRunStatus(runId: string): Promise<OptimizeResult> {
  return driverFetch(`${DRIVER_API}/jobs/optimize/runs/${encodeURIComponent(runId)}`);
}

export function optimizeAccept(
  runId: string,
  expectedVersion?: number | null
): Promise<OptimizeResult> {
  const q =
    expectedVersion != null
      ? `?expected_version=${encodeURIComponent(String(expectedVersion))}`
      : "";
  return driverFetch(`${DRIVER_API}/jobs/optimize/runs/${encodeURIComponent(runId)}/accept${q}`, {
    method: "POST",
  });
}

export function optimizeUndo(): Promise<OptimizeResult> {
  return driverFetch(`${DRIVER_API}/jobs/optimize/undo`, { method: "POST" });
}

export function fetchAssignedRoute(): Promise<AssignedRoute | null> {
  return driverFetch(`${DRIVER_API}/routes/assigned`);
}

export function startRoute(routeId: string): Promise<AssignedRoute> {
  return driverFetch(`${DRIVER_API}/routes/${encodeURIComponent(routeId)}/start`, {
    method: "POST",
  });
}

export function fetchRouteStops(routeId: string): Promise<{ stops: RouteStopRow[] }> {
  return driverFetch(`${DRIVER_API}/routes/${encodeURIComponent(routeId)}/stops`);
}

export function fetchRouteEarnings(routeId: string): Promise<{ earnings_cents: number }> {
  return driverFetch(`${DRIVER_API}/routes/${encodeURIComponent(routeId)}/earnings`);
}

export function fetchProfile(): Promise<DriverProfile> {
  return driverFetch(`${DRIVER_API}/profile`);
}

export function fetchEarningsToday(): Promise<{ today_cents?: number; amount_cents?: number }> {
  return driverFetch(`${DRIVER_API}/earnings/today`);
}

export function fetchStatementDetail(statementId: string): Promise<StatementDetail> {
  return driverFetch(`${DRIVER_API}/earnings/statements/${encodeURIComponent(statementId)}`);
}

/** CSV body for Share / save — statement download endpoint. */
export async function downloadStatementCsv(
  statementId: string
): Promise<{ csv: string; filename: string }> {
  const token = await requireBearer();
  const res = await fetchWithTimeout(
    `${apiBaseUrl}${DRIVER_API}/earnings/statements/${encodeURIComponent(statementId)}/download`,
    {
      method: "GET",
      headers: {
        Accept: "text/csv",
        Authorization: `Bearer ${token}`,
      },
    }
  );
  const csv = await res.text();
  if (!res.ok) {
    throw new Error(detailFromBody(csv, res.status));
  }
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  return { csv, filename: match?.[1] || `statement-${statementId}.csv` };
}

export function fetchVehicle(): Promise<{
  vehicle: DriverVehicle | null;
  vehicles: DriverVehicle[];
}> {
  return driverFetch(`${DRIVER_API}/vehicle`);
}

export function fetchInsurance(): Promise<InsuranceStatus> {
  return driverFetch(`${DRIVER_API}/insurance`);
}

export function fetchTraining(): Promise<{ modules: TrainingModule[] }> {
  return driverFetch(`${DRIVER_API}/training`);
}

export function completeTraining(moduleId: string): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/training/${encodeURIComponent(moduleId)}/complete`, {
    method: "POST",
  });
}

export function fetchBonuses(): Promise<{ bonuses: BonusRow[] }> {
  return driverFetch(`${DRIVER_API}/bonuses`);
}

export function claimBonus(bonusId: string): Promise<unknown> {
  return driverFetch(`${DRIVER_API}/bonuses/${encodeURIComponent(bonusId)}/claim`, {
    method: "POST",
  });
}

export function fetchRatings(): Promise<RatingsSummary> {
  return driverFetch(`${DRIVER_API}/ratings`);
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
}): Promise<{ ok: boolean; order_state: string; route: DispatchRoute | null }> {
  return driverFetch(`${DRIVER_API}/dispatch/stops/checkin`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchDispatchChecklist(orderId: string): Promise<StopChecklist> {
  return driverFetch(`${DRIVER_API}/dispatch/orders/${encodeURIComponent(orderId)}/checklist`);
}
