export const API_BASE = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(/\/$/, "");

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

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("driver_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function driverFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...init?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "request_failed");
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const driverApi = {
  login: (email: string) =>
    driverFetch<{ access_token: string; refresh_token: string; driver_id: string }>(
      "/driver-api/v1/auth/login",
      { method: "POST", body: JSON.stringify({ email }) }
    ),
  dashboard: () => driverFetch<DriverDashboard>("/driver-api/v1/dashboard"),
  earnings: () => driverFetch<{ today_cents: number; week_cents: number }>("/driver-api/v1/earnings/today"),
  wallet: () => driverFetch<{ balance_cents: number; transactions: unknown[]; payouts: unknown[] }>("/driver-api/v1/wallet"),
  route: () => driverFetch<{ route_id: string; stops: unknown[]; route_polyline?: string } | null>("/driver-api/v1/routes/assigned"),
  performance: () => driverFetch<Record<string, unknown>>("/driver-api/v1/performance"),
  vehicle: () => driverFetch<{ vehicle: unknown; vehicles: unknown[] }>("/driver-api/v1/vehicle"),
  documents: () => driverFetch<{ documents: unknown[] }>("/driver-api/v1/documents"),
  insurance: () => driverFetch<Record<string, unknown>>("/driver-api/v1/insurance"),
  bonuses: () => driverFetch<{ bonuses: unknown[] }>("/driver-api/v1/bonuses"),
  training: () => driverFetch<{ modules: unknown[] }>("/driver-api/v1/training"),
  support: () => driverFetch<{ tickets: unknown[] }>("/driver-api/v1/support"),
  setOnline: (online: boolean) =>
    driverFetch("/driver-api/v1/availability", { method: "POST", body: JSON.stringify({ online }) }),
  emergency: (location?: { lat: number; lng: number }) =>
    driverFetch("/driver-api/v1/emergency", {
      method: "POST",
      body: JSON.stringify({ location, message: "Emergency from driver portal" }),
    }),
};
