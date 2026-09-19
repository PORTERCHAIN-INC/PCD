export type Screen =
  | "sign-in"
  | "invite"
  | "onboarding"
  | "route"
  | "job-detail"
  | "inbox"
  | "support"
  | "force-update";

export type FieldTab = "work" | "jobs" | "money" | "docs" | "more";

export type LinkState = "up" | "down" | "idle";

export type PushKind = "fcm" | "apns" | "expo" | "denied" | "unavailable";

export type PushState = {
  kind: PushKind;
  permission: string;
  tokenPreview: string | null;
  registered: boolean;
  detail: string;
};

export type LocationState = {
  kind: "idle" | "granted" | "denied" | "error";
  detail: string;
};

export type Handshake = {
  api: LinkState;
  auth: LinkState;
  driverName: string | null;
  availability: string | null;
  online: boolean | null;
  nextStop: string | null;
  nextStopType: string | null;
  etaMinutes: number | null;
  stopsDone: number | null;
  stopsTotal: number | null;
  routeId: string | null;
  stopId: string | null;
  stopStatus: string | null;
  currentOrderId: string | null;
  currentOrderNumber: string | null;
  walletCents: number | null;
  todayEarningsCents: number | null;
  pendingDocuments: number | null;
  performanceScore: number | null;
  navigationUrl: string | null;
  destLat: number | null;
  destLng: number | null;
  etaLabel: string | null;
  distanceLabel: string | null;
  /** Cached from job detail during handshake — avoids FieldOps / OTP refetch races. */
  otpRequired: boolean;
  scanPickup: ScanProgress | null;
  scanDelivery: ScanProgress | null;
  codAmountCents: number | null;
  codStatus: string | null;
  push: PushState;
  location: LocationState;
  platformStatus: "ok" | "degraded" | "unknown";
  platformDetail: string | null;
  routePolyline: string | null;
  navStopCount: number | null;
  error: string | null;
};

export type OfflineActionRow = {
  id?: string;
  action_type: string;
  status?: string;
  error?: string | null;
  created_at?: string | null;
};

export type OfflineStatus = {
  pending_count: number;
  failed_count: number;
  synced_count?: number;
  pending?: OfflineActionRow[];
  failed?: OfflineActionRow[];
  last_sync_at?: string | null;
};

export type OfflineSyncResult = {
  synced: number;
  failed: number;
  conflicts_resolved?: number;
  pending?: number;
  synced_at?: string;
};

export type DriverMe = {
  id: string;
  full_name: string;
  email: string;
  is_online: boolean;
  availability: string;
  wallet_balance_cents?: number;
};

export type DriverDashboard = {
  is_online: boolean;
  availability: string;
  todays_stops_total: number;
  todays_stops_completed: number;
  todays_earnings_cents?: number;
  wallet_balance_cents?: number;
  active_route_id: string | null;
  pending_documents?: number;
  performance_score?: number;
  rating?: number | null;
};

export type DriverNextStop = {
  stop_id: string;
  stop_type: string;
  order_id: string;
  formatted_address?: string;
  status?: string | null;
  eta_minutes?: number | null;
  address?: { lat?: number; lng?: number };
};

export type DriverJobSummary = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state?: string;
  status?: string;
  bucket?: string;
  pickup_address?: string;
  delivery_address?: string;
  scheduled_at?: string | null;
  urgency?: string;
  is_current_job?: boolean;
  current_leg?: string;
};

export type DriverJobs = {
  route_id?: string | null;
  route_status?: string | null;
  next_stop?: DriverNextStop | null;
  current?: DriverJobSummary | null;
  upcoming?: DriverJobSummary[];
  completed?: DriverJobSummary[];
  jobs?: DriverJobSummary[];
};

export type ScanProgress = {
  scanned: number;
  required: number;
  complete: boolean;
  missing_suffixes: string[];
};

export type DriverJobDetail = DriverJobSummary & {
  scan_pickup?: ScanProgress;
  scan_delivery?: ScanProgress;
  otp_required?: boolean;
  cod_amount_cents?: number | null;
  cod_status?: string | null;
  currency?: string;
  amount_cents?: number;
  route_id?: string | null;
  pickup_stop_id?: string;
  delivery_stop_id?: string;
};

export type DriverOnboardingStep = {
  id: string;
  label: string;
  description: string;
  complete: boolean;
  status: string;
  missing?: string[];
};

export type DriverOnboarding = {
  ready: boolean;
  blockers: string[];
  status: string;
  clerk_linked: boolean;
  steps: DriverOnboardingStep[];
  pending_documents: number;
  can_access_portal: boolean;
};

export type WalletSnapshot = {
  balance_cents: number;
  transactions: Array<{
    id?: string;
    type?: string;
    amount_cents: number;
    description?: string;
    created_at?: string | null;
  }>;
  payouts: Array<{
    id?: string;
    amount_cents: number;
    status?: string;
    created_at?: string | null;
  }>;
};

export type EarningsSnapshot = {
  today_cents: number;
  week_cents: number;
  month_cents: number;
  completed_deliveries_today?: number;
  wallet_balance_cents?: number;
  last_updated?: string;
};

export type StatementRow = {
  id: string;
  period_label: string;
  gross_cents: number;
  net_cents: number;
  deliveries: number;
};

export type DriverDocument = {
  type: string;
  label: string;
  status: string;
  verified: boolean;
  url?: string | null;
  expires_at?: string | null;
};

export type DriverPerformance = {
  score: number;
  on_time_percent: number;
  completion_percent: number;
  deliveries_total: number;
  deliveries_today: number;
  acceptance_rate: number;
  rating: number | null;
};

export type NavigationSession = {
  idle?: boolean;
  navigation_url?: string | null;
  eta?: { eta_label?: string; duration_seconds?: number; distance_meters?: number } | null;
  dropoff?: { lat?: number; lng?: number; formatted?: string };
  pickup?: { lat?: number; lng?: number; formatted?: string };
  optimized_route?: { polyline?: string | null } | null;
};

export type NavigationRoute = {
  route_id?: string;
  route_polyline?: string | null;
  stops?: Array<{ stop_id: string; stop_type?: string; status?: string | null }>;
  eta?: { eta_label?: string; duration_seconds?: number; distance_meters?: number } | null;
};

export type MobileDriverPolicy = {
  min_version: string;
  force_update: boolean;
  store_url_ios?: string;
  store_url_android?: string;
  message?: string;
};

export type PublicHealthStatus = {
  status: string;
  components?: Record<string, string>;
  mobile?: { driver?: MobileDriverPolicy };
  updated_at?: string;
};

export type InboxNotification = {
  id: string;
  title: string;
  body: string;
  priority?: string;
  category?: string;
  template_key?: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at?: string | null;
  group?: string;
  order_id?: string;
};

export type InboxSnapshot = {
  unread_count: number;
  items: InboxNotification[];
};

export type SupportTicketRow = {
  id: string;
  ticket_number?: string;
  subject: string;
  status: string;
  priority: string;
  order_id?: string | null;
  created_at?: string | null;
};

export type SupportClaimRow = {
  id: string;
  claim_number?: string;
  claim_type: string;
  status: string;
  order_id: string;
  description?: string | null;
  created_at?: string | null;
};

export type SupportIncidentRow = {
  id: string;
  incident_type: string;
  description: string;
  status: string;
  created_at: string;
};

export type EmergencyContact = {
  name?: string | null;
  phone?: string | null;
  relationship?: string | null;
  ops_hotline?: string;
  ops_email?: string;
};

export type KbArticle = {
  id: string;
  category_id: string;
  title: string;
  body: string;
};

export type SupportHub = {
  tickets: SupportTicketRow[];
  claims: SupportClaimRow[];
  incidents: SupportIncidentRow[];
  emergency_contact: EmergencyContact;
  knowledge_base: {
    categories: Array<{ id: string; name: string }>;
    articles: KbArticle[];
    faq: Array<{ question: string; answer: string }>;
  };
  chat?: { enabled: boolean; status: string; message: string };
};

export type ShiftSnapshot = {
  online?: boolean;
  availability?: string;
  on_break?: boolean;
  route_id?: string | null;
  started_at?: string | null;
};

export type OptimizeResult = {
  plan_id?: string;
  run_id?: string | null;
  status?: string;
  warnings?: string[];
  message?: string | null;
  order_ids?: string[];
  metrics?: Record<string, unknown>;
  jobs?: DriverJobs;
  optimized_stops?: Array<Record<string, unknown>>;
  sequence_version?: number | null;
  preview?: boolean | null;
  applied?: boolean | null;
  ok?: boolean | null;
  error?: string | null;
};

export type AssignedRoute = {
  id: string;
  status?: string | null;
  stop_count?: number;
  completed_stops?: number;
  earnings_cents?: number | null;
};

export type RouteStopRow = {
  stop_id: string;
  stop_type?: string;
  order_id?: string;
  status?: string | null;
  formatted_address?: string | null;
  sequence?: number;
};

export type DriverProfile = {
  full_name?: string;
  email?: string;
  phone?: string | null;
  status?: string;
  rating?: number | null;
  profile?: {
    full_name?: string;
    email?: string;
    phone?: string | null;
    status?: string;
    rating?: number | null;
  };
};

export type DriverVehicle = {
  id: string;
  vehicle_class?: string;
  plate_number?: string;
  make_model?: string | null;
  is_active?: boolean;
};

export type TrainingModule = {
  id: string;
  title?: string;
  name?: string;
  completed?: boolean;
  status?: string;
};

export type BonusRow = {
  id: string;
  title?: string;
  label?: string;
  amount_cents?: number;
  status?: string;
  claimable?: boolean;
};

export type RatingsSummary = {
  rating?: number | null;
  count?: number;
  average?: number | null;
  recent?: Array<{ score?: number; comment?: string | null }>;
};

export type InsuranceStatus = {
  status?: string;
  verified?: boolean;
  provider?: string | null;
  expires_at?: string | null;
};

export type StatementDetail = {
  id: string;
  period_label?: string;
  net_cents?: number;
  download_url?: string | null;
  lines?: Array<{ description?: string; amount_cents?: number }>;
};
