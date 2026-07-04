export type EnterpriseRole =
  | "customer"
  | "merchant"
  | "merchant_admin"
  | "driver"
  | "dispatcher"
  | "finance"
  | "support"
  | "operations"
  | "admin"
  | "super_admin";

export type PlatformRole =
  | "visitor"
  | EnterpriseRole
  | "sales"
  | "fleet_manager";

export type UserType =
  | "visitor"
  | "customer"
  | "merchant"
  | "driver"
  | "admin"
  | "dispatcher"
  | "support"
  | "sales";

export type Permission =
  | "quote:read"
  | "quote:write"
  | "order:read"
  | "order:write"
  | "dispatch:manage"
  | "merchant:manage"
  | "driver:manage"
  | "billing:manage"
  | "crm:manage"
  | "support:manage"
  | "admin:settings"
  | "system:all";

export interface AuthPrincipal {
  userId: string;
  userType: UserType;
  roles: PlatformRole[];
  enterpriseRole?: EnterpriseRole;
  orgId?: string;
  email?: string;
  sessionId?: string;
}

export interface SessionTokens {
  accessToken: string;
  refreshToken: string;
  tokenType: "Bearer";
  expiresInSeconds: number;
}
