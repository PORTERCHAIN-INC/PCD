export type JobBucket = "current" | "upcoming" | "completed";

export type DriverJobSummary = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  status: string;
  bucket: JobBucket;
  pickup_address: string;
  delivery_address: string;
  pickup_stop_id: string;
  delivery_stop_id: string;
  scheduled_at: string | null;
  special_instructions?: string | null;
};

export type DriverJobsList = {
  route_id: string | null;
  route_status: string | null;
  current: DriverJobSummary | null;
  upcoming: DriverJobSummary[];
  completed: DriverJobSummary[];
  jobs: DriverJobSummary[];
};

export type DriverJobDetail = DriverJobSummary & {
  pickup_detail: Record<string, unknown>;
  delivery_detail: Record<string, unknown>;
  pickup_stop: Record<string, unknown>;
  delivery_stop: Record<string, unknown>;
  merchant: { id: string; company_name: string; email: string; phone: string | null } | null;
  customer: { id: string | null; email: string | null; phone: string | null; name: string | null };
  packages: Array<Record<string, unknown>>;
  timeline: Array<{
    event_type: string;
    label: string;
    from_state: string | null;
    to_state: string | null;
    occurred_at: string | null;
    actor_type: string | null;
  }>;
  photos: Array<Record<string, unknown>>;
  signatures: Array<Record<string, unknown>>;
  documents: Array<Record<string, unknown>>;
  proof_of_delivery: {
    completed: boolean;
    proofs: Array<Record<string, unknown>>;
    otp_verified: boolean;
  };
  otp_required: boolean;
  incidents: Array<{
    id: string;
    incident_type: string;
    description: string;
    status: string;
    created_at: string;
  }>;
  amount_cents: number;
  currency: string;
  updated_at: string | null;
  route_id: string | null;
};

export type DriverDashboard = {
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
};

export type DriverProfile = {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  status: string;
  rating: number | null;
  is_online: boolean;
  availability: string;
  wallet_balance_cents?: number;
};

export type DriverTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  driver_id: string;
};

export type RouteLeg = {
  source: string;
  label?: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string;
  arrives_at?: string;
  eta_label?: string;
};

export type DriverNavigationSession = {
  idle?: boolean;
  message?: string;
  order_id: string | null;
  tracking_number: string | null;
  order_number: string | null;
  state: string;
  pickup?: Record<string, unknown>;
  dropoff?: Record<string, unknown>;
  pickup_route?: RouteLeg | null;
  delivery_route?: RouteLeg | null;
  optimized_route?: RouteLeg | null;
  eta?: RouteLeg | null;
  route_polyline?: string | null;
  navigation_url?: string | null;
  current_location?: { lat: number; lng: number } | null;
  driver_location?: { lat: number; lng: number } | null;
  gps_source?: string | null;
  replay?: Array<{ lat: number; lng: number; at?: string; source?: string }>;
  geofences?: Array<Record<string, unknown>>;
  traffic?: { layer_available: boolean; source: string };
  routing_engines?: Record<string, string>;
  last_updated?: string;
};

export type DriverShiftSnapshot = {
  shift_active: boolean;
  shift: {
    id: string;
    status: string;
    started_at: string | null;
    ended_at: string | null;
    break_minutes: number;
    mileage_km: number;
    route_id: string | null;
  } | null;
  availability: string;
  is_online: boolean;
  working_minutes: number;
  working_hours_label: string;
  mileage_km: number;
  current_route: {
    route_id: string;
    status: string;
    stops_count: number;
    earnings_cents: number;
  } | null;
  last_updated: string;
};

export type DriverEarningsLineItem = {
  id: string;
  type: string;
  amount_cents: number;
  description: string;
  reference_id: string | null;
  created_at: string | null;
};

export type DriverEarningsStatement = {
  id: string;
  period_label: string;
  period_start: string;
  period_end: string;
  gross_cents: number;
  deductions_cents: number;
  net_cents: number;
  deliveries: number;
};

export type DriverEarningsSnapshot = {
  today_cents: number;
  week_cents: number;
  month_cents: number;
  wallet_balance_cents: number;
  completed_deliveries_today: number;
  completed_deliveries_week: number;
  completed_deliveries_month: number;
  bonuses: Array<{ id: string; title: string; amount_cents: number; status: string }>;
  adjustments: DriverEarningsLineItem[];
  incentives: DriverEarningsLineItem[];
  deductions: DriverEarningsLineItem[];
  payout_history: Array<{
    id: string;
    amount_cents: number;
    status: string;
    created_at: string | null;
    reference?: string | null;
    currency?: string;
  }>;
  taxes: {
    ytd_gross_cents: number;
    month_gross_cents: number;
    withheld_cents: number;
    estimated_tax_cents: number;
    tax_rate_percent: number;
    note: string;
  };
  payment_schedule: {
    frequency: string;
    day_of_week: string;
    cutoff_description: string;
    deposit_delay_business_days: number;
    currency: string;
    next_payout_date?: string;
  };
  last_updated: string;
};

export type DriverRoute = {
  route_id: string;
  driver_id: string;
  status: string;
  stops: Array<{
    stop_id: string;
    order_id: string;
    sequence: number;
    stop_type: string;
    status: string;
    address: Record<string, unknown>;
    tracking_number?: string;
    otp_required?: boolean;
    pod_required?: boolean;
  }>;
  route_polyline?: string | null;
  earnings_cents: number;
  started_at: string | null;
};

export type NotificationItem = {
  id: string;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string | null;
  priority?: string;
  category?: string;
  deep_link?: string | null;
  group?: string;
  order_id?: string;
  ticket_id?: string;
  claim_id?: string;
};

export type DriverCommunicationsSnapshot = {
  notifications: {
    unread_count: number;
    items: NotificationItem[];
    by_group?: Record<string, NotificationItem[]>;
  };
  offline: import("./offline").OfflineStatus;
  push: { registered_devices: number };
};

export type DriverIncident = {
  id: string;
  status: string;
  incident_type: string;
  description: string;
};
