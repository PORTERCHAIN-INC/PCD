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

export type ScanProgress = {
  scanned: number;
  required: number;
  complete: boolean;
  missing_suffixes: string[];
  /** Boxes the driver reported missing at pickup (photo + reason). */
  reported_missing?: number;
};

export type Handshake = {
  api: LinkState;
  auth: LinkState;
  driverName: string | null;
  online: boolean | null;
  stopsDone: number | null;
  stopsTotal: number | null;
  /** Today's jobs (current first), de-duplicated. */
  jobs: DriverJobSummary[];
  routeId: string | null;
  stopId: string | null;
  stopStatus: string | null;
  nextStop: string | null;
  nextStopType: string | null;
  etaMinutes: number | null;
  currentOrderId: string | null;
  currentOrderNumber: string | null;
  currentOrderState: string | null;
  accessNotes: string | null;
  parcelLines: string[];
  deliveryAttempts: number | null;
  maxDeliveryAttempts: number | null;
  navigationUrl: string | null;
  destLat: number | null;
  destLng: number | null;
  etaLabel: string | null;
  distanceLabel: string | null;
  otpRequired: boolean;
  podRequirements: PodRequirements | null;
  scanPickup: ScanProgress | null;
  scanDelivery: ScanProgress | null;
  codAmountCents: number | null;
  codStatus: string | null;
  push: PushState;
  location: LocationState;
  error: string | null;
};

export type OfflineStatus = {
  pending_count: number;
  failed_count: number;
  synced_count?: number;
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
  special_instructions?: string | null;
  access_unit?: string | null;
  access_buzzer?: string | null;
  access_dock?: string | null;
  call_on_arrival?: boolean;
  contact_phone_masked?: string | null;
  delivery_attempts?: number;
  max_delivery_attempts?: number;
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
  route_id?: string | null;
  scan_pickup?: ScanProgress;
  scan_delivery?: ScanProgress;
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

export type DriverPackage = {
  id?: string;
  parcel_index?: number;
  total_parcels?: number;
  tracking_suffix?: string;
  status?: string;
  weight_kg?: number | null;
  preset_label?: string | null;
  instructions?: string | null;
  scanned_pickup?: boolean;
  scanned_delivery?: boolean;
  missing_at_pickup?: boolean;
  item_key?: string | null;
  box_index?: number | null;
  box_count?: number | null;
  package_type?: string;
};

/** API pod_policy.requirements_for — what the dropoff needs before completion. */
export type PodRequirements = {
  enforced?: boolean;
  photo_or_signature?: boolean;
  photo?: boolean;
  signature?: boolean;
  id_check?: boolean;
  otp?: boolean;
  reasons?: string[];
};

export type DriverJobDetail = DriverJobSummary & {
  scan_pickup?: ScanProgress;
  scan_delivery?: ScanProgress;
  otp_required?: boolean;
  pod_requirements?: PodRequirements;
  pod_missing?: string[];
  on_duty?: boolean;
  cod_amount_cents?: number | null;
  cod_status?: string | null;
  currency?: string;
  amount_cents?: number;
  route_id?: string | null;
  pickup_stop_id?: string;
  delivery_stop_id?: string;
  special_instructions?: string | null;
  declared_value_cents?: number | null;
  booking_mode?: string | null;
  vehicle_class?: string | null;
  packages?: DriverPackage[];
  packages_error?: string | null;
  pickup_completed_at?: string | null;
  delivery_completed_at?: string | null;
  delivery_attempts?: number;
  max_delivery_attempts?: number;
  merchant?: { company_name?: string } | null;
};

export type DriverOnboarding = {
  ready: boolean;
  blockers: string[];
  status: string;
  clerk_linked: boolean;
  pending_documents: number;
  can_access_portal: boolean;
};

export type NavigationSession = {
  idle?: boolean;
  navigation_url?: string | null;
  eta?: { eta_label?: string; duration_seconds?: number; distance_meters?: number } | null;
  dropoff?: { lat?: number; lng?: number; formatted?: string };
  pickup?: { lat?: number; lng?: number; formatted?: string };
  optimized_route?: { polyline?: string | null } | null;
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

export type SupportHub = {
  emergency_contact?: { ops_hotline?: string; ops_email?: string };
};

export type ShiftSnapshot = {
  shift_active?: boolean;
  online?: boolean;
  is_online?: boolean;
  availability?: string;
  on_break?: boolean;
  route_id?: string | null;
  started_at?: string | null;
};
