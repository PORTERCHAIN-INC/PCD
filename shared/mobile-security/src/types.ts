export type MobileAppKind = "customer" | "driver";

export type SecurityAuditEventType =
  | "login_success"
  | "login_failure"
  | "logout"
  | "session_refresh"
  | "session_refresh_failed"
  | "session_timeout"
  | "biometric_unlock_success"
  | "biometric_unlock_failure"
  | "pin_unlock_success"
  | "pin_unlock_failure"
  | "pin_set"
  | "pin_cleared"
  | "device_compromised"
  | "pinning_mismatch"
  | "rbac_denied";

export type SecurityAuditEvent = {
  event_type: SecurityAuditEventType;
  app_kind: MobileAppKind;
  occurred_at: string;
  metadata?: Record<string, unknown>;
};

export type MobileSession = {
  accessToken: string;
  refreshToken?: string | null;
  userId: string;
  email?: string | null;
  roles?: string[];
  permissions?: string[];
  expiresAt?: string | null;
};

export type SecurityPolicy = {
  sessionTimeoutMinutes: number;
  pinLength: number;
  enableIntegrityCheck: boolean;
  enableCertificatePinning: boolean;
  certificatePins: string[];
};

export type DeviceIntegrityResult = {
  compromised: boolean;
  jailbroken: boolean;
  rooted: boolean;
  reasons: string[];
  checkedAt: string;
};

export type Permission = string;

export type AuthPrincipal = {
  userId: string;
  roles: string[];
  permissions: string[];
};
