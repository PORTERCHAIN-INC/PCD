export interface DriverProfileBlock {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  status: string;
  rating: number | null;
  photo_url?: string | null;
  license_class?: string | null;
  license_number?: string | null;
  service_area?: string | null;
  province?: string | null;
  city?: string | null;
  fleetbase_driver_id?: string | null;
}

export interface VerificationStatus {
  license_verified: boolean;
  insurance_verified: boolean;
  vehicle_verified: boolean;
  background_check_status: string;
  abstract_verified?: boolean;
}

export interface AbstractInfo {
  status: string;
  verified: boolean;
  license_class?: string | null;
  demerit_points?: number | null;
  has_active_suspension?: boolean | null;
  url?: string | null;
  expires_at?: string | null;
  failure_reasons?: string[];
}

export interface LicenseInfo {
  verified: boolean;
  class?: string | null;
  number?: string | null;
  status: string;
  url?: string | null;
  expires_at?: string | null;
  uploaded_at?: string | null;
}

export interface RegistrationInfo {
  status: string;
  verified: boolean;
  url?: string | null;
  plate_number?: string | null;
  expires_at?: string | null;
  uploaded_at?: string | null;
}

export interface BackgroundCheckInfo {
  status: string;
  passed: boolean;
  url?: string | null;
  completed_at?: string | null;
  expires_at?: string | null;
}

export interface MaintenanceStatus {
  status: string;
  last_service_at?: string | null;
  next_service_due?: string | null;
  odometer_km?: number | null;
  notes?: string | null;
}

export interface ProfileVehicle {
  id: string;
  vehicle_class: string;
  plate_number: string;
  make_model: string | null;
  capacity_kg: number | null;
  compliance_expires_at: string | null;
  is_active: boolean;
  maintenance?: MaintenanceStatus;
  photos?: unknown[];
}

export interface ProfileDocument {
  type: string;
  label: string;
  status: string;
  verified: boolean;
  url?: string | null;
  uploaded_at?: string | null;
  expires_at?: string | null;
  policy_number?: string | null;
  provider?: string | null;
  plate_number?: string | null;
}

export interface VehiclePhoto {
  id: string;
  url?: string | null;
  status: string;
  uploaded_at?: string | null;
  label?: string;
}

export interface ExpiryItem {
  label: string;
  category: string;
  reference_id?: string | null;
  expires_at: string;
  days_until: number | null;
  severity: "ok" | "warning" | "urgent" | "expired";
}

export interface ExpiryNotification extends ExpiryItem {
  message: string;
}

export interface ContractInfo {
  has_contract: boolean;
  read_only: boolean;
  message?: string;
  contract_name?: string | null;
  contract_type?: string;
  effective_from?: string | null;
  effective_to?: string | null;
  pay_model?: string | null;
  minimum_guarantee_cents?: number | null;
  terms_url?: string | null;
  notes?: string | null;
}

export interface DriverProfileSnapshot {
  profile: DriverProfileBlock;
  verification: VerificationStatus;
  license: LicenseInfo;
  insurance: Record<string, unknown>;
  registration: RegistrationInfo;
  background_check: BackgroundCheckInfo;
  abstract?: AbstractInfo;
  vehicle: ProfileVehicle | null;
  maintenance_status: MaintenanceStatus;
  vehicle_photos: VehiclePhoto[];
  documents: ProfileDocument[];
  expiry_dates: ExpiryItem[];
  expiry_notifications: ExpiryNotification[];
  contract: ContractInfo;
  last_updated: string;
}

export const UPLOADABLE_DOC_TYPES = [
  { value: "license", label: "Driver License" },
  { value: "insurance", label: "Insurance Certificate" },
  { value: "vehicle_registration", label: "Vehicle Registration" },
  { value: "background_check", label: "Background Check" },
] as const;

export function severityStyles(severity: string): string {
  if (severity === "expired") return "bg-red-100 text-red-800";
  if (severity === "urgent") return "bg-amber-100 text-amber-900";
  if (severity === "warning") return "bg-yellow-50 text-yellow-900";
  return "bg-emerald-50 text-emerald-800";
}

export function formatProfileDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function statusBadge(status: string): string {
  const s = status.toLowerCase();
  if (s === "verified" || s === "approved" || s === "passed" || s === "cleared") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (s === "pending_review" || s === "pending") return "bg-amber-100 text-amber-900";
  if (s === "missing" || s === "rejected" || s === "failed") return "bg-red-100 text-red-800";
  return "bg-gray-100 text-gray-800";
}
