import type { DriverRoute, DriverStop } from "./workspace";
import type { DriverJobDetail, DriverJobsList, DriverJobSummary } from "./jobs";
import type { DriverNavigationSession } from "./navigation";
import type { DriverShiftSnapshot } from "./shift";
import type { DriverEarningsSnapshot, StatementRow } from "./earnings";
import type { DriverProfileSnapshot } from "./profile";
import type { DriverSupportSnapshot } from "./support";
import type { DriverCommunicationsSnapshot } from "./communications";

export const API_BASE = "/api/driver";

export interface DriverDashboard {
  todays_earnings_cents: number;
  todays_stops_total: number;
  todays_stops_completed: number;
  wallet_balance_cents: number;
  is_online: boolean;
  availability: string;
  rating: number | null;
  active_route_id: string | null;
  bonuses_available: number;
  performance_score: number;
  pending_documents: number;
}

export interface DriverProfile {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  status: string;
  rating: number | null;
  is_online: boolean;
  availability: string;
}

export interface DriverPerformance {
  score: number;
  on_time_percent: number;
  completion_percent: number;
  deliveries_total: number;
  deliveries_today: number;
  acceptance_rate: number;
  rating: number | null;
}

export interface DriverRatings {
  rating: number;
  total_reviews: number;
  five_star_percent: number;
}

export interface DriverVehicle {
  id: string;
  vehicle_class: string;
  plate_number: string;
  make_model: string;
  capacity_kg: number | null;
  is_active: boolean;
}

export interface SupportTicket {
  id: string;
  status: string;
  priority: string;
  subject: string;
}

export interface DriverIncident {
  id: string;
  status: string;
  incident_type: string;
  description: string;
}

export type { DriverRoute, DriverStop };

async function driverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detailRaw = err.detail;
    let detail: string;
    if (typeof detailRaw === "string") {
      detail = detailRaw;
    } else if (detailRaw && typeof detailRaw === "object") {
      const d = detailRaw as { code?: string; error?: string; message?: string };
      if (d.code === "sequence_version_conflict") {
        detail = "sequence_version_conflict";
      } else if ((d.code === "pod_required" || d.code === "driver_off_duty") && d.message) {
        detail = d.message;
      } else {
        detail = d.error || d.code || "request_failed";
      }
    } else {
      detail = "request_failed";
    }
    if (res.status === 401 && typeof window !== "undefined") {
      const onLogin = window.location.pathname.startsWith("/login");
      if (!onLogin && (detail === "unauthorized" || detail === "invalid_driver_token")) {
        window.location.href = "/login?session=expired";
      }
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function hasDriverSession(): Promise<boolean> {
  const res = await fetch("/api/auth/driver-session", { credentials: "include" });
  if (!res.ok) return false;
  const data = (await res.json()) as { authenticated?: boolean };
  return Boolean(data.authenticated);
}

export async function driverLogout(): Promise<void> {
  // Clerk sign-out is handled by UI; cookie JWT minting is retired.
}

export const driverApi = {
  dispatchRoute: () =>
    driverFetch<{ route: import("@/lib/dispatch-route").DriverDispatchRoute | null }>(
      "/v1/dispatch/route"
    ),
  dispatchCheckin: (body: {
    keys: string[];
    event: import("@/lib/dispatch-route").CheckinEvent;
    lat?: number;
    lng?: number;
    accuracy_m?: number;
    note?: string;
    pod_photo?: string;
    client_id?: string;
    short_reason?: string;
  }) =>
    driverFetch<{
      ok: boolean;
      order_state: string;
      route: import("@/lib/dispatch-route").DriverDispatchRoute | null;
    }>("/v1/dispatch/stops/checkin", { method: "POST", body: JSON.stringify(body) }),
  dispatchChecklist: (orderId: string) =>
    driverFetch<import("@/lib/dispatch-route").StopChecklist>(
      `/v1/dispatch/orders/${orderId}/checklist`
    ),
  onboarding: () =>
    driverFetch<import("@/lib/onboarding").DriverOnboardingStatus>("/v1/onboarding"),
  dashboard: () => driverFetch<DriverDashboard>("/v1/dashboard"),
  earnings: () =>
    driverFetch<{ today_cents: number; week_cents: number; month_cents?: number }>(
      "/v1/earnings/today"
    ),
  earningsSnapshot: () => driverFetch<DriverEarningsSnapshot>("/v1/earnings"),
  earningsStatements: () => driverFetch<{ statements: StatementRow[] }>("/v1/earnings/statements"),
  wallet: () =>
    driverFetch<{ balance_cents: number; transactions: unknown[]; payouts: unknown[] }>(
      "/v1/wallet"
    ),
  me: () => driverFetch<DriverProfile>("/v1/me"),
  profile: () => driverFetch<DriverProfileSnapshot>("/v1/profile"),
  identityVerificationStatus: () =>
    driverFetch<{
      enabled: boolean;
      mock_allowed: boolean;
      license_verified: boolean;
      provider?: string | null;
      verification_source?: string | null;
      session_id?: string | null;
      status: string;
      failure_reason?: string | null;
    }>("/v1/verification/identity"),
  startIdentityVerification: () =>
    driverFetch<{
      session_id: string;
      url: string | null;
      client_secret: string | null;
      status: string;
      mock: boolean;
      enabled: boolean;
    }>("/v1/verification/identity/session", { method: "POST" }),
  mockCompleteIdentityVerification: (body?: { session_id?: string; verified?: boolean }) =>
    driverFetch<{
      session_id: string;
      verified: boolean;
      license_verified: boolean;
      mock: boolean;
    }>("/v1/verification/identity/mock-complete", {
      method: "POST",
      body: JSON.stringify(body ?? { verified: true }),
    }),
  backgroundCheckStatus: () =>
    driverFetch<{
      enabled: boolean;
      mock_allowed: boolean;
      background_check_status: string;
      passed: boolean;
      invitation_url?: string | null;
      license_verified: boolean;
    }>("/v1/verification/background"),
  startBackgroundCheck: () =>
    driverFetch<{
      invitation_id?: string;
      candidate_id?: string;
      invitation_url: string | null;
      status: string;
      mock: boolean;
      already_cleared?: boolean;
    }>("/v1/verification/background/start", { method: "POST" }),
  mockCompleteBackgroundCheck: (body?: { invitation_id?: string; result?: string }) =>
    driverFetch<{
      invitation_id: string;
      status: string;
      passed: boolean;
      mock: boolean;
    }>("/v1/verification/background/mock-complete", {
      method: "POST",
      body: JSON.stringify(body ?? { result: "cleared" }),
    }),
  abstractStatus: () =>
    driverFetch<{
      enabled: boolean;
      verified: boolean;
      status: string;
      failure_reasons?: string[];
      max_demerits: number;
      allowed_classes: string[];
    }>("/v1/verification/abstract"),
  submitAbstract: (body: {
    file_url: string;
    license_class: string;
    demerit_points: number;
    has_active_suspension: boolean;
    expires_at?: string;
    issued_at?: string;
    reference_number?: string;
  }) =>
    driverFetch<{
      enabled: boolean;
      verified: boolean;
      status: string;
      failure_reasons?: string[];
    }>("/v1/verification/abstract/submit", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  uploadDocument: (
    docType: string,
    fileUrl: string,
    metadata?: Record<string, string | undefined>
  ) =>
    driverFetch("/v1/documents", {
      method: "POST",
      body: JSON.stringify({ doc_type: docType, file_url: fileUrl, metadata }),
    }),
  uploadVehiclePhoto: (fileUrl: string, metadata?: Record<string, string | undefined>) =>
    driverFetch("/v1/profile/vehicle-photos", {
      method: "POST",
      body: JSON.stringify({ doc_type: "vehicle_photo", file_url: fileUrl, metadata }),
    }),
  route: () => driverFetch<DriverRoute | null>("/v1/routes/assigned"),
  jobs: () => driverFetch<import("@/lib/jobs").DriverJobsList>("/v1/jobs"),
  optimizeJobs: () =>
    driverFetch<import("@/lib/jobs").DriverJobsOptimizeResult>("/v1/jobs/optimize", {
      method: "POST",
    }),
  optimizeRunStatus: (runId: string) =>
    driverFetch<import("@/lib/jobs").DriverJobsOptimizeResult>(
      `/v1/jobs/optimize/runs/${encodeURIComponent(runId)}`
    ),
  optimizeAccept: (runId: string, expectedVersion?: number | null) => {
    const q =
      expectedVersion != null
        ? `?expected_version=${encodeURIComponent(String(expectedVersion))}`
        : "";
    return driverFetch<import("@/lib/jobs").DriverJobsOptimizeResult>(
      `/v1/jobs/optimize/runs/${encodeURIComponent(runId)}/accept${q}`,
      { method: "POST" }
    );
  },
  optimizeUndo: () =>
    driverFetch<import("@/lib/jobs").DriverJobsOptimizeResult>("/v1/jobs/optimize/undo", {
      method: "POST",
    }),
  job: (orderId: string) => driverFetch<DriverJobDetail>(`/v1/jobs/${orderId}`),
  scanPackage: (orderId: string, body: { qr_payload: string; phase: "pickup" | "delivery" }) =>
    driverFetch<{
      package_id: string;
      tracking_suffix: string;
      status: string;
      scanned: number;
      required: number;
      complete: boolean;
      missing_suffixes: string[];
    }>(`/v1/orders/${orderId}/packages/scan`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  reportPackageMissing: (
    orderId: string,
    packageId: string,
    body: { photo_url: string; reason: string; notes?: string }
  ) =>
    driverFetch<{ exception_id: string; package_id: string; status: string }>(
      `/v1/orders/${orderId}/packages/${packageId}/missing`,
      { method: "POST", body: JSON.stringify(body) }
    ),
  codCheckout: (orderId: string) =>
    driverFetch<{ checkout_url: string; session_id: string; amount_cents: number; mock?: boolean }>(
      `/v1/orders/${orderId}/cod-checkout`,
      { method: "POST" }
    ),
  jobsHistory: () => driverFetch<{ history: DriverJobSummary[] }>("/v1/jobs/history"),
  navigationSession: (orderId?: string) =>
    driverFetch<DriverNavigationSession>(
      orderId
        ? `/v1/navigation/session?order_id=${encodeURIComponent(orderId)}`
        : "/v1/navigation/session"
    ),
  navigationRoute: (routeId?: string) =>
    driverFetch<Record<string, unknown>>(
      routeId
        ? `/v1/navigation/route?route_id=${encodeURIComponent(routeId)}`
        : "/v1/navigation/route"
    ),
  gpsStatus: () => driverFetch<{ enabled: boolean; message: string }>("/v1/gps-status"),
  postLocation: (body: {
    lat: number;
    lng: number;
    accuracy_m?: number;
    heading?: number;
    speed_mps?: number;
    recorded_at?: string;
  }) =>
    driverFetch("/v1/location", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  jobNavigation: (orderId: string) =>
    driverFetch<Record<string, unknown>>(`/v1/orders/${orderId}/navigation`),
  arriveStop: (routeId: string, stopId: string) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/arrive`, { method: "POST" }),
  deliverStop: (routeId: string, stopId: string) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/deliver`, { method: "POST" }),
  reportException: (
    routeId: string,
    stopId: string,
    body: { exception_type: string; notes?: string; photo_url?: string }
  ) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/exception`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  podPhoto: (routeId: string, stopId: string, fileUrl: string) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/pod-photo`, {
      method: "POST",
      body: JSON.stringify({ file_url: fileUrl }),
    }),
  podSignature: (routeId: string, stopId: string, signatureData: string) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/pod-signature`, {
      method: "POST",
      body: JSON.stringify({ signature_data: signatureData }),
    }),
  podIdCheck: (
    routeId: string,
    stopId: string,
    body: { id_type: string; name_matches: boolean; age_verified?: boolean | null }
  ) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/pod-id-check`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  podComplete: (routeId: string, stopId: string, otp?: string) =>
    driverFetch(`/v1/routes/${routeId}/stops/${stopId}/pod-complete`, {
      method: "POST",
      body: JSON.stringify({ otp: otp ?? "" }),
    }),
  generateOtp: (orderId: string) =>
    driverFetch<{ otp: string }>(`/v1/orders/${orderId}/otp`, { method: "POST" }),
  reportIncident: (body: {
    incident_type: string;
    description: string;
    order_id?: string;
    location?: { lat: number; lng: number };
  }) =>
    driverFetch("/v1/incidents", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  startRoute: (routeId: string) =>
    driverFetch<DriverRoute>(`/v1/routes/${routeId}/start`, { method: "POST" }),
  performance: () => driverFetch<DriverPerformance>("/v1/performance"),
  ratings: () => driverFetch<DriverRatings>("/v1/ratings"),
  vehicle: () =>
    driverFetch<{ vehicle: DriverVehicle | null; vehicles: DriverVehicle[] }>("/v1/vehicle"),
  incidents: () => driverFetch<{ incidents: DriverIncident[] }>("/v1/incidents"),
  documents: () => driverFetch<{ documents: unknown[] }>("/v1/documents"),
  insurance: () => driverFetch<Record<string, unknown>>("/v1/insurance"),
  bonuses: () => driverFetch<{ bonuses: unknown[] }>("/v1/bonuses"),
  training: () => driverFetch<{ modules: unknown[] }>("/v1/training"),
  support: () => driverFetch<{ tickets: unknown[] }>("/v1/support"),
  supportHub: () => driverFetch<DriverSupportSnapshot>("/v1/support/hub"),
  createSupportTicket: (body: {
    subject: string;
    description?: string;
    order_id?: string;
    priority?: string;
  }) =>
    driverFetch("/v1/support", {
      method: "POST",
      body: JSON.stringify({ ...body, category: "driver_support" }),
    }),
  openClaim: (body: { order_id: string; claim_type: string; description?: string }) =>
    driverFetch("/v1/support/claims", { method: "POST", body: JSON.stringify(body) }),
  acceptOrder: (orderId: string) => driverFetch(`/v1/orders/${orderId}/accept`, { method: "POST" }),
  rejectOrder: (orderId: string, reason?: string) =>
    driverFetch(`/v1/orders/${orderId}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? "" }),
    }),
  updateEmergencyContact: (body: { name: string; phone: string; relationship?: string }) =>
    driverFetch("/v1/support/emergency-contact", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  setOnline: (online: boolean) =>
    driverFetch("/v1/availability", {
      method: "POST",
      body: JSON.stringify({ online }),
    }),
  setAvailabilityMode: (mode: "online" | "offline" | "busy" | "idle") =>
    driverFetch<DriverShiftSnapshot>("/v1/availability", {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  shift: () => driverFetch<DriverShiftSnapshot>("/v1/shift"),
  shiftStart: (routeId?: string, pretrip?: Record<string, boolean>) =>
    driverFetch<DriverShiftSnapshot>("/v1/shift/start", {
      method: "POST",
      body: JSON.stringify({ route_id: routeId ?? null, pretrip: pretrip ?? null }),
    }),
  shiftEnd: () => driverFetch<DriverShiftSnapshot>("/v1/shift/end", { method: "POST" }),
  shiftBreak: () => driverFetch<DriverShiftSnapshot>("/v1/shift/break", { method: "POST" }),
  shiftResume: () => driverFetch<DriverShiftSnapshot>("/v1/shift/resume", { method: "POST" }),
  emergency: (location?: { lat: number; lng: number }) =>
    driverFetch("/v1/emergency", {
      method: "POST",
      body: JSON.stringify({ location, message: "Emergency from driver portal" }),
    }),
  registerPush: (deviceToken: string, platform = "web") =>
    driverFetch("/v1/push/register", {
      method: "POST",
      body: JSON.stringify({ device_token: deviceToken, platform }),
    }),
  communicationsHub: () => driverFetch<DriverCommunicationsSnapshot>("/v1/communications"),
  markNotificationRead: (notificationId: string) =>
    driverFetch(`/v1/communications/notifications/${notificationId}/read`, { method: "POST" }),
  markAllNotificationsRead: () =>
    driverFetch<{ ok: boolean; marked: number }>("/v1/communications/notifications/mark-all-read", {
      method: "POST",
    }),
  queueOffline: (actionType: string, payload: Record<string, unknown>) =>
    driverFetch("/v1/offline/queue", {
      method: "POST",
      body: JSON.stringify({ action_type: actionType, payload }),
    }),
  syncOffline: () =>
    driverFetch<{ synced: number; failed: number }>("/v1/offline/sync", { method: "POST" }),
  retryOffline: () =>
    driverFetch<{ synced: number; failed: number; retried: number }>(
      "/v1/communications/offline/retry",
      { method: "POST" }
    ),
  logout: () => driverLogout(),
};
