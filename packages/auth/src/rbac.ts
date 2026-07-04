import type { AuthPrincipal, EnterpriseRole, Permission, PlatformRole } from "@porterchain/types";

export const ENTERPRISE_ROLE_PERMISSIONS: Record<EnterpriseRole, readonly Permission[]> = {
  customer: ["quote:read", "quote:write", "order:read"],
  merchant: ["quote:read", "quote:write", "order:read", "order:write"],
  merchant_admin: [
    "quote:read",
    "quote:write",
    "order:read",
    "order:write",
    "merchant:manage",
  ],
  driver: ["order:read"],
  dispatcher: ["order:read", "order:write", "dispatch:manage"],
  finance: ["order:read", "billing:manage"],
  support: ["order:read", "support:manage", "crm:manage"],
  operations: [
    "order:read",
    "order:write",
    "dispatch:manage",
    "driver:manage",
    "merchant:manage",
    "crm:manage",
  ],
  admin: [
    "order:read",
    "order:write",
    "dispatch:manage",
    "merchant:manage",
    "driver:manage",
    "billing:manage",
    "crm:manage",
    "support:manage",
    "admin:settings",
  ],
  super_admin: ["system:all"],
};

export const ROLE_PERMISSIONS: Record<PlatformRole, readonly Permission[]> = {
  visitor: ["quote:read", "quote:write"],
  ...ENTERPRISE_ROLE_PERMISSIONS,
  sales: ["crm:manage", "merchant:manage"],
  fleet_manager: ["dispatch:manage", "driver:manage"],
};

export function hasRole(principal: AuthPrincipal, role: PlatformRole): boolean {
  return principal.roles.includes(role);
}

export function hasAnyRole(principal: AuthPrincipal, ...roles: PlatformRole[]): boolean {
  return roles.some((r) => principal.roles.includes(r));
}

export function hasEnterpriseRole(principal: AuthPrincipal, role: EnterpriseRole): boolean {
  return principal.enterpriseRole === role;
}

export function hasPermission(principal: AuthPrincipal, permission: Permission): boolean {
  const perms = new Set<Permission>();
  if (principal.enterpriseRole) {
    for (const p of ENTERPRISE_ROLE_PERMISSIONS[principal.enterpriseRole] ?? []) {
      perms.add(p);
    }
  }
  for (const role of principal.roles) {
    for (const p of ROLE_PERMISSIONS[role] ?? []) {
      perms.add(p);
    }
  }
  return perms.has(permission) || perms.has("system:all");
}
