import type { AuthPrincipal, Permission, PlatformRole } from "@porterchain/types";

export const ROLE_PERMISSIONS: Record<PlatformRole, readonly Permission[]> = {
  visitor: ["quote:read", "quote:write"],
  customer: ["quote:read", "quote:write", "order:read"],
  merchant: ["quote:read", "quote:write", "order:read", "order:write"],
  driver: ["order:read"],
  dispatcher: ["order:read", "order:write", "dispatch:manage"],
  support: ["order:read", "support:manage", "crm:manage"],
  sales: ["crm:manage", "merchant:manage"],
  fleet_manager: ["dispatch:manage", "driver:manage"],
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

export function hasRole(principal: AuthPrincipal, role: PlatformRole): boolean {
  return principal.roles.includes(role);
}

export function hasAnyRole(principal: AuthPrincipal, ...roles: PlatformRole[]): boolean {
  return roles.some((r) => principal.roles.includes(r));
}

export function hasPermission(principal: AuthPrincipal, permission: Permission): boolean {
  const perms = new Set<Permission>();
  for (const role of principal.roles) {
    for (const p of ROLE_PERMISSIONS[role] ?? []) {
      perms.add(p);
    }
  }
  return perms.has(permission) || perms.has("system:all");
}
